"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Server,
  ShieldCheck,
  DollarSign,
  Activity,
  Cloud,
  Database,
  HardDrive,
  Lock,
  Eye,
  Globe,
  Layers,
  CheckCircle,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import type { DashboardData, AuditEvent } from "@/lib/api";
import { fetchDashboard } from "@/lib/api";

const SERVICE_META: Record<string, { icon: typeof Server; label: string; color: string }> = {
  vpc: { icon: Globe, label: "VPC", color: "#3b82f6" },
  ec2: { icon: Server, label: "EC2", color: "#8b5cf6" },
  s3: { icon: HardDrive, label: "S3", color: "#22c55e" },
  iam: { icon: Lock, label: "IAM", color: "#f59e0b" },
  cloudwatch: { icon: Eye, label: "CloudWatch", color: "#ec4899" },
  dynamodb: { icon: Database, label: "DynamoDB", color: "#06b6d4" },
};

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] as const } },
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return (
      <div style={{ textAlign: "center", padding: "80px 20px" }}>
        <XCircle size={48} color="var(--accent-red)" style={{ margin: "0 auto 16px" }} />
        <h2 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: 8 }}>
          Backend Unavailable
        </h2>
        <p style={{ color: "var(--text-secondary)", maxWidth: 400, margin: "0 auto" }}>
          Could not connect to the API at localhost:8000. Make sure the FastAPI server
          is running:{" "}
          <code style={{ color: "var(--accent-blue)" }}>
            cd web-ui/api && uvicorn server:app --reload --port 8000
          </code>
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 20 }}>
        {[...Array(4)].map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 160, borderRadius: "var(--radius-lg)" }} />
        ))}
      </div>
    );
  }

  const policyIcon =
    data.policy_health.status === "clean" ? CheckCircle :
    data.policy_health.status === "warnings" ? AlertTriangle : XCircle;
  const policyColor =
    data.policy_health.status === "clean" ? "var(--accent-green)" :
    data.policy_health.status === "warnings" ? "var(--accent-amber)" : "var(--accent-red)";

  const driftColor =
    data.drift_status === "clean" ? "var(--accent-green)" :
    data.drift_status === "drift_detected" ? "var(--accent-red)" : "var(--text-muted)";

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* ── Status Cards ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 20,
          marginBottom: 32,
        }}
      >
        {/* Services Card */}
        <motion.div variants={item} className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
            <div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.05em" }}>
                Active Services
              </p>
              <p style={{ fontSize: "2rem", fontWeight: 800, marginTop: 4 }}>
                {data.active_count}
                <span style={{ fontSize: "1rem", color: "var(--text-muted)", fontWeight: 400 }}> / 6</span>
              </p>
            </div>
            <div style={{ width: 44, height: 44, borderRadius: "var(--radius-sm)", background: "var(--accent-blue-glow)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Layers size={22} color="var(--accent-blue)" />
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {Object.entries(data.services).map(([key, enabled]) => {
              const meta = SERVICE_META[key];
              if (!meta) return null;
              const Icon = meta.icon;
              return (
                <div
                  key={key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "4px 10px",
                    borderRadius: "var(--radius-sm)",
                    background: enabled ? `${meta.color}15` : "var(--bg-input)",
                    border: `1px solid ${enabled ? `${meta.color}30` : "var(--border-subtle)"}`,
                    fontSize: "0.75rem",
                    fontWeight: 500,
                    color: enabled ? meta.color : "var(--text-muted)",
                  }}
                >
                  <Icon size={12} />
                  {meta.label}
                </div>
              );
            })}
          </div>
        </motion.div>

        {/* Policy Health Card */}
        <motion.div variants={item} className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
            <div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.05em" }}>
                Policy Health
              </p>
              <p style={{ fontSize: "2rem", fontWeight: 800, marginTop: 4, color: policyColor, textTransform: "capitalize" }}>
                {data.policy_health.status}
              </p>
            </div>
            <div style={{ width: 44, height: 44, borderRadius: "var(--radius-sm)", background: `${policyColor}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>
              {(() => { const PI = policyIcon; return <PI size={22} color={policyColor} />; })()}
            </div>
          </div>
          <div style={{ display: "flex", gap: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent-red)" }} />
              <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{data.policy_health.blocks} Blocks</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent-amber)" }} />
              <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{data.policy_health.warnings} Warnings</span>
            </div>
          </div>
        </motion.div>

        {/* Cost Card */}
        <motion.div variants={item} className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
            <div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.05em" }}>
                Est. Monthly Cost
              </p>
              <p style={{ fontSize: "2rem", fontWeight: 800, marginTop: 4 }}>
                $0<span style={{ fontSize: "1rem", color: "var(--text-muted)", fontWeight: 400 }}>.00</span>
              </p>
            </div>
            <div style={{ width: 44, height: 44, borderRadius: "var(--radius-sm)", background: "var(--accent-green-glow)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <DollarSign size={22} color="var(--accent-green)" />
            </div>
          </div>
          <p style={{ fontSize: "0.8rem", color: "var(--accent-green)" }}>
            ✓ Within free tier
          </p>
        </motion.div>

        {/* Drift Card */}
        <motion.div variants={item} className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
            <div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.05em" }}>
                Drift Status
              </p>
              <p style={{ fontSize: "2rem", fontWeight: 800, marginTop: 4, color: driftColor, textTransform: "capitalize" }}>
                {data.drift_status.replace("_", " ")}
              </p>
            </div>
            <div style={{ width: 44, height: 44, borderRadius: "var(--radius-sm)", background: `${driftColor}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Activity size={22} color={driftColor} />
            </div>
          </div>
          <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            Run a scan from the Drift page
          </p>
        </motion.div>
      </div>

      {/* ── Recent Activity ── */}
      <motion.div variants={item} className="glass-card" style={{ padding: "24px" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 16 }}>
          Recent Activity
        </h3>
        {data.recent_events.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", textAlign: "center", padding: "24px 0" }}>
            No audit events yet. Deploy something to see activity here.
          </p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Environment</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_events.map((evt: AuditEvent, i: number) => (
                <tr key={evt.event_id ?? i}>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>
                    {evt.timestamp ? new Date(evt.timestamp).toLocaleString() : "—"}
                  </td>
                  <td>{evt.action}</td>
                  <td>{evt.actor}</td>
                  <td>
                    <span className={`badge ${evt.environment === "production" ? "badge-block" : "badge-info"}`}>
                      {evt.environment}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${evt.status === "success" ? "badge-success" : evt.status === "failed" ? "badge-block" : "badge-warning"}`}>
                      {evt.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </motion.div>
    </motion.div>
  );
}
