"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Settings, Shield, Bell, Key, Database, Globe } from "lucide-react";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } };

export default function SettingsPage() {
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    try {
      const user = JSON.parse(sessionStorage.getItem("auth_user") || "{}");
      setIsAdmin(user.role === "admin");
    } catch {}
  }, []);

  if (!isAdmin) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "50vh" }}>
        <p style={{ color: "var(--accent-red)", fontWeight: 600 }}>Access Denied: Administrator privileges required.</p>
      </div>
    );
  }

  return (
    <motion.div variants={container} initial="hidden" animate="show" style={{ maxWidth: 800, margin: "0 auto" }}>
      <motion.div variants={item} className="glass-card" style={{ padding: 32, marginBottom: 24 }}>
        <h2 style={{ fontSize: "1.2rem", fontWeight: 700, display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
          <Settings color="var(--accent-indigo)" /> Global Settings
        </h2>
        
        <div style={{ display: "grid", gap: 24 }}>
          {/* Notifications config */}
          <div style={{ display: "flex", gap: 16, alignItems: "flex-start", paddingBottom: 24, borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{ padding: 10, background: "var(--bg-input)", borderRadius: "var(--radius-md)" }}><Bell size={20} color="var(--accent-amber)" /></div>
            <div style={{ flex: 1 }}>
              <h3 style={{ fontWeight: 600, fontSize: "0.95rem" }}>Slack Integration</h3>
              <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4, marginBottom: 12 }}>Configure webhook URL for deployment approvals and drift alerts.</p>
              <input className="input" placeholder="Enter your Slack webhook URL" type="password" style={{ width: "100%", maxWidth: 400 }} />
            </div>
            <button className="btn-primary" style={{ padding: "6px 16px" }}>Save</button>
          </div>

          {/* Infrastructure config */}
          <div style={{ display: "flex", gap: 16, alignItems: "flex-start", paddingBottom: 24, borderBottom: "1px solid var(--border-subtle)" }}>
            <div style={{ padding: 10, background: "var(--bg-input)", borderRadius: "var(--radius-md)" }}><Globe size={20} color="var(--accent-blue)" /></div>
            <div style={{ flex: 1 }}>
              <h3 style={{ fontWeight: 600, fontSize: "0.95rem" }}>Default AWS Region</h3>
              <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4, marginBottom: 12 }}>Set the default region for new deployments.</p>
              <select className="select" defaultValue="ap-south-1" style={{ width: 200 }}>
                <option value="us-east-1">US East (N. Virginia)</option>
                <option value="ap-south-1">Asia Pacific (Mumbai)</option>
                <option value="eu-central-1">Europe (Frankfurt)</option>
              </select>
            </div>
            <button className="btn-primary" style={{ padding: "6px 16px" }}>Save</button>
          </div>

          {/* Security config */}
          <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
            <div style={{ padding: 10, background: "var(--bg-input)", borderRadius: "var(--radius-md)" }}><Shield size={20} color="var(--accent-green)" /></div>
            <div style={{ flex: 1 }}>
              <h3 style={{ fontWeight: 600, fontSize: "0.95rem" }}>Strict Mode</h3>
              <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4, marginBottom: 12 }}>When enabled, any warning in OPA/YAML policies will completely block deployments.</p>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                <input type="checkbox" style={{ accentColor: "var(--accent-indigo)", width: 16, height: 16 }} />
                <span style={{ fontSize: "0.85rem" }}>Enforce Strict Mode</span>
              </label>
            </div>
            <button className="btn-primary" style={{ padding: "6px 16px" }}>Save</button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
