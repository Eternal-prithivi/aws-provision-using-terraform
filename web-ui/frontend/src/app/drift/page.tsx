"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, RefreshCw, CheckCircle, XCircle, AlertTriangle, FileText, Loader2, Wrench, ShieldAlert } from "lucide-react";
import type { DriftStatus } from "@/lib/api";
import { fetchDriftStatus, streamSSE, triggerDriftRemediation } from "@/lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } };

export default function DriftPage() {
  const [drift, setDrift] = useState<DriftStatus | null>(null);
  const [scanning, setScanning] = useState(false);
  const [remediating, setRemediating] = useState(false);
  const [scanOutput, setScanOutput] = useState<string[]>([]);

  useEffect(() => {
    fetchDriftStatus().then(setDrift).catch(() => {});
  }, []);

  const triggerScan = () => {
    setScanning(true);
    setScanOutput([]);
    streamSSE(
      "/api/drift/scan",
      (line) => setScanOutput((prev) => [...prev, line]),
      (code) => {
        setScanning(false);
        setScanOutput((prev) => [...prev, `\n>>> Scan complete (exit code: ${code})`]);
        fetchDriftStatus().then(setDrift).catch(() => {});
      },
      (err) => {
        setScanning(false);
        setScanOutput((prev) => [...prev, `ERROR: ${err.message}`]);
      },
    );
  };

  const handleRemediate = async (checkOnly: boolean) => {
    setRemediating(true);
    setScanOutput([`>>> Starting remediation (${checkOnly ? "Dry Run" : "Apply"})...`]);
    try {
      const res = await triggerDriftRemediation(checkOnly, !checkOnly);
      setScanOutput((prev) => [...prev, res.message]);
      fetchDriftStatus().then(setDrift).catch(() => {});
    } catch (err: any) {
      setScanOutput((prev) => [...prev, `ERROR: ${err.message}`]);
    }
    setRemediating(false);
  };

  const statusConfig = {
    clean: { icon: CheckCircle, color: "var(--accent-green)", label: "No Drift", bg: "var(--accent-green-glow)" },
    drift_detected: { icon: XCircle, color: "var(--accent-red)", label: "Drift Detected", bg: "var(--accent-red-glow)" },
    error: { icon: AlertTriangle, color: "var(--accent-amber)", label: "Error", bg: "var(--accent-amber-glow)" },
    no_report: { icon: Activity, color: "var(--text-muted)", label: "No Report", bg: "var(--bg-input)" },
    unknown: { icon: Activity, color: "var(--text-muted)", label: "Unknown", bg: "var(--bg-input)" },
  };

  const sc = statusConfig[(drift?.status as keyof typeof statusConfig) ?? "unknown"] ?? statusConfig.unknown;
  const StatusIcon = sc.icon;

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Status Banner */}
      <motion.div variants={item} className="glass-card" style={{ padding: 28, marginBottom: 24, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ width: 56, height: 56, borderRadius: "var(--radius-md)", background: sc.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <StatusIcon size={28} color={sc.color} />
          </div>
          <div>
            <h3 style={{ fontSize: "1.5rem", fontWeight: 800, color: sc.color }}>{sc.label}</h3>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}>
              {drift?.timestamp ? `Last scan: ${drift.timestamp}` : "No scan has been run yet"}
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          {drift?.status === "drift_detected" && (
            <button className="btn-secondary" onClick={() => handleRemediate(true)} disabled={scanning || remediating}
              style={{ borderColor: "var(--accent-amber)", color: "var(--accent-amber)" }}>
              <Wrench size={16} /> Dry Run Fix
            </button>
          )}
          {drift?.status === "drift_detected" && (
            <button className="btn-danger" onClick={() => handleRemediate(false)} disabled={scanning || remediating}>
              <ShieldAlert size={16} /> Apply Fix
            </button>
          )}
          <button className="btn-primary" onClick={triggerScan} disabled={scanning || remediating}>
            {scanning ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : <RefreshCw size={16} />}
            {scanning ? "Scanning..." : "Run Scan"}
          </button>
        </div>
      </motion.div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        {/* Drift Report */}
        <motion.div variants={item} className="glass-card" style={{ padding: 24 }}>
          <h4 style={{ fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <FileText size={16} color="var(--accent-blue)" /> Drift Report
          </h4>
          {drift?.report ? (
            <pre style={{
              background: "#0d0d0d", padding: 16, borderRadius: "var(--radius-sm)",
              fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)",
              overflow: "auto", maxHeight: 400, whiteSpace: "pre-wrap", lineHeight: 1.6,
            }}>
              {drift.report}
            </pre>
          ) : (
            <p style={{ color: "var(--text-muted)", textAlign: "center", padding: 40 }}>
              {drift?.message ?? "No drift report available. Click \"Run Scan\" to check."}
            </p>
          )}
        </motion.div>

        {/* Live Scan Output */}
        <motion.div variants={item} className="glass-card" style={{ padding: 24 }}>
          <h4 style={{ fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <Activity size={16} color="var(--accent-purple)" /> Live Scan Output
          </h4>
          {scanOutput.length > 0 ? (
            <div className="terminal" style={{ maxHeight: 400 }}>
              {scanOutput.map((line, i) => (
                <div key={i} className={line.includes("ERROR") ? "error" : line.includes("WARNING") ? "warning" : ""}>
                  {line}
                </div>
              ))}
              {scanning && <span className="animate-pulse-glow">▌</span>}
            </div>
          ) : (
            <p style={{ color: "var(--text-muted)", textAlign: "center", padding: 40 }}>
              Scan output will appear here in real-time.
            </p>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}
