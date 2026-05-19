"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "@xterm/xterm/css/xterm.css";

interface TerminalProps {
  username: string;
  role: string;
  onSessionStart?: (sessionId: string) => void;
  onSessionEnd?: () => void;
}

const MAX_RETRIES = 3;
const BASE_RETRY_DELAY_MS = 1500;
const API_BASE = "http://localhost:8000";
const WS_BASE = "ws://localhost:8000";

export default function TerminalComponent({
  username,
  role,
  onSessionStart,
  onSessionEnd,
}: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const connectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);

  /** Check if the FastAPI server is reachable before attempting WebSocket. */
  const checkServerHealth = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        setServerOnline(true);
        return true;
      }
    } catch {
      /* server unreachable */
    }
    setServerOnline(false);
    return false;
  }, []);

  /** Open a WebSocket to the terminal backend. */
  const openWebSocket = useCallback((term: XTerm) => {
    // Close stale socket if any
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    const wsUrl = `${WS_BASE}/ws/terminal?username=${encodeURIComponent(
      username
    )}&role=${encodeURIComponent(role)}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setServerOnline(true);
      setError("");
      retryCountRef.current = 0;
      // Send actual terminal dimensions so PTY wraps correctly
      if (term.cols && term.rows) {
        ws.send(
          JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols })
        );
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case "session_start":
            setSessionId(msg.data.session_id);
            onSessionStart?.(msg.data.session_id);
            term.write(
              `\r\n\x1b[1;32m✓ Connected to CloudShell\x1b[0m (session: ${msg.data.session_id})\r\n` +
                `\x1b[90mWorking directory: ${msg.data.working_directory}\x1b[0m\r\n` +
                `\x1b[90mTimeout: ${msg.data.timeout_seconds / 60} minutes\x1b[0m\r\n\r\n`
            );
            break;
          case "output":
            term.write(msg.data);
            break;
          case "error":
            setError(msg.data);
            term.write(`\r\n\x1b[1;31m✗ Error: ${msg.data}\x1b[0m\r\n`);
            break;
          case "timeout":
            term.write(`\r\n\x1b[1;33m⏱ ${msg.data}\x1b[0m\r\n`);
            setConnected(false);
            onSessionEnd?.();
            break;
          case "pong":
            break;
        }
      } catch {
        term.write(event.data);
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      if (event.code === 4003) {
        setError("Access denied. Terminal requires Admin or DevOps role.");
      } else if (event.code === 4004) {
        setError("Session limit reached. Close an existing terminal first.");
      } else if (event.code !== 1000) {
        // Auto-retry with exponential backoff
        if (retryCountRef.current < MAX_RETRIES) {
          const delay = BASE_RETRY_DELAY_MS * Math.pow(2, retryCountRef.current);
          retryCountRef.current += 1;
          term.write(`\r\n\x1b[90m─── Connection lost. Retrying in ${(delay / 1000).toFixed(1)}s (${retryCountRef.current}/${MAX_RETRIES})... ───\x1b[0m\r\n`);
          retryTimerRef.current = setTimeout(() => {
            openWebSocket(term);
          }, delay);
        } else {
          term.write(`\r\n\x1b[90m─── Connection closed ───\x1b[0m\r\n`);
        }
      }
      onSessionEnd?.();
    };

    ws.onerror = () => {
      // Don't set error immediately — let onclose handle retry logic
      setConnected(false);
      setServerOnline(false);
    };
  }, [username, role, onSessionStart, onSessionEnd]);

  /** Attempt connection: health check → WebSocket. */
  const attemptConnect = useCallback(async (term: XTerm) => {
    term.write("\x1b[90mChecking server status...\x1b[0m\r\n");
    const online = await checkServerHealth();
    
    if (online) {
      term.write("\x1b[1;32m✓ Server online\x1b[0m — opening terminal session...\r\n");
      openWebSocket(term);
    } else {
      setError("server_offline");
      term.write(
        "\r\n\x1b[1;31m✗ Cannot reach API server at localhost:8000\x1b[0m\r\n\r\n" +
        "\x1b[90mTo start the server, run:\x1b[0m\r\n" +
        "\x1b[1;36m  cd web-ui/api && uvicorn server:app --reload --port 8000\x1b[0m\r\n\r\n" +
        "\x1b[90mThen click \x1b[1;34mReconnect\x1b[90m or press \x1b[1;37mCtrl+R\x1b[90m to retry.\x1b[0m\r\n"
      );
    }
  }, [checkServerHealth, openWebSocket]);

  // ──────────────────────────────────────────────────────────
  // Single useEffect — no dependency on callbacks
  // Uses a 200ms delay so React Strict Mode's first mount/unmount
  // cycle completes before we ever open a WebSocket.
  // ──────────────────────────────────────────────────────────
  useEffect(() => {
    const container = terminalRef.current;
    if (!container) return;

    // 1. Create xterm.js instance
    const term = new XTerm({
      theme: {
        background: "#06060b",
        foreground: "#e2e8f0",
        cursor: "#6366f1",
        cursorAccent: "#06060b",
        selectionBackground: "rgba(99, 102, 241, 0.3)",
        black: "#1e293b",
        red: "#ef4444",
        green: "#22c55e",
        yellow: "#f59e0b",
        blue: "#6366f1",
        magenta: "#a855f7",
        cyan: "#06b6d4",
        white: "#e2e8f0",
        brightBlack: "#475569",
        brightRed: "#f87171",
        brightGreen: "#4ade80",
        brightYellow: "#fbbf24",
        brightBlue: "#818cf8",
        brightMagenta: "#c084fc",
        brightCyan: "#22d3ee",
        brightWhite: "#f8fafc",
      },
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
      fontSize: 14,
      lineHeight: 1.4,
      cursorBlink: true,
      cursorStyle: "bar",
      scrollback: 5000,
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.open(container);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Welcome banner
    term.write(
      "\x1b[1;36m╔══════════════════════════════════════╗\x1b[0m\r\n" +
        "\x1b[1;36m║\x1b[0m   \x1b[1;37mAWS Provisioner CloudShell\x1b[0m        \x1b[1;36m║\x1b[0m\r\n" +
        "\x1b[1;36m╚══════════════════════════════════════╝\x1b[0m\r\n\r\n"
    );

    // Forward keystrokes to WebSocket
    term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "input", data }));
      }
    });

    // 2. Delay WebSocket connect by 200ms — React Strict Mode's
    //    first unmount fires within ~50ms, so only the surviving
    //    second mount will actually open the socket.
    connectTimerRef.current = setTimeout(() => {
      attemptConnect(term);

      // Keepalive ping every 30s
      pingTimerRef.current = setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    }, 200);

    // 3. Resize handling
    const resizeObserver = new ResizeObserver(() => {
      try {
        fitAddon.fit();
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols })
          );
        }
      } catch {
        /* ignore */
      }
    });
    resizeObserver.observe(container);

    // 4. Cleanup
    return () => {
      // Cancel the delayed connect — critical for Strict Mode
      if (connectTimerRef.current) {
        clearTimeout(connectTimerRef.current);
        connectTimerRef.current = null;
      }
      if (pingTimerRef.current) {
        clearInterval(pingTimerRef.current);
        pingTimerRef.current = null;
      }
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
      resizeObserver.disconnect();
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      term.dispose();
      xtermRef.current = null;
      fitAddonRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleReconnect = async () => {
    setError("");
    retryCountRef.current = 0;
    if (xtermRef.current) {
      xtermRef.current.write("\r\n\x1b[90mReconnecting...\x1b[0m\r\n");
      await attemptConnect(xtermRef.current);
    }
  };

  const isServerOffline = error === "server_offline";

  return (
    <div style={{ position: "relative", height: "100%", width: "100%" }}>
      {/* Status bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 16px",
          background: "rgba(6, 6, 11, 0.95)",
          borderBottom: "1px solid var(--border-subtle)",
          fontSize: "0.75rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: connected ? "#22c55e" : error ? "#ef4444" : "#f59e0b",
              boxShadow: connected
                ? "0 0 6px rgba(34,197,94,0.5)"
                : error
                ? "0 0 6px rgba(239,68,68,0.5)"
                : "none",
              animation: !connected && !error ? "pulse-glow 1.5s ease-in-out infinite" : "none",
            }}
          />
          <span style={{ color: "var(--text-muted)" }}>
            {connected
              ? `Connected • ${username} • Session: ${sessionId}`
              : isServerOffline
              ? "Server Offline"
              : error
              ? "Disconnected"
              : "Connecting..."}
          </span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          {!connected && (
            <button
              onClick={handleReconnect}
              style={{
                background: "rgba(99,102,241,0.15)",
                border: "1px solid rgba(99,102,241,0.3)",
                color: "#818cf8",
                padding: "3px 10px",
                borderRadius: "4px",
                cursor: "pointer",
                fontSize: "0.7rem",
                fontWeight: 600,
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(99,102,241,0.25)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(99,102,241,0.15)";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              Reconnect
            </button>
          )}
        </div>
      </div>

      {/* Server offline banner */}
      {isServerOffline && (
        <div
          style={{
            padding: "14px 16px",
            background: "linear-gradient(135deg, rgba(239,68,68,0.08), rgba(245,158,11,0.06))",
            borderBottom: "1px solid rgba(239,68,68,0.15)",
            fontSize: "0.82rem",
            display: "flex",
            alignItems: "flex-start",
            gap: 12,
          }}
        >
          <div style={{
            width: 32, height: 32, borderRadius: "var(--radius-sm)",
            background: "rgba(239,68,68,0.12)", display: "flex",
            alignItems: "center", justifyContent: "center", flexShrink: 0,
            marginTop: 2,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>
          <div>
            <p style={{ fontWeight: 600, color: "#f87171", marginBottom: 6 }}>
              API Server Not Running
            </p>
            <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
              CloudShell requires the FastAPI backend on port 8000. Start it with:
            </p>
            <code style={{
              display: "block", margin: "8px 0",
              padding: "8px 12px", background: "rgba(0,0,0,0.3)",
              borderRadius: "var(--radius-xs)", fontSize: "0.78rem",
              fontFamily: "var(--font-mono)", color: "#22d3ee",
              border: "1px solid var(--border-subtle)",
            }}>
              cd web-ui/api && uvicorn server:app --reload --port 8000
            </code>
            <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
              Once started, click <strong style={{ color: "#818cf8" }}>Reconnect</strong> above.
            </p>
          </div>
        </div>
      )}

      {/* Error banner (non-server-offline errors) */}
      {error && !isServerOffline && (
        <div
          style={{
            padding: "10px 16px",
            background: "rgba(239,68,68,0.1)",
            borderBottom: "1px solid rgba(239,68,68,0.2)",
            color: "#f87171",
            fontSize: "0.8rem",
          }}
        >
          ✗ {error}
        </div>
      )}

      {/* Terminal container */}
      <div
        ref={terminalRef}
        style={{
          height: "calc(100% - 40px)",
          padding: "8px",
          background: "#06060b",
        }}
      />
    </div>
  );
}
