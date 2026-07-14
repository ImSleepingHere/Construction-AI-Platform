/**
 * Typed API client. Every call to the backend goes through here -- no
 * scattered fetch() calls in components/pages.
 *
 * Two base URLs, because server components run inside the frontend
 * container (Docker-internal networking) while client components run in
 * the browser on the host (published-port networking):
 * - NEXT_PUBLIC_API_URL: browser-facing, defaults to http://localhost:8000.
 * - API_URL_INTERNAL: server-facing (not NEXT_PUBLIC_, so it never reaches
 *   the client bundle), defaults to http://api:8000 -- the docker-compose
 *   service name, resolved via Docker's internal DNS. Falls back to the
 *   public URL when unset (e.g. running the dev server outside Docker).
 */

import type {
  Agent,
  AgentRunResponse,
  AIAuditLog,
  AIAuditLogPage,
  AIMemoryPage,
  ApprovalRequest,
  ApprovalRequestPage,
  AgentMetric,
  ChatRequest,
  ChatResponse,
  Meeting,
  MeetingWithDecisions,
  MetricsOverview,
  NCR,
  Project,
  PurchaseOrder,
  SafetyEvent,
  Supplier,
  ToolMetric,
} from "./types";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const INTERNAL_API_URL = process.env.API_URL_INTERNAL ?? PUBLIC_API_URL;
const API_BASE_URL = typeof window === "undefined" ? INTERNAL_API_URL : PUBLIC_API_URL;

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type QueryParams = Record<string, string | number | boolean | undefined | null>;

function buildQuery(params?: QueryParams): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch (cause) {
    throw new ApiError(
      `Could not reach the API at ${API_BASE_URL}${path}. Is the backend running? (${String(cause)})`,
      0,
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body?.detail === "string") detail = body.detail;
      else if (body?.detail !== undefined) detail = JSON.stringify(body.detail);
    } catch {
      // Response body wasn't JSON -- fall back to statusText.
    }
    throw new ApiError(
      `${init?.method ?? "GET"} ${path} failed (${res.status}): ${detail}`,
      res.status,
    );
  }

  // No content (e.g. some future 204 response).
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

export function listAgents(): Promise<Agent[]> {
  return apiFetch<Agent[]>("/agents");
}

export function runAgent<T>(
  skillName: string,
  input: Record<string, unknown>,
): Promise<AgentRunResponse<T>> {
  return apiFetch<AgentRunResponse<T>>(`/agents/${skillName}`, {
    method: "POST",
    body: JSON.stringify({ input }),
  });
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export function chat(req: ChatRequest): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export function listProjects(params?: { limit?: number; offset?: number }): Promise<Project[]> {
  return apiFetch<Project[]>(`/projects${buildQuery(params)}`);
}

export function getProject(id: number): Promise<Project> {
  return apiFetch<Project>(`/projects/${id}`);
}

export function listProjectMeetings(
  projectId: number,
  params?: { limit?: number; offset?: number },
): Promise<Meeting[]> {
  return apiFetch<Meeting[]>(`/projects/${projectId}/meetings${buildQuery(params)}`);
}

export function listProjectPurchaseOrders(
  projectId: number,
  params?: { limit?: number; offset?: number },
): Promise<PurchaseOrder[]> {
  return apiFetch<PurchaseOrder[]>(`/projects/${projectId}/purchase-orders${buildQuery(params)}`);
}

export function listProjectNCRs(
  projectId: number,
  params?: { limit?: number; offset?: number },
): Promise<NCR[]> {
  return apiFetch<NCR[]>(`/projects/${projectId}/ncrs${buildQuery(params)}`);
}

export function listProjectSafetyEvents(
  projectId: number,
  params?: { limit?: number; offset?: number },
): Promise<SafetyEvent[]> {
  return apiFetch<SafetyEvent[]>(`/projects/${projectId}/safety-events${buildQuery(params)}`);
}

// ---------------------------------------------------------------------------
// Suppliers
// ---------------------------------------------------------------------------

export function listSuppliers(params?: {
  limit?: number;
  offset?: number;
}): Promise<Supplier[]> {
  return apiFetch<Supplier[]>(`/suppliers${buildQuery(params)}`);
}

export function getSupplier(id: number): Promise<Supplier> {
  return apiFetch<Supplier>(`/suppliers/${id}`);
}

export function listSupplierPurchaseOrders(
  supplierId: number,
  params?: { limit?: number; offset?: number },
): Promise<PurchaseOrder[]> {
  return apiFetch<PurchaseOrder[]>(`/suppliers/${supplierId}/purchase-orders${buildQuery(params)}`);
}

export function listSupplierNCRs(
  supplierId: number,
  params?: { limit?: number; offset?: number },
): Promise<NCR[]> {
  return apiFetch<NCR[]>(`/suppliers/${supplierId}/ncrs${buildQuery(params)}`);
}

// ---------------------------------------------------------------------------
// Meetings
// ---------------------------------------------------------------------------

export function listMeetings(params?: {
  project_id?: number;
  limit?: number;
  offset?: number;
}): Promise<Meeting[]> {
  return apiFetch<Meeting[]>(`/meetings${buildQuery(params)}`);
}

export function getMeeting(id: number): Promise<MeetingWithDecisions> {
  return apiFetch<MeetingWithDecisions>(`/meetings/${id}`);
}

// ---------------------------------------------------------------------------
// Memories
// ---------------------------------------------------------------------------

export function listMemories(params?: {
  category?: string;
  project_id?: number;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<AIMemoryPage> {
  return apiFetch<AIMemoryPage>(`/memories${buildQuery(params)}`);
}

// ---------------------------------------------------------------------------
// Approvals
// ---------------------------------------------------------------------------

export function listApprovals(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ApprovalRequestPage> {
  return apiFetch<ApprovalRequestPage>(`/approvals${buildQuery(params)}`);
}

export function getApproval(id: number): Promise<ApprovalRequest> {
  return apiFetch<ApprovalRequest>(`/approvals/${id}`);
}

export function approveRequest(
  id: number,
  body: { reviewer: string; notes?: string },
): Promise<ApprovalRequest> {
  return apiFetch<ApprovalRequest>(`/approvals/${id}/approve`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function rejectRequest(
  id: number,
  body: { reviewer: string; notes?: string },
): Promise<ApprovalRequest> {
  return apiFetch<ApprovalRequest>(`/approvals/${id}/reject`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Audit logs
// ---------------------------------------------------------------------------

export function listAuditLogs(params?: {
  workflow?: string;
  project_id?: number;
  output_valid?: boolean;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}): Promise<AIAuditLogPage> {
  return apiFetch<AIAuditLogPage>(`/audit-logs${buildQuery(params)}`);
}

export function getAuditLog(id: number): Promise<AIAuditLog> {
  return apiFetch<AIAuditLog>(`/audit-logs/${id}`);
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

export function getMetricsOverview(): Promise<MetricsOverview> {
  return apiFetch<MetricsOverview>("/metrics/overview");
}

export function getMetricsAgents(): Promise<AgentMetric[]> {
  return apiFetch<AgentMetric[]>("/metrics/agents");
}

export function getMetricsTools(): Promise<ToolMetric[]> {
  return apiFetch<ToolMetric[]>("/metrics/tools");
}
