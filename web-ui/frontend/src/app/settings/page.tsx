"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Settings, Shield, Bell, Globe, Clock, DollarSign,
  LogOut, User, Check, Loader2, Save, ChevronRight,
} from "lucide-react";
import { useRouter } from "next/navigation";
import type { AdminSettings } from "@/lib/api";
import { fetchSettings, saveSettings } from "@/lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } };

const AWS_REGIONS = [
  { value: "us-east-1", label: "US East (N. Virginia)" },
  { value: "us-west-2", label: "US West (Oregon)" },
  { value: "eu-west-1", label: "Europe (Ireland)" },
  { value: "eu-central-1", label: "Europe (Frankfurt)" },
  { value: "ap-south-1", label: "Asia Pacific (Mumbai)" },
  { value: "ap-southeast-1", label: "Asia Pacific (Singapore)" },
  { value: "ap-northeast-1", label: "Asia Pacific (Tokyo)" },
];

export default function SettingsPage() {
  const router = useRouter();
  const [isAdmin, setIsAdmin] = useState(false);
  const [user, setUser] = useState<{ name?: string; username?: string; role?: string; method?: string; permissions?: string[] } | null>(null);
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState("profile");

  useEffect(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem("auth_user") || "{}");
      setUser(stored);
      setIsAdmin(stored.role === "admin" || stored.role === "devops");
    } catch {}
    fetchSettings().then((d) => setSettings(d.settings)).catch(() => {});
  }, []);

  const handleSave = async (field: string, value: any) => {
    setSaving(field);
    try {
      const res = await saveSettings({ [field]: value });
      setSettings(res.settings);
      setSaved(field);
      setTimeout(() => setSaved(null), 2000);
    } catch {}
    setSaving(null);
  };

  const handleLogout = () => {
    sessionStorage.removeItem("auth_user");
    router.push("/login");
  };

  const SECTIONS = [
    { key: "profile", label: "Profile", icon: User, desc: "Account info" },
    { key: "notifications", label: "Notifications", icon: Bell, desc: "Slack & alerts" },
    { key: "infrastructure", label: "Infrastructure", icon: Globe, desc: "Defaults" },
    { key: "security", label: "Security", icon: Shield, desc: "Policy enforcement" },
    { key: "billing", label: "Cost Controls", icon: DollarSign, desc: "Budget alerts" },
    { key: "session", label: "Session", icon: Clock, desc: "Timeouts" },
  ];

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 24, maxWidth: 1100, margin: "0 auto" }}>
        {/* Settings Navigation */}
        <motion.div variants={item}>
          <nav style={{ position: "sticky", top: "calc(var(--topbar-height) + 28px)" }}>
            <div className="glass-card" style={{ padding: 8, overflow: "hidden" }}>
              {SECTIONS.map((s) => {
                const Icon = s.icon;
                const active = activeSection === s.key;
                return (
                  <button
                    key={s.key}
                    onClick={() => setActiveSection(s.key)}
                    style={{
                      width: "100%", textAlign: "left", padding: "12px 14px",
                      border: "none", borderRadius: "var(--radius-sm)",
                      background: active ? "linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08))" : "transparent",
                      cursor: "pointer", display: "flex", alignItems: "center", gap: 12,
                      transition: "all 0.2s ease", position: "relative",
                    }}
                    onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "rgba(255,255,255,0.02)"; }}
                    onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
                  >
                    {active && (
                      <div style={{
                        position: "absolute", left: 0, top: "25%", bottom: "25%", width: 3,
                        borderRadius: "0 4px 4px 0",
                        background: "linear-gradient(180deg, #6366f1, #a855f7)",
                      }} />
                    )}
                    <div style={{
                      width: 32, height: 32, borderRadius: "var(--radius-xs)",
                      background: active ? "rgba(99,102,241,0.15)" : "var(--bg-input)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <Icon size={16} color={active ? "#818cf8" : "var(--text-muted)"} />
                    </div>
                    <div>
                      <p style={{ fontSize: "0.82rem", fontWeight: active ? 600 : 500, color: active ? "var(--text-primary)" : "var(--text-secondary)" }}>{s.label}</p>
                      <p style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>{s.desc}</p>
                    </div>
                    {active && <ChevronRight size={14} color="var(--text-muted)" style={{ marginLeft: "auto" }} />}
                  </button>
                );
              })}
            </div>

            {/* Logout button at bottom of sidebar nav */}
            <button
              onClick={handleLogout}
              className="btn-danger"
              style={{ width: "100%", marginTop: 16, padding: "10px 16px", fontSize: "0.82rem" }}
            >
              <LogOut size={15} /> Sign Out
            </button>
          </nav>
        </motion.div>

        {/* Settings Content */}
        <motion.div variants={item}>
          {/* Profile Section */}
          {activeSection === "profile" && (
            <div className="glass-card" style={{ padding: 32 }}>
              <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: 24, display: "flex", alignItems: "center", gap: 10 }}>
                <User color="var(--accent-indigo)" size={20} /> User Profile
              </h2>
              
              <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
                {/* Avatar */}
                <div style={{
                  width: 80, height: 80, borderRadius: "var(--radius-lg)",
                  background: "linear-gradient(135deg, #6366f1, #a855f7, #ec4899)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "1.5rem", fontWeight: 800, color: "white",
                  boxShadow: "0 8px 32px rgba(99,102,241,0.3)",
                  flexShrink: 0,
                }}>
                  {user?.name?.substring(0, 2).toUpperCase() || "US"}
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
                    <div>
                      <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 6 }}>Full Name</label>
                      <p style={{ fontSize: "1rem", fontWeight: 600 }}>{user?.name || "—"}</p>
                    </div>
                    <div>
                      <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 6 }}>Username</label>
                      <p style={{ fontSize: "1rem", fontWeight: 600, fontFamily: "var(--font-mono)" }}>@{user?.username || "—"}</p>
                    </div>
                    <div>
                      <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 6 }}>Role</label>
                      <span className={`badge ${user?.role === "admin" ? "badge-purple" : user?.role === "devops" ? "badge-info" : "badge-success"}`}>
                        {user?.role || "viewer"}
                      </span>
                    </div>
                    <div>
                      <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 6 }}>Auth Method</label>
                      <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}>{user?.method === "github_token" ? "GitHub Token" : "Username Lookup"}</p>
                    </div>
                  </div>

                  {/* Permissions */}
                  {user?.permissions && user.permissions.length > 0 && (
                    <div>
                      <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 8 }}>Permissions</label>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {user.permissions.map((p) => (
                          <span key={p} className="badge badge-info" style={{ fontSize: "0.7rem", padding: "3px 10px", fontFamily: "var(--font-mono)" }}>{p}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Notifications Section */}
          {activeSection === "notifications" && (
            <div className="glass-card" style={{ padding: 32 }}>
              <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: 24, display: "flex", alignItems: "center", gap: 10 }}>
                <Bell color="var(--accent-amber)" size={20} /> Notification Settings
              </h2>
              <SettingsRow
                icon={<Bell size={20} color="var(--accent-amber)" />}
                title="Slack Webhook URL"
                description="Configure webhook URL for deployment approvals, drift alerts, and team notifications."
                saving={saving === "slack_webhook_url"}
                saved={saved === "slack_webhook_url"}
              >
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    className="input"
                    placeholder="https://hooks.slack.com/services/..."
                    type="password"
                    defaultValue={settings?.slack_webhook_url || ""}
                    onBlur={(e) => {
                      if (e.target.value !== (settings?.slack_webhook_url || "")) {
                        handleSave("slack_webhook_url", e.target.value);
                      }
                    }}
                    style={{ flex: 1, maxWidth: 420 }}
                  />
                </div>
              </SettingsRow>
            </div>
          )}

          {/* Infrastructure Section */}
          {activeSection === "infrastructure" && (
            <div className="glass-card" style={{ padding: 32 }}>
              <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: 24, display: "flex", alignItems: "center", gap: 10 }}>
                <Globe color="var(--accent-blue)" size={20} /> Infrastructure Defaults
              </h2>
              <SettingsRow
                icon={<Globe size={20} color="var(--accent-blue)" />}
                title="Default AWS Region"
                description="Set the default region for new deployments. Users can still override per-deployment."
                saving={saving === "default_region"}
                saved={saved === "default_region"}
              >
                <select
                  className="select"
                  value={settings?.default_region || "ap-south-1"}
                  onChange={(e) => handleSave("default_region", e.target.value)}
                  style={{ width: 280 }}
                >
                  {AWS_REGIONS.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </SettingsRow>
            </div>
          )}

          {/* Security Section */}
          {activeSection === "security" && (
            <div className="glass-card" style={{ padding: 32 }}>
              <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: 24, display: "flex", alignItems: "center", gap: 10 }}>
                <Shield color="var(--accent-green)" size={20} /> Security & Policy Enforcement
              </h2>
              <SettingsRow
                icon={<Shield size={20} color="var(--accent-green)" />}
                title="Strict Mode"
                description="When enabled, any warning-level violation in YAML or OPA policies will completely block deployments. Recommended for production environments."
                saving={saving === "strict_mode"}
                saved={saved === "strict_mode"}
              >
                <label style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer" }}>
                  <div
                    onClick={() => handleSave("strict_mode", !(settings?.strict_mode ?? false))}
                    style={{
                      width: 48, height: 26, borderRadius: 13,
                      background: settings?.strict_mode
                        ? "linear-gradient(135deg, #6366f1, #4f46e5)"
                        : "var(--bg-input)",
                      border: `1px solid ${settings?.strict_mode ? "rgba(99,102,241,0.3)" : "var(--border-subtle)"}`,
                      position: "relative", cursor: "pointer",
                      transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                      boxShadow: settings?.strict_mode ? "0 0 12px rgba(99,102,241,0.2)" : "none",
                    }}
                  >
                    <div style={{
                      width: 20, height: 20, borderRadius: "50%",
                      background: "white",
                      position: "absolute", top: 2,
                      left: settings?.strict_mode ? 24 : 2,
                      transition: "left 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                      boxShadow: "0 1px 4px rgba(0,0,0,0.2)",
                    }} />
                  </div>
                  <span style={{ fontSize: "0.85rem", fontWeight: 500 }}>
                    {settings?.strict_mode ? "Enabled" : "Disabled"}
                  </span>
                </label>
              </SettingsRow>
            </div>
          )}

          {/* Billing Section */}
          {activeSection === "billing" && (
            <div className="glass-card" style={{ padding: 32 }}>
              <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: 24, display: "flex", alignItems: "center", gap: 10 }}>
                <DollarSign color="var(--accent-green)" size={20} /> Cost Controls
              </h2>
              <SettingsRow
                icon={<DollarSign size={20} color="var(--accent-green)" />}
                title="Cost Alert Threshold"
                description="Monthly cost threshold in USD. If estimated deployment cost exceeds this, an extra confirmation will be required."
                saving={saving === "cost_alert_threshold"}
                saved={saved === "cost_alert_threshold"}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>$</span>
                  <input
                    className="input"
                    type="number"
                    step="0.5"
                    min="0"
                    defaultValue={settings?.cost_alert_threshold ?? 1}
                    onBlur={(e) => {
                      const val = parseFloat(e.target.value);
                      if (!isNaN(val) && val !== settings?.cost_alert_threshold) {
                        handleSave("cost_alert_threshold", val);
                      }
                    }}
                    style={{ width: 120, fontFamily: "var(--font-mono)" }}
                  />
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>USD / month</span>
                </div>
              </SettingsRow>
            </div>
          )}

          {/* Session Section */}
          {activeSection === "session" && (
            <div className="glass-card" style={{ padding: 32 }}>
              <h2 style={{ fontSize: "1.15rem", fontWeight: 700, marginBottom: 24, display: "flex", alignItems: "center", gap: 10 }}>
                <Clock color="var(--accent-cyan)" size={20} /> Session Settings
              </h2>
              <SettingsRow
                icon={<Clock size={20} color="var(--accent-cyan)" />}
                title="Terminal Session Timeout"
                description="Duration of inactivity (in minutes) before a CloudShell terminal session is automatically disconnected."
                saving={saving === "session_timeout_minutes"}
                saved={saved === "session_timeout_minutes"}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input
                    className="input"
                    type="number"
                    min="5"
                    max="120"
                    step="5"
                    defaultValue={settings?.session_timeout_minutes ?? 30}
                    onBlur={(e) => {
                      const val = parseInt(e.target.value);
                      if (!isNaN(val) && val !== settings?.session_timeout_minutes) {
                        handleSave("session_timeout_minutes", val);
                      }
                    }}
                    style={{ width: 100, fontFamily: "var(--font-mono)" }}
                  />
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>minutes</span>
                </div>
              </SettingsRow>
            </div>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}

/** Reusable settings row with icon, description, and save indicator */
function SettingsRow({ icon, title, description, saving, saved, children }: {
  icon: React.ReactNode;
  title: string;
  description: string;
  saving?: boolean;
  saved?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div style={{
      display: "flex", gap: 16, alignItems: "flex-start",
      padding: "20px 0",
      borderBottom: "1px solid var(--border-subtle)",
    }}>
      <div style={{
        padding: 10, background: "var(--bg-input)",
        borderRadius: "var(--radius-md)", flexShrink: 0,
      }}>
        {icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <h3 style={{ fontWeight: 600, fontSize: "0.95rem" }}>{title}</h3>
          {saving && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: "0.72rem", color: "var(--accent-indigo)" }}>
              <Loader2 size={12} style={{ animation: "spin 1s linear infinite" }} /> Saving...
            </span>
          )}
          {saved && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: "0.72rem", color: "var(--accent-green)" }}>
              <Check size={12} /> Saved
            </span>
          )}
        </div>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 14, lineHeight: 1.5 }}>{description}</p>
        {children}
      </div>
    </div>
  );
}
