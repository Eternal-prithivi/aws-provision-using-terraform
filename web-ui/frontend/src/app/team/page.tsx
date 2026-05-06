"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Users, Shield, UserPlus, Check, X, Crown, Wrench, Code, Eye, Trash2, Edit2, ThumbsUp, ThumbsDown, Clock } from "lucide-react";
import type { TeamMember, RoleDef, ApprovalRequest } from "@/lib/api";
import { fetchTeamMembers, fetchTeamRoles, addTeamUser, deleteTeamUser, modifyTeamUserRole, fetchApprovals, processApprovalAction } from "@/lib/api";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } };

const ROLE_ICONS: Record<string, typeof Crown> = { admin: Crown, devops: Wrench, developer: Code, viewer: Eye };
const ROLE_COLORS: Record<string, string> = { admin: "#ef4444", devops: "#3b82f6", developer: "#22c55e", viewer: "#8b8b9e" };

export default function TeamPage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [roles, setRoles] = useState<RoleDef[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", github_username: "", role: "developer", team: "devops-core" });
  const [addError, setAddError] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [currentUser, setCurrentUser] = useState("");

  const refreshData = () => {
    fetchTeamMembers().then((d) => setMembers(d.members)).catch(() => {});
    fetchTeamRoles().then((d) => setRoles(d.roles)).catch(() => {});
    fetchApprovals().then((d) => setApprovals(d.requests)).catch(() => {});
  };

  useEffect(() => {
    refreshData();
    try {
      const user = JSON.parse(sessionStorage.getItem("auth_user") || "{}");
      setIsAdmin(user.role === "admin");
      setCurrentUser(user.username || "");
    } catch {}
  }, []);

  const handleAdd = async () => {
    setAddError("");
    try {
      await addTeamUser(form);
      setShowAdd(false);
      setForm({ name: "", email: "", github_username: "", role: "developer", team: "devops-core" });
      refreshData();
    } catch (e: any) {
      setAddError(e.message ?? "Failed to add user");
    }
  };

  const handleDelete = async (username: string) => {
    if (!confirm(`Remove ${username}?`)) return;
    try {
      await deleteTeamUser(username);
      refreshData();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleRoleChange = async (username: string, newRole: string) => {
    try {
      await modifyTeamUserRole({ username, new_role: newRole });
      refreshData();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleApprovalAction = async (requestId: string, action: "approve" | "reject") => {
    try {
      await processApprovalAction({ request_id: requestId, action, approver: currentUser, reason: "" });
      refreshData();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <motion.div variants={container} initial="hidden" animate="show">
      {/* Roles Overview */}
      <motion.div variants={item} style={{ marginBottom: 32 }}>
        <h3 style={{ fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <Shield size={18} color="var(--accent-blue)" /> Role Definitions
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
          {roles.map((r) => {
            const Icon = ROLE_ICONS[r.key] ?? Shield;
            const color = ROLE_COLORS[r.key] ?? "var(--text-muted)";
            return (
              <div key={r.key} className="glass-card" style={{ padding: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                  <div style={{ width: 36, height: 36, borderRadius: "var(--radius-sm)", background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icon size={18} color={color} />
                  </div>
                  <div>
                    <p style={{ fontWeight: 700, fontSize: "0.9rem" }}>{r.name}</p>
                    <p style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>{r.description}</p>
                  </div>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {r.permissions.slice(0, 6).map((p) => (
                    <span key={p} style={{ fontSize: "0.65rem", padding: "2px 8px", borderRadius: 9999, background: "var(--bg-input)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}>{p}</span>
                  ))}
                  {r.permissions.length > 6 && <span style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>+{r.permissions.length - 6}</span>}
                </div>
                <div style={{ marginTop: 10, fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", gap: 12 }}>
                  <span>Max/day: {r.max_per_day === -1 ? "∞" : r.max_per_day}</span>
                  <span>Approval: {r.requires_approval ? "Required" : "No"}</span>
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Approvals */}
      {approvals.length > 0 && (
        <motion.div variants={item} className="glass-card" style={{ padding: 24, marginBottom: 32 }}>
          <h3 style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <Clock size={18} color="var(--accent-amber)" /> Deployment Approvals
          </h3>
          <div style={{ display: "grid", gap: 12 }}>
            {approvals.map((req) => (
              <div key={req.request_id} style={{ padding: 16, background: "var(--bg-input)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <p style={{ fontWeight: 700, fontSize: "0.95rem", display: "flex", alignItems: "center", gap: 8 }}>
                    #{req.request_id} — {req.environment.toUpperCase()}
                    <span className={`badge ${req.status === "approved" ? "badge-success" : req.status === "rejected" ? "badge-block" : "badge-warning"}`}>
                      {req.status}
                    </span>
                  </p>
                  <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 4 }}>
                    Requested by <strong>{req.requester}</strong> • {req.description || "No description"}
                  </p>
                  <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                    Approvals: {req.approvals_received.length} / {req.approvals_needed}
                  </p>
                </div>
                {req.status === "pending" && isAdmin && req.requester !== currentUser && (
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="btn-secondary" onClick={() => handleApprovalAction(req.request_id, "reject")} style={{ borderColor: "var(--accent-red)", color: "var(--accent-red)", padding: "6px 12px" }}>
                      <ThumbsDown size={14} /> Reject
                    </button>
                    <button className="btn-primary" onClick={() => handleApprovalAction(req.request_id, "approve")} style={{ padding: "6px 12px" }}>
                      <ThumbsUp size={14} /> Approve
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Members */}
      <motion.div variants={item} className="glass-card" style={{ padding: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h3 style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
            <Users size={18} color="var(--accent-blue)" /> Team Members ({members.length})
          </h3>
          <button className="btn-primary" onClick={() => setShowAdd(!showAdd)} style={{ fontSize: "0.8rem", padding: "8px 16px" }}>
            <UserPlus size={14} /> Add User
          </button>
        </div>

        {/* Add Form */}
        {showAdd && (
          <div style={{ padding: 20, background: "var(--bg-input)", borderRadius: "var(--radius-md)", marginBottom: 20, border: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <input className="input" placeholder="Full Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <input className="input" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              <input className="input" placeholder="GitHub Username" value={form.github_username} onChange={(e) => setForm({ ...form, github_username: e.target.value })} />
              <select className="select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="developer">Developer</option>
                <option value="devops">DevOps</option>
                <option value="admin">Admin</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            {addError && <p style={{ color: "var(--accent-red)", fontSize: "0.8rem", marginTop: 8 }}>{addError}</p>}
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="btn-primary" onClick={handleAdd} style={{ padding: "8px 16px", fontSize: "0.8rem" }}><Check size={14} /> Add</button>
              <button className="btn-secondary" onClick={() => setShowAdd(false)} style={{ padding: "8px 16px", fontSize: "0.8rem" }}><X size={14} /> Cancel</button>
            </div>
          </div>
        )}

        {/* Members Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12 }}>
          {members.map((m) => {
            const color = ROLE_COLORS[m.role] ?? "var(--text-muted)";
            const Icon = ROLE_ICONS[m.role] ?? Shield;
            return (
              <div key={m.username} style={{ padding: 16, background: "var(--bg-input)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", gap: 14 }}>
                <div style={{ width: 40, height: 40, borderRadius: "50%", background: `${color}20`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Icon size={18} color={color} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontWeight: 600, fontSize: "0.9rem" }}>{m.name}</p>
                  <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis" }}>@{m.username} • {m.email}</p>
                </div>
                {isAdmin && m.username !== currentUser ? (
                  <div style={{ display: "flex", gap: 8, flexShrink: 0, alignItems: "center" }}>
                    <select className="select" value={m.role} onChange={(e) => handleRoleChange(m.username, e.target.value)} style={{ width: 120, padding: "6px 28px 6px 10px", fontSize: "0.75rem" }}>
                      {roles.map(r => <option key={r.key} value={r.key}>{r.name}</option>)}
                    </select>
                    <button onClick={() => handleDelete(m.username)} style={{ background: "transparent", border: "none", color: "var(--accent-red)", cursor: "pointer", padding: 6, borderRadius: "var(--radius-xs)" }}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                ) : (
                  <span className={`badge ${m.role === "admin" ? "badge-block" : m.role === "devops" ? "badge-info" : m.role === "developer" ? "badge-success" : "badge-warning"}`} style={{ flexShrink: 0 }}>
                    {m.role_name}
                  </span>
                )}
              </div>
            );
          })}
          {members.length === 0 && <p style={{ color: "var(--text-muted)", gridColumn: "1 / -1", textAlign: "center", padding: 24 }}>No team members found.</p>}
        </div>
      </motion.div>
    </motion.div>
  );
}
