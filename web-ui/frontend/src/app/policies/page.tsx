"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, ShieldAlert, Check, AlertTriangle, XCircle, Loader2, Play, Plus, X, Trash2, Lock } from "lucide-react";
import type { PolicyRule, ConfigPayload, ValidationResult } from "@/lib/api";
import { fetchYamlPolicies, fetchOpaPolicies, evaluatePolicies, addCustomPolicy, deleteCustomPolicy } from "@/lib/api";

const BUILTIN_RULES = new Set([
  "public_s3_bucket", "open_ssh_port", "open_rdp_port",
  "iam_wildcard_permissions", "expensive_ec2_instance",
  "missing_s3_encryption", "missing_resource_tags", "cloudtrail_disabled",
]);

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
  const [deleting, setDeleting] = useState<string | null>(null);

  // Custom Policy Form
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", severity: "warning", condition: "" });
  const [addError, setAddError] = useState("");
  const [addSuccess, setAddSuccess] = useState("");

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
    setAddSuccess("");
    if (!form.name.trim() || !form.description.trim() || !form.condition.trim()) {
      setAddError("All fields are required");
      return;
    }
    try {
      const result = await addCustomPolicy(form);
      setAddSuccess(result.message || "Rule added successfully");
      setShowAdd(false);
      setForm({ name: "", description: "", severity: "warning", condition: "" });
      refreshRules();
      setTimeout(() => setAddSuccess(""), 3000);
    } catch (e: any) {
      setAddError(e.message ?? "Failed to add policy");
    }
  };

  const handleDeletePolicy = async (ruleName: string) => {
    if (!confirm(`Delete custom rule "${ruleName}"? This cannot be undone.`)) return;
    setDeleting(ruleName);
    try {
      await deleteCustomPolicy(ruleName);
      refreshRules();
    } catch (e: any) {
      alert(e.message ?? "Failed to delete policy");
    }
    setDeleting(null);
  };

  const rules = tab === "yaml" ? yamlRules : opaRules;
  const builtinCount = yamlRules.filter(r => BUILTIN_RULES.has(r.name)).length;
  const customCount = yamlRules.length - builtinCount;

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Tabs */}
      <motion.div variants={item} style={{ display: "flex", gap: 4, marginBottom: 24, background: "var(--bg-card)", borderRadius: "var(--radius-sm)", padding: 4, width: "fit-content" }}>
        {(["yaml", "opa"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "8px 20px", borderRadius: "var(--radius-sm)", fontSize: "0.85rem", fontWeight: 600, cursor: "pointer",
            background: tab === t ? "var(--accent-blue)" : "transparent", color: tab === t ? "white" : "var(--text-secondary)", border: "none", transition: "all 0.2s ease",
          }}>
            {t === "yaml" ? `YAML Rules (${yamlRules.length})` : `OPA Rules (${opaRules.length})`}
          </button>
        ))}
      </motion.div>

      {/* Success Banner */}
      {addSuccess && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} style={{
          padding: "10px 16px", background: "var(--accent-green-glow)", border: "1px solid rgba(16,185,129,0.2)",
          borderRadius: "var(--radius-sm)", marginBottom: 16, fontSize: "0.85rem", color: "var(--accent-green)",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <Check size={16} /> {addSuccess}
        </motion.div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 24 }}>
        {/* Rules Table */}
        <motion.div variants={item} className="glass-card" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div>
              <h3 style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <ShieldCheck size={18} color="var(--accent-blue)" />
                {tab === "yaml" ? "YAML Policy Rules" : "OPA Rego Rules"}
              </h3>
              {tab === "yaml" && customCount > 0 && (
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  {builtinCount} built-in · {customCount} custom
                </p>
              )}
            </div>
            {tab === "yaml" && (
              <button className="btn-primary" onClick={() => setShowAdd(!showAdd)} style={{ fontSize: "0.8rem", padding: "6px 12px" }}>
                {showAdd ? <X size={14} /> : <Plus size={14} />} {showAdd ? "Cancel" : "Add Rule"}
              </button>
            )}
          </div>
          
          {/* Add Policy Form */}
          {showAdd && tab === "yaml" && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              style={{ padding: 20, background: "linear-gradient(135deg, rgba(99,102,241,0.06), rgba(168,85,247,0.04))", borderRadius: "var(--radius-md)", marginBottom: 20, border: "1px solid rgba(99,102,241,0.15)" }}
            >
              <h4 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
                <Plus size={16} color="var(--accent-indigo)" /> Create Custom Policy
              </h4>
              <div style={{ display: "grid", gap: 14 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 140px", gap: 12 }}>
                  <div>
                    <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 6 }}>Rule Name</label>
                    <input className="input" placeholder="e.g. restrict_large_instances" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value.replace(/\s/g, "_").toLowerCase() })} style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem" }} />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 6 }}>Severity</label>
                    <select className="select" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
                      <option value="warning">⚠ Warning</option>
                      <option value="block">🛑 Block</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 6 }}>Description</label>
                  <input className="input" placeholder="Human-readable description of what this rule checks" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                </div>
                <div>
                  <label style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: 6 }}>Condition</label>
                  <input className="input" placeholder="e.g. instance_type not in ['t2.micro', 't3.micro']" value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })} style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem" }} />
                  <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 6 }}>
                    Python expression evaluated against the config dict. Available keys: instance_type, s3_bucket_public, s3_encryption, ssh_open_to_world, iam_wildcard, tags, cloudtrail_enabled, environment
                  </p>
                </div>
              </div>
              {addError && <p style={{ color: "var(--accent-red)", fontSize: "0.8rem", marginTop: 10 }}>{addError}</p>}
              <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
                <button className="btn-secondary" onClick={() => { setShowAdd(false); setAddError(""); }} style={{ padding: "8px 18px", fontSize: "0.82rem" }}>Cancel</button>
                <button className="btn-primary" onClick={handleAddPolicy} style={{ padding: "8px 18px", fontSize: "0.82rem" }}><Check size={14} /> Save Rule</button>
              </div>
            </motion.div>
          )}

          {!opaAvailable && tab === "opa" && (
            <div style={{ padding: 12, background: "var(--accent-amber-glow)", borderRadius: "var(--radius-sm)", marginBottom: 16, fontSize: "0.8rem", color: "var(--accent-amber)" }}>
              ⚠ OPA CLI not installed. These rules will be skipped during evaluation.
            </div>
          )}
          <table className="data-table">
            <thead><tr><th>Rule</th><th>Description</th><th>Severity</th>{tab === "yaml" && <th style={{ width: 60 }}>Type</th>}{tab === "yaml" && <th style={{ width: 50 }}></th>}</tr></thead>
            <tbody>
              {rules.map((r, i) => {
                const isBuiltin = BUILTIN_RULES.has(r.name);
                return (
                  <tr key={i} style={{ opacity: deleting === r.name ? 0.4 : 1, transition: "opacity 0.3s" }}>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: isBuiltin ? "var(--accent-blue)" : "var(--accent-purple)" }}>{r.name}</td>
                    <td>{r.description}</td>
                    <td><span className={`badge ${r.severity === "block" ? "badge-block" : "badge-warning"}`}>{r.severity}</span></td>
                    {tab === "yaml" && (
                      <td>
                        {isBuiltin ? (
                          <span className="badge badge-info" style={{ fontSize: "0.65rem", padding: "2px 8px", display: "inline-flex", alignItems: "center", gap: 3 }}>
                            <Lock size={10} /> Core
                          </span>
                        ) : (
                          <span className="badge badge-purple" style={{ fontSize: "0.65rem", padding: "2px 8px" }}>Custom</span>
                        )}
                      </td>
                    )}
                    {tab === "yaml" && (
                      <td>
                        {!isBuiltin && (
                          <button
                            onClick={() => handleDeletePolicy(r.name)}
                            disabled={deleting === r.name}
                            style={{
                              background: "transparent", border: "none", cursor: "pointer",
                              color: "var(--text-muted)", padding: 4, borderRadius: "var(--radius-xs)",
                              transition: "all 0.2s",
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.color = "var(--accent-red)"; e.currentTarget.style.background = "var(--accent-red-glow)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-muted)"; e.currentTarget.style.background = "transparent"; }}
                            title={`Delete rule "${r.name}"`}
                          >
                            {deleting === r.name ? <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> : <Trash2 size={14} />}
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
              {rules.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)", padding: 24 }}>Loading rules...</td></tr>}
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

              {/* Detailed violations */}
              {(testResult.yaml.blocks.length > 0 || testResult.yaml.warnings.length > 0) && (
                <div style={{ marginTop: 12, padding: 12, background: "var(--bg-input)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
                  <p style={{ fontWeight: 600, fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.04em" }}>Details</p>
                  {[...testResult.yaml.blocks, ...testResult.yaml.warnings].map((v, i) => (
                    <div key={i} style={{ padding: "6px 0", borderBottom: i < testResult.yaml.blocks.length + testResult.yaml.warnings.length - 1 ? "1px solid var(--border-subtle)" : "none" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        {v.severity === "block" ? <XCircle size={12} color="var(--accent-red)" /> : <AlertTriangle size={12} color="var(--accent-amber)" />}
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: v.severity === "block" ? "var(--accent-red)" : "var(--accent-amber)" }}>{v.rule_name}</span>
                      </div>
                      <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 2, marginLeft: 18 }}>{v.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}
