/**
 * API Client — Fetch wrappers for the FastAPI backend (localhost:8000).
 *
 * Every page uses these helpers instead of raw fetch() so the base URL,
 * error handling, and types are centralised in one place.
 */

const API_BASE = "http://localhost:8000";

/* ─── Generic Helpers ─── */

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function put<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

/* ─── Types ─── */

export interface DashboardData {
  services: Record<string, boolean>;
  active_count: number;
  policy_health: { blocks: number; warnings: number; status: string };
  drift_status: string;
  recent_events: AuditEvent[];
}

export interface AuditEvent {
  event_id?: string;
  timestamp: string;
  action: string;
  actor: string;
  environment: string;
  deployment_id?: string;
  status: string;
  details?: string;
  reason?: string;
}

export interface Template {
  key: string;
  name: string;
  description: string;
  services: Record<string, boolean>;
  environment: string;
  icon: string;
}

export interface ConfigPayload {
  aws_region?: string;
  enable_vpc?: boolean;
  enable_ec2?: boolean;
  enable_s3?: boolean;
  enable_iam?: boolean;
  enable_cloudwatch?: boolean;
  enable_dynamodb?: boolean;
  vpc_cidr?: string;
  instance_type?: string;
  ami_id?: string;
  bucket_name?: string;
  role_name?: string;
  alarm_email?: string;
  budget_limit?: string;
  budget_email?: string;
  dynamodb_table_name?: string;
  dynamodb_hash_key?: string;
  dynamodb_hash_key_type?: string;
  dynamodb_read_capacity?: number;
  dynamodb_write_capacity?: number;
  dynamodb_enable_pitr?: boolean;
  tags?: Record<string, string>;
  environment?: string;
}

export interface PolicyViolation {
  rule_name: string;
  description: string;
  severity: string;
}

export interface ValidationResult {
  yaml: { blocks: PolicyViolation[]; warnings: PolicyViolation[]; error: string | null };
  opa: { blocks: string[]; warnings: string[]; available: boolean; error: string | null };
  summary: { total_blocks: number; total_warnings: number; can_deploy: boolean };
}

export interface CostEstimate {
  available: boolean;
  total_monthly_cost?: string;
  currency?: string;
  resources?: { name: string; monthly_cost: string; hourly_cost: string }[];
  error?: string;
}

export interface PolicyRule {
  name: string;
  description: string;
  severity: string;
  condition?: string;
  type?: string;
}

export interface TeamMember {
  username: string;
  name: string;
  email: string;
  role: string;
  role_name: string;
  teams: string[];
  permissions: string[];
}

export interface RoleDef {
  key: string;
  name: string;
  description: string;
  permissions: string[];
  requires_approval: boolean;
  max_per_day: number;
}

export interface DriftStatus {
  status: string;
  timestamp: string | null;
  report: string | null;
  message?: string;
}

export interface ApprovalRequest {
  request_id: string;
  requester: string;
  environment: string;
  description: string;
  status: string;
  created_at: string;
  approvals_needed: number;
  approvals_received: { approver: string; timestamp: string; reason: string }[];
  rejections: { rejector: string; timestamp: string; reason: string }[];
}

/* ─── API Functions ─── */

// Auth
export interface AuthUser {
  authenticated: boolean;
  method?: string;
  username?: string;
  name?: string;
  role?: string;
  role_name?: string;
  permissions?: string[];
  teams?: string[];
  avatar_url?: string;
  warning?: string;
  error?: string;
}

export const loginWithToken = (github_token: string) =>
  post<AuthUser>("/api/auth/login", { github_token });

export const loginWithUsername = (username: string) =>
  post<AuthUser>("/api/auth/login", { username });

// Health
export const fetchHealth = () => get<{ status: string; version: string }>("/api/health");

// Dashboard
export const fetchDashboard = () => get<DashboardData>("/api/dashboard");

// Templates
export const fetchTemplates = () => get<Template[]>("/api/templates");

// Config
export const validateConfig = (config: ConfigPayload) =>
  post<ValidationResult>("/api/config/validate", config);

