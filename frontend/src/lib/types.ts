/**
 * TypeScript interfaces mirroring the backend's Pydantic models.
 *
 * Naming: matches the backend's conceptual entity name, not its Pydantic
 * schema class name -- the backend's "Read" suffix (ProjectRead, NCRRead,
 * ...) is a schema-layer convention with no meaning here, so it's dropped
 * (ProjectRead -> Project, AIAuditLogRead -> AIAuditLog, etc). Two backend
 * concepts are both called "decision": meeting_intelligence's LLM-extracted
 * `Decision` (description/rationale/owner) and the raw dataset's
 * `ProjectDecision` (decision_text/owner/decision_date, from DecisionRead).
 * Kept distinct here for the same reason they're distinct in the backend.
 *
 * See docs/API.md's "Agent invocation protocol" section for how
 * AgentRunResponse<T> is derived from the real response shape.
 */

// ---------------------------------------------------------------------------
// Agents (generic invocation protocol)
// ---------------------------------------------------------------------------

export interface Agent {
  name: string;
  description: string;
  version: string;
}

export interface ToolCallTraceEntry {
  turn: number;
  tool: string;
  arguments: Record<string, unknown>;
  output: unknown;
  error: string | null;
}

/** Fixed metadata fields present on every POST /agents/{name} response. */
export interface AgentRunMeta {
  audit_log_id: number;
  model: string;
  latency_ms: number;
  turns_used: number;
  tool_call_trace: ToolCallTraceEntry[];
  memory_ids: number[];
  output_valid: boolean;
  error: string | null;
}

/** An agent's own output fields, flattened alongside the fixed metadata. */
export type AgentRunResponse<T> = T & AgentRunMeta;

// ---------------------------------------------------------------------------
// hello_world
// ---------------------------------------------------------------------------

export interface HelloOutput {
  greeting: string;
  citations: number[];
}

// ---------------------------------------------------------------------------
// meeting_intelligence
// ---------------------------------------------------------------------------

export interface ActionItem {
  description: string;
  owner: string;
  due_date: string | null;
  priority: "low" | "medium" | "high";
}

export interface Decision {
  description: string;
  rationale: string | null;
  owner: string | null;
}

export interface Risk {
  description: string;
  severity: "low" | "medium" | "high";
}

export interface MeetingAnalysis {
  summary: string;
  action_items: ActionItem[];
  decisions: Decision[];
  risks: Risk[];
  confidence: number;
}

// ---------------------------------------------------------------------------
// supplier_risk
// ---------------------------------------------------------------------------

export interface RiskFactor {
  description: string;
  severity: "low" | "medium" | "high";
  evidence: string;
}

export interface SupplierRiskAssessment {
  supplier_id: number;
  supplier_name: string;
  risk_score: number;
  overall_severity: "low" | "medium" | "high";
  top_concerns: RiskFactor[];
  recommendations: string[];
  confidence: number;
  summary: string;
}

// ---------------------------------------------------------------------------
// executive_report
// ---------------------------------------------------------------------------

export interface ReportSection {
  title: string;
  key_points: string[];
  /** "label: value" strings -- see docs/ARCHITECTURE.md for why this isn't a dict. */
  supporting_data: string[];
}

export interface WeeklyReport {
  week_of: string;
  executive_summary: string;
  sections: ReportSection[];
  top_recommendations: string[];
  confidence: number;
}

// ---------------------------------------------------------------------------
// chat
// ---------------------------------------------------------------------------

export interface ChatRequest {
  message: string;
  project_id?: number;
  session_id?: string;
}

export type DomainAgentName = "meeting_intelligence" | "supplier_risk" | "executive_report";

export interface ChatResponse {
  agent_used: DomainAgentName | null;
  /** Structured agent output when agent_used is set, else a plain string answer. */
  response: unknown;
  audit_log_id: number;
  latency_ms: number;
}

// ---------------------------------------------------------------------------
// approvals
// ---------------------------------------------------------------------------

export interface ApprovalRequest {
  id: number;
  workflow: string;
  project_id: number | null;
  action_type: string;
  payload: Record<string, unknown>;
  reasoning: string;
  source_ids: unknown[];
  status: string;
  reviewer: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
}

export interface ApprovalRequestPage {
  items: ApprovalRequest[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// audit logs
// ---------------------------------------------------------------------------

export interface AIAuditLog {
  id: number;
  workflow: string;
  project_id: number | null;
  model: string;
  prompt: string;
  system_instruction: string | null;
  output: string | null;
  output_valid: boolean;
  error: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  latency_ms: number | null;
  retrieved_source_ids: unknown[] | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

export interface AIAuditLogPage {
  items: AIAuditLog[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// memories
// ---------------------------------------------------------------------------

export interface AIMemory {
  id: number;
  project_id: number | null;
  category: string;
  content: string;
  source_reference: Record<string, unknown>;
  confidence: number;
  extracted_by: string;
  created_at: string;
}

export interface AIMemoryPage {
  items: AIMemory[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// metrics
// ---------------------------------------------------------------------------

export interface AgentMetric {
  workflow: string;
  total_runs: number;
  success_rate: number;
  avg_latency_ms: number;
  avg_tokens: number;
  last_run_at: string;
}

export interface ToolMetric {
  tool: string;
  total_invocations: number;
  avg_output_size_chars: number;
  error_rate: number;
}

export interface MetricsOverview {
  total_llm_calls: number;
  total_tokens: number;
  estimated_cost_usd: number;
  cost_estimate_note: string;
  audit_log_count: number;
  memory_count: number;
  document_chunk_count: number;
}

// ---------------------------------------------------------------------------
// construction dataset (projects, suppliers, meetings, POs, NCRs, safety)
// ---------------------------------------------------------------------------

export interface Project {
  id: number;
  project_code: string;
  project_name: string;
  project_type: string;
  client_name: string;
  city: string;
  start_date: string;
  planned_finish: string;
  actual_finish: string | null;
  status: string;
  budget: number;
}

export interface Supplier {
  id: number;
  supplier_name: string;
  category: string;
  city: string;
  status: string;
}

export interface ProjectDecision {
  id: number;
  project_id: number;
  meeting_id: number;
  decision_date: string;
  decision_text: string;
  owner: string;
}

export interface Meeting {
  id: number;
  project_id: number;
  meeting_date: string;
  title: string;
  meeting_type: string;
}

export interface MeetingWithDecisions extends Meeting {
  decisions: ProjectDecision[];
}

export interface PurchaseOrder {
  id: number;
  pr_id: number;
  project_id: number;
  supplier_id: number;
  po_number: string;
  issue_date: string;
  promised_delivery: string;
  actual_delivery: string | null;
  status: string;
  is_late: number;
  delay_days: number;
  delay_root_cause: string | null;
}

export interface NCR {
  id: number;
  project_id: number;
  supplier_id: number | null;
  subcontractor_id: number | null;
  ncr_type: string;
  description: string;
  root_cause: string;
  issue_date: string;
  status: string;
}

export interface SafetyEvent {
  id: number;
  project_id: number;
  subcontractor_id: number;
  event_date: string;
  severity: string;
  description: string;
  corrective_action: string;
}
