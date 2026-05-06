#!/usr/bin/env python3
"""team-management/audit.py — Deployment audit logging and compliance tracking.

Maintains immutable audit logs for all deployment actions for compliance and debugging.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AuditEvent:
    """Represents an audit event."""

    event_id: str
    timestamp: str
    action: str  # deploy, approve, reject, rollback, etc.
    actor: str  # username or service
    environment: str
    deployment_id: str
    status: str  # success, pending, failed
    details: dict[str, Any]
    reason: str | None = None


class AuditLogger:
    """Audit logger for deployment tracking."""

    def __init__(self, log_file: Path | None = None) -> None:
        """Initialize audit logger."""
        if log_file is None:
            log_file = Path(__file__).resolve().parent.parent / "audit.jsonl"
        
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        action: str,
        actor: str,
        environment: str,
        deployment_id: str,
        status: str,
        details: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> AuditEvent:
        """Log a deployment event."""
        event_id = f"{datetime.now(tz=timezone.utc).isoformat()}-{deployment_id}"
        
        event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
            action=action,
            actor=actor,
            environment=environment,
            deployment_id=deployment_id,
            status=status,
            details=details or {},
            reason=reason,
        )
        
        self._write_event(event)
        return event

    def _write_event(self, event: AuditEvent) -> None:
        """Write event to audit log (append-only)."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")

    def read_events(
        self,
        actor: str | None = None,
        environment: str | None = None,
        action: str | None = None,
        limit: int | None = None,
    ) -> list[AuditEvent]:
        """Read events from audit log with optional filtering."""
        if not self.log_file.exists():
            return []
        
        events = []
        with open(self.log_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                data = json.loads(line)
                event = AuditEvent(**data)
                
                # Apply filters
                if actor and event.actor != actor:
                    continue
                if environment and event.environment != environment:
                    continue
                if action and event.action != action:
                    continue
                
                events.append(event)
        
        # Return most recent first, limited by limit
        events.reverse()
        return events[:limit] if limit else events

    def get_deployment_history(self, deployment_id: str) -> list[AuditEvent]:
        """Get all events for a specific deployment."""
        events = []
        if not self.log_file.exists():
            return events
        
        with open(self.log_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                data = json.loads(line)
                if data.get("deployment_id") == deployment_id:
                    events.append(AuditEvent(**data))
        
        return events

    def get_user_actions(self, username: str) -> list[AuditEvent]:
        """Get all actions by a specific user."""
        return self.read_events(actor=username)

    def get_environment_history(self, environment: str) -> list[AuditEvent]:
        """Get all deployment actions in an environment."""
        return self.read_events(environment=environment)

    def generate_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Generate audit report for a date range."""
        if not self.log_file.exists():
            return {
                "total_events": 0,
                "by_action": {},
                "by_actor": {},
                "by_environment": {},
                "by_status": {},
            }
        
        events = []
        with open(self.log_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                data = json.loads(line)
                event = AuditEvent(**data)
                
                event_time = datetime.fromisoformat(event.timestamp)
                if start_date and event_time < start_date:
                    continue
                if end_date and event_time > end_date:
                    continue
                
                events.append(event)
        
        # Build report
        report: dict[str, Any] = {
            "total_events": len(events),
            "by_action": {},
            "by_actor": {},
            "by_environment": {},
            "by_status": {},
        }
        
        for event in events:
            # By action
            report["by_action"][event.action] = report["by_action"].get(event.action, 0) + 1
            
            # By actor
            report["by_actor"][event.actor] = report["by_actor"].get(event.actor, 0) + 1
            
            # By environment
            env_key = event.environment or "unknown"
            report["by_environment"][env_key] = report["by_environment"].get(env_key, 0) + 1
            
            # By status
            report["by_status"][event.status] = report["by_status"].get(event.status, 0) + 1
        
        return report


def build_parser() -> Any:
    """Build argument parser for CLI."""
    import argparse
    parser = argparse.ArgumentParser(description="Audit logging and compliance tracking.")
    parser.add_argument(
        "--actor",
        help="Filter by actor (username).",
    )
    parser.add_argument(
        "--environment",
        help="Filter by environment.",
    )
    parser.add_argument(
        "--action",
        help="Filter by action.",
    )
    parser.add_argument(
        "--deployment",
        help="Get history for specific deployment.",
    )
    parser.add_argument(
        "--user",
        help="Get all actions by user.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate audit report.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to audit log file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for audit logging."""
    parser = build_parser()
    args = parser.parse_args(argv)
    
    logger = AuditLogger(log_file=args.log_file)
    
    if args.deployment:
        events = logger.get_deployment_history(args.deployment)
        print(f"Deployment {args.deployment}: {len(events)} events")
        for event in events:
            print(f"  {event.timestamp}: {event.action} → {event.status} ({event.actor})")
        return 0
    
    if args.user:
        events = logger.get_user_actions(args.user)
        print(f"Actions by {args.user}: {len(events)} events")
        for event in events[:10]:
            print(f"  {event.timestamp}: {event.action} on {event.environment} ({event.status})")
        return 0
    
    if args.report:
        report = logger.generate_report()
        print("Audit Report:")
        print(f"  Total Events: {report['total_events']}")
        print("  By Action:")
        for action, count in report["by_action"].items():
            print(f"    {action}: {count}")
        print("  By Status:")
        for status, count in report["by_status"].items():
            print(f"    {status}: {count}")
        return 0
    
    # Default: show recent events
    events = logger.read_events(limit=20)
    print(f"Recent Audit Events ({len(events)}):")
    for event in events:
        print(f"  {event.timestamp}: {event.action} by {event.actor} on {event.environment} ({event.status})")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
