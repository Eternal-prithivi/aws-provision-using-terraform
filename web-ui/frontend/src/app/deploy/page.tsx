"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Globe, Server, HardDrive, Lock, Eye, Database,
  ChevronRight, ChevronLeft, Check, Rocket, AlertTriangle,
  XCircle, Loader2,
} from "lucide-react";
import type { ConfigPayload, Template, ValidationResult, CostEstimate } from "@/lib/api";
import {
  fetchTemplates, validateConfig, generateTfvars,
  fetchCostEstimate, streamSSE,
} from "@/lib/api";

const STEPS = ["Template", "Services", "Environment", "Configure", "Policy Check", "Cost", "Deploy"];

const SERVICE_INFO = [
  { key: "enable_vpc", label: "VPC", desc: "Virtual Private Cloud with subnets", icon: Globe, color: "#3b82f6" },
  { key: "enable_ec2", label: "EC2", desc: "Compute instances (t2.micro free tier)", icon: Server, color: "#8b5cf6" },
  { key: "enable_s3", label: "S3", desc: "Object storage (encrypted, private)", icon: HardDrive, color: "#22c55e" },
  { key: "enable_iam", label: "IAM", desc: "Identity & access management", icon: Lock, color: "#f59e0b" },
  { key: "enable_cloudwatch", label: "CloudWatch", desc: "Monitoring & alarms", icon: Eye, color: "#ec4899" },
  { key: "enable_dynamodb", label: "DynamoDB", desc: "NoSQL database (always free)", icon: Database, color: "#06b6d4" },
];

