"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { CloudCog, Key, User, ArrowRight, Loader2, AlertCircle, Shield } from "lucide-react";
import { loginWithToken, loginWithUsername } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [tab, setTab] = useState<"token" | "username">("token");
  const [token, setToken] = useState("");
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async () => {
    setLoading(true);
    setError("");
    try {
      const res = tab === "token"
        ? await loginWithToken(token)
        : await loginWithUsername(username);

      if (res.authenticated) {
        // Store user data in sessionStorage
        sessionStorage.setItem("auth_user", JSON.stringify(res));
        router.push("/");
      } else {
        setError(res.error ?? "Authentication failed");
      }
    } catch {
      setError("Cannot connect to backend. Make sure the API is running on port 8000.");
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "var(--bg-primary)", position: "relative", overflow: "hidden",
    }}>
      {/* Background orbs */}
      <div className="orb" style={{ width: 500, height: 500, top: "-10%", right: "-10%", background: "radial-gradient(circle, rgba(99,102,241,0.15), transparent 70%)" }} />
      <div className="orb" style={{ width: 400, height: 400, bottom: "-5%", left: "-5%", background: "radial-gradient(circle, rgba(168,85,247,0.1), transparent 70%)" }} />
      <div className="orb" style={{ width: 300, height: 300, top: "40%", left: "30%", background: "radial-gradient(circle, rgba(6,182,212,0.06), transparent 70%)" }} />

      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
        style={{
          width: "100%", maxWidth: 440, padding: 40,
          background: "var(--bg-card)", border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-2xl)", backdropFilter: "blur(24px)",
          position: "relative", zIndex: 10,
          boxShadow: "0 24px 80px rgba(0,0,0,0.5), 0 0 120px rgba(99,102,241,0.05)",
        }}
      >
        {/* Logo */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: 32 }}>
          <motion.div
            className="animate-float"
            style={{
              width: 64, height: 64, borderRadius: "var(--radius-lg)",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6, #a855f7)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 8px 32px rgba(99,102,241,0.4)", marginBottom: 20,
            }}
          >
            <CloudCog size={32} color="white" />
          </motion.div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.02em" }}>
            <span className="gradient-text">AWS Provisioner</span>
          </h1>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: 6, textAlign: "center" }}>
            Sign in to manage your infrastructure
          </p>
        </div>

        {/* Auth method tabs */}
        <div style={{
          display: "flex", gap: 4, marginBottom: 24,
          background: "var(--bg-input)", borderRadius: "var(--radius-sm)", padding: 4,
        }}>
          <button
            onClick={() => setTab("token")}
            style={{
              flex: 1, padding: "9px 0", borderRadius: "var(--radius-xs)", fontSize: "0.82rem",
              fontWeight: 600, cursor: "pointer", border: "none",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              background: tab === "token" ? "var(--accent-indigo)" : "transparent",
              color: tab === "token" ? "white" : "var(--text-secondary)",
              transition: "all 0.25s ease",
            }}
          >
            <Key size={14} /> GitHub Token
          </button>
          <button
            onClick={() => setTab("username")}
            style={{
              flex: 1, padding: "9px 0", borderRadius: "var(--radius-xs)", fontSize: "0.82rem",
              fontWeight: 600, cursor: "pointer", border: "none",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              background: tab === "username" ? "var(--accent-indigo)" : "transparent",
              color: tab === "username" ? "white" : "var(--text-secondary)",
              transition: "all 0.25s ease",
            }}
          >
            <User size={14} /> Username
          </button>
        </div>

        {/* Input */}
        {tab === "token" ? (
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: "0.78rem", color: "var(--text-secondary)", display: "block", marginBottom: 6, fontWeight: 500 }}>
              GitHub Personal Access Token
            </label>
            <input
              className="input"
              type="password"
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              style={{ height: 46, fontSize: "0.9rem" }}
            />
            <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 8 }}>
              Generate at{" "}
              <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer"
                style={{ color: "var(--accent-indigo-light)", textDecoration: "none" }}>
                github.com/settings/tokens
              </a>
              {" "}— needs <code style={{ fontSize: "0.65rem", padding: "1px 4px", background: "var(--bg-input)", borderRadius: 4 }}>read:user</code> scope
            </p>
          </div>
        ) : (
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: "0.78rem", color: "var(--text-secondary)", display: "block", marginBottom: 6, fontWeight: 500 }}>
              Username (from teams.yaml)
            </label>
            <input
              className="input"
              placeholder="e.g. prithivi-admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLogin()}
              style={{ height: 46, fontSize: "0.9rem" }}
            />
            <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 8, display: "flex", alignItems: "center", gap: 4 }}>
              <Shield size={10} /> Looks up your role in the team configuration file
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              padding: "10px 14px", background: "var(--accent-red-glow)",
              border: "1px solid rgba(244,63,94,0.2)", borderRadius: "var(--radius-sm)",
              marginBottom: 16, display: "flex", alignItems: "center", gap: 8,
              fontSize: "0.8rem", color: "var(--accent-red)",
            }}
          >
            <AlertCircle size={14} /> {error}
          </motion.div>
        )}

        {/* Login button */}
        <button
          className="btn-primary"
          onClick={handleLogin}
          disabled={loading || (tab === "token" ? !token : !username)}
          style={{ width: "100%", height: 46, fontSize: "0.9rem" }}
        >
          {loading ? (
            <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
          ) : (
            <>Sign In <ArrowRight size={16} /></>
          )}
        </button>

        {/* Security note */}
        <div style={{
          marginTop: 24, padding: "12px 14px",
          background: "rgba(99,102,241,0.04)", borderRadius: "var(--radius-sm)",
          border: "1px solid rgba(99,102,241,0.08)",
        }}>
          <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", textAlign: "center", lineHeight: 1.6 }}>
            🔒 Your token is verified against GitHub&apos;s API and never stored on disk.
            This runs entirely on localhost — zero data leaves your machine.
          </p>
        </div>
      </motion.div>
    </div>
  );
}