export const generateTfvars = (config: ConfigPayload) =>
  post<{ tfvars: string; path: string }>("/api/config/generate-tfvars", config);

// Cost
export const fetchCostEstimate = () => post<CostEstimate>("/api/cost-estimate");

// Policies
export const fetchYamlPolicies = () => get<{ rules: PolicyRule[]; count: number }>("/api/policies/yaml");
export const addCustomPolicy = (payload: { name: string; description: string; severity: string; condition: string }) =>
  post<{ success: boolean; message: string }>("/api/policies/yaml", payload);
export const fetchOpaPolicies = () =>
  get<{ rules: PolicyRule[]; count: number; opa_available: boolean }>("/api/policies/opa");
export const evaluatePolicies = (config: ConfigPayload) =>
  post<ValidationResult>("/api/policies/evaluate", config);

// Audit
export const fetchAuditEvents = (params?: {
  actor?: string;
  environment?: string;
  action?: string;
  limit?: number;
}) => {
  const query = new URLSearchParams();
  if (params?.actor) query.set("actor", params.actor);
  if (params?.environment) query.set("environment", params.environment);
  if (params?.action) query.set("action", params.action);
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  return get<{ events: AuditEvent[]; total: number }>(`/api/audit/events${qs ? `?${qs}` : ""}`);
};

export const fetchAuditReport = () =>
  get<{ total_events: number; by_action: Record<string, number>; by_actor: Record<string, number>; by_environment: Record<string, number>; by_status: Record<string, number> }>("/api/audit/report");

// Team
export const fetchTeamMembers = () => get<{ members: TeamMember[]; total: number }>("/api/team/members");
export const fetchTeamRoles = () => get<{ roles: RoleDef[]; total: number }>("/api/team/roles");
export const fetchTeamUser = (username: string) => get<{ user: TeamMember }>(`/api/team/user/${username}`);
export const addTeamUser = (payload: {
  name: string;
  email: string;
  github_username: string;
  role?: string;
  team?: string;
}) => post<{ success: boolean; user: unknown }>("/api/team/user", payload);
export const deleteTeamUser = (username: string) =>
  del<{ success: boolean; message: string }>(`/api/team/user/${username}`);
export const modifyTeamUserRole = (payload: { username: string; new_role: string }) =>
  put<{ success: boolean; message: string; user?: TeamMember }>("/api/team/user/role", payload);

// Approvals
export const fetchApprovals = () => get<{ requests: ApprovalRequest[]; total: number; pending: number }>("/api/approvals");
export const requestApproval = (payload: { requester: string; environment: string; description: string }) =>
  post<{ success: boolean; request_id: string; status: string; slack_sent: boolean }>("/api/approvals/request", payload);
export const processApprovalAction = (payload: { request_id: string; action: "approve" | "reject"; approver: string; reason?: string }) =>
  post<{ success: boolean; request_id: string; status: string; action: string; message?: string }>("/api/approvals/action", payload);

// Drift
export const fetchDriftStatus = () => get<DriftStatus>("/api/drift/status");
export const triggerDriftRemediation = (checkOnly = true, autoApprove = false) =>
  post<{ success: boolean; performed: boolean; message: string; report_path: string }>(
    `/api/drift/remediate?check_only=${checkOnly}&auto_approve=${autoApprove}`,
  );

// SSE stream helper — used by deploy + drift scan
export function streamSSE(
  path: string,
  onLine: (line: string) => void,
  onDone: (exitCode: number) => void,
  onError?: (err: Error) => void,
): AbortController {
  const controller = new AbortController();

  fetch(`${API_BASE}${path}`, {
    method: "POST",
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        onError?.(new Error(`SSE ${path} failed: ${res.status}`));
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const raw of lines) {
          if (raw.startsWith("data: ")) {
            try {
              const parsed = JSON.parse(raw.slice(6));
              if (parsed.done) {
                onDone(parsed.exit_code ?? 0);
              } else if (parsed.line !== undefined) {
                onLine(parsed.line);
              }
            } catch {
              /* skip malformed */
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError?.(err);
    });

  return controller;
}
