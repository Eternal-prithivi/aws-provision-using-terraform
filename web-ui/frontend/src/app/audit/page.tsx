"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { FileText, Download, Search, Filter } from "lucide-react";
import type { AuditEvent } from "@/lib/api";
import { fetchAuditEvents, fetchAuditReport } from "@/lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } };

function AuditContent() {
  const searchParams = useSearchParams();
  const initialActor = searchParams.get("actor") || "";

  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [filterActor, setFilterActor] = useState(initialActor);
  const [filterEnv, setFilterEnv] = useState("");
  const [filterAction, setFilterAction] = useState("");

  const loadData = async (forceActor?: string) => {
    try {
      const params: Record<string, string | number> = { limit: 100 };
      const actorToUse = forceActor !== undefined ? forceActor : filterActor;
      if (actorToUse) params.actor = actorToUse;
      if (filterEnv) params.environment = filterEnv;
      if (filterAction) params.action = filterAction;
      const res = await fetchAuditEvents(params as { actor?: string; environment?: string; action?: string; limit?: number });
      setEvents(res.events);
    } catch { /* ignore */ }
    try { const r = await fetchAuditReport(); setReport(r as Record<string, unknown>); } catch { /* ignore */ }
  };

  useEffect(() => { 
    if (initialActor !== undefined) {
      setFilterActor(initialActor);
      loadData(initialActor);
    } else {
      loadData();
    }
  }, [initialActor]); // re-run if URL query param changes

  const handleFilter = () => { loadData(); };

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(events, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "audit-events.json"; a.click();
    URL.revokeObjectURL(url);
  };

  const totalEvents = (report as { total_events?: number })?.total_events ?? events.length;
  const byAction = (report as { by_action?: Record<string, number> })?.by_action ?? {};
  const byEnv = (report as { by_environment?: Record<string, number> })?.by_environment ?? {};

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Summary Cards */}
      <motion.div variants={item} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
        <div className="glass-card" style={{ padding: 16, textAlign: "center" }}>
          <p style={{ fontSize: "1.5rem", fontWeight: 800 }}>{totalEvents}</p>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Total Events</p>
        </div>
        {Object.entries(byAction).slice(0, 3).map(([action, count]) => (
          <div key={action} className="glass-card" style={{ padding: 16, textAlign: "center" }}>
            <p style={{ fontSize: "1.5rem", fontWeight: 800 }}>{count}</p>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{action}</p>
          </div>
        ))}
        {Object.entries(byEnv).slice(0, 2).map(([env, count]) => (
          <div key={env} className="glass-card" style={{ padding: 16, textAlign: "center" }}>
            <p style={{ fontSize: "1.5rem", fontWeight: 800 }}>{count}</p>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{env}</p>
          </div>
        ))}
      </motion.div>

      {/* Filters */}
      <motion.div variants={item} style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "end" }}>
        <div>
          <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Actor</label>
          <input className="input" style={{ width: 160 }} placeholder="username" value={filterActor} onChange={(e) => setFilterActor(e.target.value)} />
        </div>
        <div>
          <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Environment</label>
          <select className="select" style={{ width: 160 }} value={filterEnv} onChange={(e) => setFilterEnv(e.target.value)}>
            <option value="">All</option>
            <option value="production">production</option>
            <option value="staging">staging</option>
            <option value="free-tier">free-tier</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: "0.7rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Action</label>
          <input className="input" style={{ width: 160 }} placeholder="deploy, approve..." value={filterAction} onChange={(e) => setFilterAction(e.target.value)} />
        </div>
        <button className="btn-primary" onClick={handleFilter} style={{ height: 40 }}>
          <Filter size={14} /> Filter
        </button>
        <button className="btn-secondary" onClick={exportJson} style={{ height: 40 }}>
          <Download size={14} /> Export JSON
        </button>
      </motion.div>

      {/* Events Table */}
      <motion.div variants={item} className="glass-card" style={{ padding: 24 }}>
        <h3 style={{ fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <FileText size={18} color="var(--accent-blue)" /> Audit Events
        </h3>
        {events.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <Search size={32} color="var(--text-muted)" style={{ margin: "0 auto 12px" }} />
            <p style={{ color: "var(--text-muted)" }}>No audit events found. Deploy infrastructure to generate events.</p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr><th>Timestamp</th><th>Action</th><th>Actor</th><th>Environment</th><th>Status</th><th>Details</th></tr>
              </thead>
              <tbody>
                {events.map((e, i) => (
                  <tr key={e.event_id ?? i}>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", whiteSpace: "nowrap" }}>
                      {e.timestamp ? new Date(e.timestamp).toLocaleString() : "—"}
                    </td>
                    <td><span className="badge badge-info">{e.action}</span></td>
                    <td>{e.actor}</td>
                    <td><span className={`badge ${e.environment === "production" ? "badge-block" : "badge-success"}`}>{e.environment}</span></td>
                    <td><span className={`badge ${e.status === "success" ? "badge-success" : e.status === "failed" ? "badge-block" : "badge-warning"}`}>{e.status}</span></td>
                    <td style={{ fontSize: "0.8rem", color: "var(--text-muted)", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{e.details && typeof e.details === "object" ? JSON.stringify(e.details) : (e.details ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

export default function AuditPage() {
  return (
    <Suspense fallback={<div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>Loading audit logs...</div>}>
      <AuditContent />
    </Suspense>
  );
}