export default function DeployPage() {
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [config, setConfig] = useState<ConfigPayload>({
    aws_region: "ap-south-1", enable_vpc: false, enable_ec2: false,
    enable_s3: false, enable_iam: false, enable_cloudwatch: false,
    enable_dynamodb: false, instance_type: "t2.micro", bucket_name: "",
    role_name: "app-role", environment: "free-tier", tags: { project: "aws-provisioner" },
    budget_limit: "1", budget_email: "", dynamodb_table_name: "",
    dynamodb_hash_key: "id", dynamodb_hash_key_type: "S",
    dynamodb_read_capacity: 5, dynamodb_write_capacity: 5,
  });
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [cost, setCost] = useState<CostEstimate | null>(null);
  const [termOutput, setTermOutput] = useState<string[]>([]);
  const [deploying, setDeploying] = useState(false);
  const [deployDone, setDeployDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadTemplates = useCallback(async () => {
    if (templates.length > 0) return;
    try { setTemplates(await fetchTemplates()); } catch { /* ignore */ }
  }, [templates.length]);

  const handleNext = async () => {
    if (step === 0) await loadTemplates();
    if (step === 4) {
      setLoading(true);
      try {
        await generateTfvars(config);
        const res = await validateConfig(config);
        setValidation(res);
      } catch { /* ignore */ }
      setLoading(false);
    }
    if (step === 5) {
      setLoading(true);
      try {
        await generateTfvars(config);
        const res = await fetchCostEstimate();
        setCost(res);
      } catch { /* ignore */ }
      setLoading(false);
    }
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const handleDeploy = () => {
    setDeploying(true);
    setTermOutput([]);
    streamSSE(
      "/api/deploy/apply",
      (line) => setTermOutput((prev) => [...prev, line]),
      (code) => { setDeploying(false); setDeployDone(true); setTermOutput((prev) => [...prev, `\n>>> Exit code: ${code}`]); },
      (err) => { setDeploying(false); setTermOutput((prev) => [...prev, `ERROR: ${err.message}`]); },
    );
  };

  const selectTemplate = (t: Template) => {
    const svcKeys = ["enable_vpc","enable_ec2","enable_s3","enable_iam","enable_cloudwatch","enable_dynamodb"];
    const updates: Record<string, boolean> = {};
    svcKeys.forEach((k) => { updates[k] = t.services[k] ?? false; });
    setConfig((c) => ({ ...c, ...updates, environment: t.environment }));
    setStep(1);
  };

  const toggleService = (key: string) => {
    setConfig((c) => ({ ...c, [key]: !(c as Record<string, unknown>)[key] }));
  };

  const updateField = (key: string, value: string | number | boolean) => {
    setConfig((c) => ({ ...c, [key]: value }));
  };

  return (
    <div>
      {/* Step Indicator */}
      <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 32 }}>
        {STEPS.map((s, i) => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "0.7rem", fontWeight: 700,
              background: i < step ? "var(--accent-green)" : i === step ? "var(--accent-blue)" : "var(--bg-input)",
              color: i <= step ? "white" : "var(--text-muted)",
              transition: "all 0.3s ease",
            }}>
              {i < step ? <Check size={14} /> : i + 1}
            </div>
            <span style={{ fontSize: "0.75rem", color: i === step ? "var(--text-primary)" : "var(--text-muted)", fontWeight: i === step ? 600 : 400, display: i === step ? "block" : "none" }}>
              {s}
            </span>
            {i < STEPS.length - 1 && <div style={{ width: 24, height: 2, background: i < step ? "var(--accent-green)" : "var(--border-subtle)", borderRadius: 1 }} />}
          </div>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={step} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.25 }}>

          {/* Step 0: Template */}
          {step === 0 && (
            <div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: 8 }}>Choose a Template</h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginBottom: 24 }}>Start with a pre-configured template or go custom.</p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 16 }}>
                {[
                  { key: "static-site", name: "Static Website", description: "S3-only hosting. Free tier.", services: { enable_s3: true }, environment: "free-tier", icon: "globe" },
                  { key: "backend-app", name: "Backend App", description: "VPC + EC2 + IAM. Free tier.", services: { enable_vpc: true, enable_ec2: true, enable_iam: true }, environment: "free-tier", icon: "server" },
                  { key: "serverless-db", name: "Serverless DB", description: "DynamoDB table. Always free.", services: { enable_dynamodb: true }, environment: "free-tier", icon: "database" },
                ].map((t) => (
                  <button key={t.key} className="glass-card" onClick={() => selectTemplate(t as unknown as Template)}
                    style={{ padding: 24, textAlign: "left", cursor: "pointer", border: "1px solid var(--border-subtle)" }}>
                    <div style={{ width: 40, height: 40, borderRadius: "var(--radius-sm)", background: "var(--accent-blue-glow)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 12 }}>
                      {t.icon === "globe" ? <Globe size={20} color="var(--accent-blue)" /> : t.icon === "server" ? <Server size={20} color="var(--accent-blue)" /> : <Database size={20} color="var(--accent-blue)" />}
                    </div>
                    <h4 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 4 }}>{t.name}</h4>
                    <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{t.description}</p>
                  </button>
                ))}
                <button className="glass-card" onClick={() => setStep(1)}
                  style={{ padding: 24, textAlign: "left", cursor: "pointer", border: "1px dashed var(--border-subtle)" }}>
                  <div style={{ width: 40, height: 40, borderRadius: "var(--radius-sm)", background: "var(--bg-input)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 12 }}>
                    <Rocket size={20} color="var(--text-muted)" />
                  </div>
                  <h4 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 4 }}>Custom</h4>
                  <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Pick services manually.</p>
                </button>
              </div>
            </div>
          )}

          {/* Step 1: Services */}
          {step === 1 && (
            <div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: 24 }}>Select Services</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12 }}>
                {SERVICE_INFO.map(({ key, label, desc, icon: Icon, color }) => {
                  const enabled = !!(config as Record<string, unknown>)[key];
                  return (
                    <button key={key} className="glass-card" onClick={() => toggleService(key)}
                      style={{ padding: 20, display: "flex", alignItems: "center", gap: 16, cursor: "pointer", textAlign: "left", border: enabled ? `1px solid ${color}50` : "1px solid var(--border-subtle)", background: enabled ? `${color}08` : "var(--bg-card)" }}>
                      <div style={{ width: 42, height: 42, borderRadius: "var(--radius-sm)", background: enabled ? `${color}20` : "var(--bg-input)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <Icon size={20} color={enabled ? color : "var(--text-muted)"} />
                      </div>
                      <div style={{ flex: 1 }}>
                        <p style={{ fontWeight: 600, fontSize: "0.9rem", color: enabled ? "var(--text-primary)" : "var(--text-secondary)" }}>{label}</p>
                        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>{desc}</p>
                      </div>
                      <div style={{ width: 20, height: 20, borderRadius: "50%", border: enabled ? "none" : "2px solid var(--border-subtle)", background: enabled ? color : "transparent", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        {enabled && <Check size={12} color="white" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Step 2: Environment */}
          {step === 2 && (
            <div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: 24 }}>Select Environment</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, maxWidth: 600 }}>
                {[{ key: "free-tier", label: "Free Tier", desc: "Development/testing. $0/month.", color: "var(--accent-green)" },
                  { key: "production", label: "Production", desc: "Production workloads. May incur costs.", color: "var(--accent-amber)" }].map((env) => {
                  const sel = config.environment === env.key;
                  return (
                    <button key={env.key} className="glass-card" onClick={() => updateField("environment", env.key)}
                      style={{ padding: 24, cursor: "pointer", textAlign: "left", border: sel ? `1px solid ${env.color}` : "1px solid var(--border-subtle)" }}>
                      <div style={{ width: 16, height: 16, borderRadius: "50%", border: sel ? "none" : "2px solid var(--text-muted)", background: sel ? env.color : "transparent", marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        {sel && <Check size={10} color="white" />}
                      </div>
                      <h4 style={{ fontWeight: 700, marginBottom: 4 }}>{env.label}</h4>
                      <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{env.desc}</p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Step 3: Configure */}
          {step === 3 && (
            <div style={{ maxWidth: 600 }}>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: 24 }}>Configuration</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>AWS Region
                  <select className="select" value={config.aws_region} onChange={(e) => updateField("aws_region", e.target.value)} style={{ marginTop: 6 }}>
                    <option value="ap-south-1">ap-south-1 (Mumbai)</option>
                    <option value="us-east-1">us-east-1 (N. Virginia)</option>
                    <option value="us-west-2">us-west-2 (Oregon)</option>
                    <option value="eu-west-1">eu-west-1 (Ireland)</option>
                  </select>
                </label>
                {config.enable_ec2 && (
                  <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Instance Type
                    <input className="input" value={config.instance_type} onChange={(e) => updateField("instance_type", e.target.value)} style={{ marginTop: 6 }} />
                  </label>
                )}
                {config.enable_s3 && (
                  <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Bucket Name
                    <input className="input" value={config.bucket_name} placeholder="my-bucket-name" onChange={(e) => updateField("bucket_name", e.target.value)} style={{ marginTop: 6 }} />
                  </label>
                )}
                {config.enable_dynamodb && (
                  <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>DynamoDB Table Name
                    <input className="input" value={config.dynamodb_table_name} placeholder="my-table" onChange={(e) => updateField("dynamodb_table_name", e.target.value)} style={{ marginTop: 6 }} />
                  </label>
                )}
                <label style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>Budget Email
                  <input className="input" type="email" value={config.budget_email} placeholder="you@example.com" onChange={(e) => updateField("budget_email", e.target.value)} style={{ marginTop: 6 }} />
                </label>
              </div>
            </div>
          )}

          {/* Step 4: Policy Check */}
          {step === 4 && (
            <div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: 24 }}>Policy Check Results</h3>
              {loading ? (
                <div style={{ textAlign: "center", padding: 40 }}><Loader2 size={32} color="var(--accent-blue)" style={{ animation: "spin 1s linear infinite" }} /><p style={{ marginTop: 12, color: "var(--text-secondary)" }}>Running policy engines...</p></div>
              ) : validation ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                  <div className="glass-card" style={{ padding: 20 }}>
                    <h4 style={{ fontWeight: 700, marginBottom: 12 }}>YAML Engine</h4>
                    {validation.yaml.blocks.length === 0 && validation.yaml.warnings.length === 0 ? (
                      <p style={{ color: "var(--accent-green)", display: "flex", alignItems: "center", gap: 8 }}><Check size={16} /> All checks passed</p>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {validation.yaml.blocks.map((v, i) => <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}><XCircle size={16} color="var(--accent-red)" style={{ flexShrink: 0, marginTop: 2 }} /><span style={{ fontSize: "0.8rem" }}>{v.description}</span></div>)}
                        {validation.yaml.warnings.map((v, i) => <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}><AlertTriangle size={16} color="var(--accent-amber)" style={{ flexShrink: 0, marginTop: 2 }} /><span style={{ fontSize: "0.8rem" }}>{v.description}</span></div>)}
                      </div>
                    )}
                  </div>
                  <div className="glass-card" style={{ padding: 20 }}>
                    <h4 style={{ fontWeight: 700, marginBottom: 12 }}>OPA Engine</h4>
                    {!validation.opa.available ? (
                      <p style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>OPA CLI not installed — skipped</p>
                    ) : validation.opa.blocks.length === 0 && validation.opa.warnings.length === 0 ? (
                      <p style={{ color: "var(--accent-green)", display: "flex", alignItems: "center", gap: 8 }}><Check size={16} /> All checks passed</p>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {validation.opa.blocks.map((b, i) => <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}><XCircle size={16} color="var(--accent-red)" style={{ flexShrink: 0, marginTop: 2 }} /><span style={{ fontSize: "0.8rem" }}>{b}</span></div>)}
                        {validation.opa.warnings.map((w, i) => <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}><AlertTriangle size={16} color="var(--accent-amber)" style={{ flexShrink: 0, marginTop: 2 }} /><span style={{ fontSize: "0.8rem" }}>{w}</span></div>)}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <p style={{ color: "var(--text-muted)" }}>Click Next to run the policy check.</p>
              )}
            </div>
          )}

          {/* Step 5: Cost */}
          {step === 5 && (
            <div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: 24 }}>Cost Estimate</h3>
              {loading ? (
                <div style={{ textAlign: "center", padding: 40 }}><Loader2 size={32} color="var(--accent-blue)" style={{ animation: "spin 1s linear infinite" }} /></div>
              ) : cost ? (
                <div className="glass-card" style={{ padding: 24 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                    <div>
                      <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Total Monthly Cost</p>
                      <p style={{ fontSize: "2rem", fontWeight: 800 }}>${cost.total_monthly_cost ?? "0.00"}</p>
                    </div>
                    <span className="badge badge-success">Free Tier</span>
                  </div>
                  {cost.resources && cost.resources.length > 0 && (
                    <table className="data-table">
                      <thead><tr><th>Resource</th><th>Monthly</th></tr></thead>
                      <tbody>{cost.resources.map((r, i) => <tr key={i}><td>{r.name}</td><td>${r.monthly_cost}</td></tr>)}</tbody>
                    </table>
                  )}
                  {!cost.available && <p style={{ color: "var(--accent-amber)", fontSize: "0.8rem", marginTop: 12 }}>⚠ Infracost not available: {cost.error}</p>}
                </div>
              ) : (
                <p style={{ color: "var(--text-muted)" }}>Cost data will appear here.</p>
              )}
            </div>
          )}

          {/* Step 6: Deploy */}
          {step === 6 && (
            <div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: 24 }}>Review & Deploy</h3>
              {!deploying && !deployDone && (
                <div>
                  <div className="glass-card" style={{ padding: 20, marginBottom: 20 }}>
                    <h4 style={{ fontWeight: 600, marginBottom: 12, fontSize: "0.9rem" }}>Configuration Summary</h4>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: "0.8rem" }}>
                      <span style={{ color: "var(--text-muted)" }}>Region:</span><span>{config.aws_region}</span>
                      <span style={{ color: "var(--text-muted)" }}>Environment:</span><span>{config.environment}</span>
                      <span style={{ color: "var(--text-muted)" }}>Services:</span>
                      <span>{SERVICE_INFO.filter(s => !!(config as Record<string, unknown>)[s.key]).map(s => s.label).join(", ") || "None"}</span>
                    </div>
                  </div>
                  <button className="btn-primary" onClick={handleDeploy} disabled={validation?.summary?.can_deploy === false}>
                    <Rocket size={16} /> Deploy Infrastructure
                  </button>
                </div>
              )}
              {(deploying || deployDone) && (
                <div className="terminal">
                  {termOutput.map((line, i) => <div key={i}>{line}</div>)}
                  {deploying && <span className="animate-pulse-glow">▌</span>}
                </div>
              )}
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Navigation Buttons */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 32 }}>
        <button className="btn-secondary" onClick={() => setStep((s) => Math.max(s - 1, 0))} disabled={step === 0}>
          <ChevronLeft size={16} /> Back
        </button>
        {step < 6 && (
          <button className="btn-primary" onClick={handleNext}>
            Next <ChevronRight size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
