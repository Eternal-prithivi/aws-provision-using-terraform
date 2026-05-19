"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { Terminal as TerminalIcon, ShieldCheck, Info, XCircle, Wifi, WifiOff, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";

// Dynamic import to avoid SSR issues with xterm.js
const TerminalComponent = dynamic(
  () => import("@/components/Terminal"),
  { ssr: false }
);

export default function TerminalPage() {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("");
  const [hasAccess, setHasAccess] = useState<boolean | null>(null);
  const [sessionId, setSessionId] = useState("");
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);

  useEffect(() => {
    // Read auth from sessionStorage (same pattern as AuthGuard + TopBar)
    try {
      const stored = sessionStorage.getItem("auth_user");
      if (stored) {
        const data = JSON.parse(stored);
        setUsername(data.username || "");
        setRole(data.role || "viewer");
        setHasAccess(
          data.role === "admin" || data.role === "devops"
        );
      } else {
        setHasAccess(false);
      }
    } catch {
      setHasAccess(false);
    }

    // Check server health
    checkServer();
  }, []);

  const checkServer = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/health", {
        signal: AbortSignal.timeout(3000),
      });
      setServerOnline(res.ok);
    } catch {
      setServerOnline(false);
    }
  };

  if (hasAccess === null) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          color: "var(--text-muted)",
        }}
      >
        Loading...
      </div>
    );
  }

  if (!hasAccess) {
    return (
      <div style={{ padding: "40px" }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            maxWidth: 600,
            margin: "80px auto",
            textAlign: "center",
          }}
        >
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: "50%",
              background: "rgba(239,68,68,0.1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 24px",
            }}
          >
            <XCircle size={40} color="#ef4444" />
          </div>
          <h2
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "var(--text-primary)",
              marginBottom: 12,
            }}
          >
            Access Denied
          </h2>
          <p style={{ color: "var(--text-muted)", marginBottom: 24, lineHeight: 1.6 }}>
            The CloudShell terminal requires <strong>Admin</strong> or{" "}
            <strong>DevOps</strong> role.
            <br />
            Your current role: <span style={{ color: "#f59e0b", fontWeight: 600 }}>{role || "Unknown"}</span>
          </p>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Contact your team administrator to request elevated access.
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div style={{ height: "calc(100vh - var(--topbar-height, 64px))", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div
        style={{
          padding: "20px 32px 16px",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "var(--radius-md)",
                background: "linear-gradient(135deg, rgba(6,182,212,0.15), rgba(99,102,241,0.15))",
                border: "1px solid rgba(6,182,212,0.2)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <TerminalIcon size={22} color="#06b6d4" />
            </div>
            <div>
              <h1
                style={{
                  fontSize: "1.25rem",
                  fontWeight: 700,
                  color: "var(--text-primary)",
                  letterSpacing: "-0.01em",
                }}
              >
                CloudShell
              </h1>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 2 }}>
                Browser-based terminal • Terraform, AWS CLI, Infracost, OPA
                {" · "}
                <a
                  href="https://github.com/Eternal-prithivi/aws-provision-using-terraform/blob/main/docs/README.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    color: "#22d3ee",
                    textDecoration: "none",
                    fontWeight: 600,
                    borderBottom: "1px dotted rgba(34,211,238,0.3)",
                  }}
                >
                  Docs ↗
                </a>
              </p>
            </div>
          </div>

          {/* Info badges */}
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            {/* Server Status Badge */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "5px 12px",
                borderRadius: "var(--radius-sm)",
                background: serverOnline
                  ? "rgba(34,197,94,0.1)"
                  : serverOnline === false
                  ? "rgba(239,68,68,0.1)"
                  : "rgba(245,158,11,0.1)",
                border: `1px solid ${
                  serverOnline
                    ? "rgba(34,197,94,0.15)"
                    : serverOnline === false
                    ? "rgba(239,68,68,0.15)"
                    : "rgba(245,158,11,0.15)"
                }`,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onClick={checkServer}
              title="Click to recheck server status"
            >
              {serverOnline ? (
                <Wifi size={14} color="#22c55e" />
              ) : serverOnline === false ? (
                <WifiOff size={14} color="#ef4444" />
              ) : (
                <RefreshCw size={14} color="#f59e0b" style={{ animation: "spin 1s linear infinite" }} />
              )}
              <span style={{
                fontSize: "0.72rem",
                fontWeight: 600,
                color: serverOnline ? "#4ade80" : serverOnline === false ? "#f87171" : "#fbbf24",
              }}>
                {serverOnline ? "Server Online" : serverOnline === false ? "Server Offline" : "Checking..."}
              </span>
            </div>
            
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "5px 12px",
                borderRadius: "var(--radius-sm)",
                background: "rgba(34,197,94,0.1)",
                border: "1px solid rgba(34,197,94,0.15)",
              }}
            >
              <ShieldCheck size={14} color="#22c55e" />
              <span style={{ fontSize: "0.72rem", color: "#4ade80", fontWeight: 600 }}>
                {role.toUpperCase()}
              </span>
            </div>
            {sessionId && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "5px 12px",
                  borderRadius: "var(--radius-sm)",
                  background: "rgba(99,102,241,0.1)",
                  border: "1px solid rgba(99,102,241,0.15)",
                }}
              >
                <Info size={14} color="#818cf8" />
                <span style={{ fontSize: "0.72rem", color: "#818cf8", fontWeight: 600 }}>
                  Session: {sessionId}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Terminal */}
      <div style={{ flex: 1, overflow: "hidden" }}>
        <TerminalComponent
          username={username}
          role={role}
          onSessionStart={(sid) => setSessionId(sid)}
          onSessionEnd={() => setSessionId("")}
        />
      </div>
    </div>
  );
}
