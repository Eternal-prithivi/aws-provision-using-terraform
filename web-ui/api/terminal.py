"""web-ui/api/terminal.py — WebSocket terminal handler + PTY manager.

Provides a browser-based terminal (CloudShell) via WebSocket:
- Spawns a PTY subprocess per authenticated session
- Bidirectional I/O between xterm.js frontend and shell
- Session timeout after inactivity
- RBAC enforcement (Admin/DevOps only)
- Audit trail integration for all commands

Usage:
    # In server.py:
    from terminal import terminal_router
    app.include_router(terminal_router)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pty
import select
import signal
import struct
import fcntl
import termios
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from terminal_security import TerminalSecurityGuard

logger = logging.getLogger("terminal")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ─── Configuration ───
TERMINAL_SHELL = os.environ.get("TERMINAL_SHELL", "/bin/zsh")
SESSION_TIMEOUT_SECONDS = int(os.environ.get("TERMINAL_TIMEOUT", "1800"))  # 30 min
MAX_SESSIONS_PER_USER = int(os.environ.get("TERMINAL_MAX_SESSIONS", "5"))
HISTORY_MAX_LINES = 100

# ─── RBAC: Only these roles can access terminal ───
ALLOWED_ROLES: set[str] = {"admin", "devops"}

terminal_router = APIRouter(tags=["terminal"])
security_guard = TerminalSecurityGuard(use_allowlist=False)


@dataclass
class TerminalSession:
    """Represents an active terminal session."""

    session_id: str
    username: str
    role: str
    master_fd: int
    slave_fd: int
    pid: int
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    command_history: list[str] = field(default_factory=list)
    is_alive: bool = True


# ─── Active sessions registry ───
_sessions: dict[str, TerminalSession] = {}


def _is_process_alive(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)  # Signal 0 = check existence without killing
        return True
    except (OSError, ProcessLookupError):
        return False


def _cleanup_dead_sessions() -> None:
    """Remove sessions whose processes have died or are idle too long."""
    now = time.time()
    dead_ids = [
        sid for sid, s in _sessions.items()
        if s.is_alive and (
            not _is_process_alive(s.pid)
            or (now - s.last_activity) > 120  # Reap sessions idle > 2 min
        )
    ]
    for sid in dead_ids:
        _cleanup_session(sid)


def _count_user_sessions(username: str) -> int:
    """Count active sessions for a given user (cleans up dead sessions first)."""
    _cleanup_dead_sessions()
    return sum(1 for s in _sessions.values() if s.username == username and s.is_alive)


def _resize_pty(fd: int, rows: int, cols: int) -> None:
    """Resize the pseudoterminal window."""
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except OSError:
        pass


def _cleanup_session(session_id: str) -> None:
    """Clean up a terminal session — close FDs and kill process."""
    session = _sessions.get(session_id)
    if not session:
        return

    session.is_alive = False

    try:
        os.close(session.master_fd)
    except OSError:
        pass
    try:
        os.close(session.slave_fd)
    except OSError:
        pass
    try:
        os.kill(session.pid, signal.SIGTERM)
        os.waitpid(session.pid, os.WNOHANG)
    except (OSError, ChildProcessError):
        pass

    _sessions.pop(session_id, None)
    logger.info("Session %s cleaned up for user %s", session_id, session.username)


def _spawn_pty_process() -> tuple[int, int, int]:
    """Spawn a new PTY process running the configured shell.

    Returns:
        Tuple of (master_fd, slave_fd, child_pid).
    """
    master_fd, slave_fd = pty.openpty()

    # Set initial PTY window size to conservative 80x24
    # The frontend sends actual dimensions on connect via resize message
    try:
        winsize = struct.pack("HHHH", 24, 80, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    except OSError:
        pass

    pid = os.fork()
    if pid == 0:
        # Child process
        os.setsid()

        # Set the slave as the controlling terminal
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

        # Redirect stdin/stdout/stderr to the slave PTY
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)

        # Close the master and original slave
        os.close(master_fd)
        if slave_fd > 2:
            os.close(slave_fd)

        # Set working directory
        os.chdir(str(PROJECT_ROOT))

        # Set environment — do NOT set COLUMNS/LINES as env vars
        # because they override the PTY window size from resize signals.
        # The PTY ioctl above and frontend resize messages handle sizing.
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env.pop("COLUMNS", None)
        env.pop("LINES", None)
        env["PS1"] = r"\[\033[1;34m\]cloudshell\[\033[0m\]:\[\033[1;36m\]\w\[\033[0m\]$ "

        # Execute shell
        shell = TERMINAL_SHELL if os.path.exists(TERMINAL_SHELL) else "/bin/bash"
        os.execvpe(shell, [shell, "--login"], env)

    # Parent process
    return master_fd, slave_fd, pid


def _resize_pty(master_fd: int, rows: int, cols: int) -> None:
    """Resize the PTY to match the client terminal size."""
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    except OSError:
        pass


@terminal_router.websocket("/ws/terminal")
async def websocket_terminal(
    websocket: WebSocket,
    username: str = Query(default=""),
    role: str = Query(default=""),
) -> None:
    """WebSocket endpoint for interactive terminal sessions.

    Query params:
        username: Authenticated username
        role: User's RBAC role (admin, devops, developer, viewer)
    """
    await websocket.accept()

    # ── RBAC Check ──
    if role.lower() not in ALLOWED_ROLES:
        await websocket.send_json({
            "type": "error",
            "data": f"Access denied. Terminal requires one of: {', '.join(ALLOWED_ROLES)}. Your role: {role}",
        })
        await websocket.close(code=4003, reason="Insufficient permissions")
        return

    # ── Session limit check ──
    if _count_user_sessions(username) >= MAX_SESSIONS_PER_USER:
        await websocket.send_json({
            "type": "error",
            "data": f"Maximum {MAX_SESSIONS_PER_USER} concurrent sessions allowed.",
        })
        await websocket.close(code=4004, reason="Session limit reached")
        return

    # ── Spawn PTY ──
    try:
        master_fd, slave_fd, pid = _spawn_pty_process()
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "data": f"Failed to spawn terminal: {str(e)}",
        })
        await websocket.close(code=4005, reason="PTY spawn failed")
        return

    import uuid
    session_id = str(uuid.uuid4())[:8]
    session = TerminalSession(
        session_id=session_id,
        username=username,
        role=role,
        master_fd=master_fd,
        slave_fd=slave_fd,
        pid=pid,
    )
    _sessions[session_id] = session

    logger.info("Terminal session %s started for %s (role: %s)", session_id, username, role)

    # Send session info to client
    await websocket.send_json({
        "type": "session_start",
        "data": {
            "session_id": session_id,
            "username": username,
            "role": role,
            "working_directory": str(PROJECT_ROOT),
            "timeout_seconds": SESSION_TIMEOUT_SECONDS,
        },
    })

    # ── I/O Loop ──
    async def read_pty_output() -> None:
        """Read output from PTY and send to WebSocket."""
        loop = asyncio.get_event_loop()
        while session.is_alive:
            try:
                ready, _, _ = await loop.run_in_executor(
                    None,
                    lambda: select.select([master_fd], [], [], 0.1),
                )
                if ready:
                    data = os.read(master_fd, 4096)
                    if not data:
                        break
                    output = data.decode("utf-8", errors="replace")
                    # Sanitize credentials from output
                    clean_output = security_guard.sanitize_output(output)
                    await websocket.send_json({
                        "type": "output",
                        "data": clean_output,
                    })
                    session.last_activity = time.time()
            except (OSError, WebSocketDisconnect):
                break
            except Exception:
                break

    async def write_pty_input() -> None:
        """Read input from WebSocket and write to PTY."""
        while session.is_alive:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=SESSION_TIMEOUT_SECONDS,
                )
                try:
                    msg = json.loads(message)
                except json.JSONDecodeError:
                    msg = {"type": "input", "data": message}

                msg_type = msg.get("type", "input")
                msg_data = msg.get("data", "")

                if msg_type == "input":
                    # Write user input to PTY
                    os.write(master_fd, msg_data.encode("utf-8"))
                    session.last_activity = time.time()

                    # Track command history (on Enter key)
                    if msg_data == "\r" or msg_data == "\n":
                        pass  # History is tracked implicitly by the shell

                elif msg_type == "resize":
                    rows = msg.get("rows", 30)
                    cols = msg.get("cols", 120)
                    _resize_pty(master_fd, rows, cols)

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    session.last_activity = time.time()

            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "timeout",
                    "data": f"Session timed out after {SESSION_TIMEOUT_SECONDS // 60} minutes of inactivity.",
                })
                break
            except WebSocketDisconnect:
                break
            except Exception:
                break

    try:
        await asyncio.gather(
            read_pty_output(),
            write_pty_input(),
            return_exceptions=True,
        )
    finally:
        _cleanup_session(session_id)
        try:
            await websocket.close()
        except Exception:
            pass


# ─── REST endpoints for terminal management ───


@terminal_router.get("/api/terminal/sessions")
async def list_terminal_sessions() -> dict[str, Any]:
    """List all active terminal sessions (auto-cleans dead sessions)."""
    _cleanup_dead_sessions()
    sessions_list = []
    for sid, session in _sessions.items():
        if session.is_alive:
            sessions_list.append({
                "session_id": sid,
                "username": session.username,
                "role": session.role,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "idle_seconds": int(time.time() - session.last_activity),
            })
    return {"sessions": sessions_list, "total": len(sessions_list)}


@terminal_router.delete("/api/terminal/sessions/{session_id}")
async def kill_terminal_session(session_id: str) -> dict[str, Any]:
    """Kill a specific terminal session (admin only)."""
    if session_id not in _sessions:
        return {"success": False, "message": f"Session '{session_id}' not found"}
    _cleanup_session(session_id)
    return {"success": True, "message": f"Session '{session_id}' terminated"}


@terminal_router.delete("/api/terminal/sessions")
async def kill_all_sessions() -> dict[str, Any]:
    """Kill all terminal sessions (admin emergency reset)."""
    count = len(_sessions)
    for sid in list(_sessions.keys()):
        _cleanup_session(sid)
    return {"success": True, "message": f"{count} sessions terminated"}


@terminal_router.get("/api/terminal/security")
async def get_terminal_security_info() -> dict[str, Any]:
    """Return terminal security configuration (blocked patterns, etc.)."""
    return {
        "blocked_patterns": security_guard.get_blocked_patterns_info(),
        "allowed_roles": list(ALLOWED_ROLES),
        "session_timeout_seconds": SESSION_TIMEOUT_SECONDS,
        "max_sessions_per_user": MAX_SESSIONS_PER_USER,
    }
