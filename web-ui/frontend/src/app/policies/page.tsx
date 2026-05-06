"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, ShieldAlert, Check, AlertTriangle, XCircle, Loader2, Play, Plus, X } from "lucide-react";
import type { PolicyRule, ConfigPayload, ValidationResult } from "@/lib/api";
import { fetchYamlPolicies, fetchOpaPolicies, evaluatePolicies, addCustomPolicy } from "@/lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } };

export default function PoliciesPage() {
  const [tab, setTab] = useState<"yaml" | "opa">("yaml");
  const [yamlRules, setYamlRules] = useState<PolicyRule[]>([]);
  const [opaRules, setOpaRules] = useState<PolicyRule[]>([]);
  const [opaAvailable, setOpaAvailable] = useState(true);
  const [testResult, setTestResult] = useState<ValidationResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [configJson, setConfigJson] = useState(JSON.stringify({ instance_type: "t2.micro", s3_encryption: true, tags: { project: "test" }, environment: "free-tier" }, null, 2));

  // Custom Policy Form
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", severity: "warning", condition: "" });
  const [addError, setAddError] = useState("");

  const refreshRules = () => {
    fetchYamlPolicies().then((d) => setYamlRules(d.rules)).catch(() => {});
    fetchOpaPolicies().then((d) => { setOpaRules(d.rules); setOpaAvailable(d.opa_available); }).catch(() => {});
  };

  useEffect(() => {
    refreshRules();
  }, []);

  const runTest = async () => {
    setTesting(true);
    try {
      const parsed = JSON.parse(configJson);
      const res = await evaluatePolicies(parsed as ConfigPayload);
      setTestResult(res);
    } catch { /* ignore */ }
    setTesting(false);
  };

  const handleAddPolicy = async () => {
    setAddError("");
    try {
      await addCustomPolicy(form);
      setShowAdd(false);
      setForm({ name: "", description: "", severity: "warning", condition: "" });
      refreshRules();
    } catch (e: any) {
      setAddError(e.message ?? "Failed to add policy");
    }
  };

  const rules = tab === "yaml" ? yamlRules : opaRules;

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Tabs */}
      <motion.div variants={item} style={{ display: "flex", gap: 4, marginBottom: 24, background: "var(--bg-card)", borderRadius: "var(--radius-sm)", padding: 4, width: "fit-content" }}>
        {(["yaml", "opa"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "8px 20px", borderRadius: "var(--radius-sm)", fontSize: "0.85rem", fontWeight: 600, cursor: "pointer",
            background: tab === t ? "var(--accent-blue)" : "transparent", color: tab === t ? "white" : "var(--text-secondary)", border: "none", transition: "all 0.2s ease",
          }}>
            {t === "yaml" ? "YAML Rules (8)" : `OPA Rules (${opaRules.length})`}
          </button>
        ))}
      </motion.div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 24 }}>
        {/* Rules Table */}
        <motion.div variants={item} className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h3 style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
              <ShieldCheck size={18} color="var(--accent-blue)" />
              {tab === "yaml" ? "YAML Policy Rules" : "OPA Rego Rules"}
            </h3>
            {tab === "yaml" && (
              <button className="btn-primary" onClick={() => setShowAdd(!showAdd)} style={{ fontSize: "0.8rem", padding: "6px 12px" }}>
                <Plus size={14} /> Add Rule
              </button>
            )}
          </div>
          
          {/* Add Policy Form */}
          {showAdd && tab === "yaml" && (
            <div style={{ padding: 16, background: "var(--bg-input)", borderRadius: "var(--radius-md)", marginBottom: 20, border: "1px solid var(--border-subtle)" }}>
              <h4 style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: 12 }}>New Custom Policy</h4>
              <div style={{ display: "grid", gap: 12 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <input className="input" placeholder="Rule name (e.g. restrict_instance)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                  <select className="select" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
                    <option value="warning">Warning</option>
                    <option value="block">Block</option>
                  </select>
                </div>
                <input className="input" placeholder="Description of the rule" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                <input className="input" placeholder="Condition (e.g. instance_type == 't2.micro')" value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })} style={{ fontFamily: "var(--font-mono)" }} />
              </div>
              {addError && <p style={{ color: "var(--accent-red)", fontSize: "0.8rem", marginTop: 8 }}>{addError}</p>}
              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <button className="btn-primary" onClick={handleAddPolicy} style={{ padding: "6px 16px", fontSize: "0.8rem" }}><Check size={14} /> Save</button>
                <button className="btn-secondary" onClick={() => setShowAdd(false)} style={{ padding: "6px 16px", fontSize: "0.8rem" }}><X size={14} /> Cancel</button>
              </div>
            </div>
          )}

          {!opaAvailable && tab === "opa" && (
            <div style={{ padding: 12, background: "var(--accent-amber-glow)", borderRadius: "var(--radius-sm)", marginBottom: 16, fontSize: "0.8rem", color: "var(--accent-amber)" }}>
              ⚠ OPA CLI not installed. These rules will be skipped during evaluation.
            </div>
          )}
          <table className="data-table">
            <thead><tr><th>Rule</th><th>Description</th><th>Severity</th></tr></thead>
            <tbody>
              {rules.map((r, i) => (
                <tr key={i}>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "var(--accent-blue)" }}>{r.name}</td>
                  <td>{r.description}</td>
                  <td><span className={`badge ${r.severity === "block" ? "badge-block" : "badge-warning"}`}>{r.severity}</span></td>
                </tr>
              ))}
              {rules.length === 0 && <tr><td colSpan={3} style={{ textAlign: "center", color: "var(--text-muted)", padding: 24 }}>Loading rules...</td></tr>}
            </tbody>
          </table>
        </motion.div>

        {/* Test Runner */}
        <motion.div variants={item} className="glass-card" style={{ padding: 20, alignSelf: "start" }}>
          <h4 style={{ fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <ShieldAlert size={16} color="var(--accent-purple)" /> Test Config
          </h4>
          <textarea
            className="input" value={configJson} onChange={(e) => setConfigJson(e.target.value)}
            style={{ height: 180, fontFamily: "var(--font-mono)", fontSize: "0.75rem", resize: "vertical", marginBottom: 12 }}
          />
          <button className="btn-primary" onClick={runTest} disabled={testing} style={{ width: "100%" }}>
            {testing ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Play size={14} />}
            Run Policy Check
          </button>
          {testResult && (
            <div style={{ marginTop: 16, fontSize: "0.8rem" }}>
              <div style={{ display: "flex", gap: 12, marginBottom: 8 }}>
                <span className="badge badge-block">{testResult.summary.total_blocks} blocks</span>
                <span className="badge badge-warning">{testResult.summary.total_warnings} warnings</span>
              </div>
              {testResult.summary.can_deploy ? (
                <p style={{ color: "var(--accent-green)", display: "flex", alignItems: "center", gap: 6 }}><Check size={14} /> Ready to deploy</p>
              ) : (
                <p style={{ color: "var(--accent-red)", display: "flex", alignItems: "center", gap: 6 }}><XCircle size={14} /> Blocked</p>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}
