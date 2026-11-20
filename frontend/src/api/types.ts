export type UserRole = "ADMIN" | "MANAGER" | "STAFF";

export type DocumentStatus = "UPLOADED" | "PROCESSING" | "READY" | "FAILED" | "ARCHIVED";
export type DocumentAccessScope = "PRIVATE" | "DEPARTMENT" | "ORGANIZATION";
export type DocumentPermissionLevel = "VIEW" | "EDIT" | "MANAGE";
export type FeedbackRating = "HELPFUL" | "NOT_HELPFUL";
export type ChatMessageRole = "USER" | "ASSISTANT";
export type GroundingStatus = "ANSWERED" | "NO_ANSWER";
export type DocumentLifecycleStatus = "ACTIVE" | "SUPERSEDED" | "ARCHIVED" | "DRAFT";

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface DataResponse<T> {
  data: T;
  meta: null;
}

export interface ListResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: unknown;
  request_id?: string | null;
}

export interface ApiErrorEnvelope {
  error: ApiErrorPayload;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department_id: string | null;
  /** BR-4: name of the caller's own Department, null without one. */
  department_name: string | null;
  is_active: boolean;
}

export interface TokenPairData {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthenticatedUser;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  description: string | null;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  description: string | null;
  /** BR-1 version fields. */
  document_code: string | null;
  document_version: string | null;
  effective_from: string | null;
  effective_to: string | null;
  lifecycle_status: DocumentLifecycleStatus;
  supersedes_document_id: string | null;
  original_filename: string;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  access_scope: DocumentAccessScope;
  department_id: string | null;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
  /** BR-4: whether the caller uploaded it; for every viewer. */
  uploaded_by_me: boolean;
  /** BR-4 option (a): present only for an Admin caller; the keys are absent otherwise. */
  uploaded_by_name?: string;
  department_name?: string | null;
}

export interface DocumentStatusResponse {
  id: string;
  status: DocumentStatus;
  error_message: string | null;
  updated_at: string;
}

export interface DocumentPermission {
  id: string;
  document_id: string;
  user_id: string | null;
  department_id: string | null;
  permission: DocumentPermissionLevel;
  created_by: string;
  created_at: string;
}

export interface Citation {
  document_id: string;
  document_title: string;
  chunk_id: string | null;
  page_number: number;
  excerpt: string;

  evidence_text?: string | null;

  relevance_score: number | null;
  citation_order: number;
}

/** BR-3 follow-up: an ANSWERED message cut into sentences by the server's own recognition step. */
export interface AnswerSegment {
  kind: "verified" | "unverified";
  /** The sentence without its citation numbers. */
  text: string;
  /** citation_order values of the citations this sentence shows. */
  citation_ids: number[];
}

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  response_time_ms: number | null;
  citations: Citation[];
  created_at: string;
  /** BR-3: ANSWERED / NO_ANSWER on ASSISTANT messages; null on USER and on answers stored before it existed. */
  grounding_status: GroundingStatus | null;
  /** null on USER, NO_ANSWER and answers stored before the segments migration. */
  segments?: AnswerSegment[] | null;
}

export interface ChatSessionSummary {
  id: string;
  title: string | null;
  is_archived: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail {
  id: string;
  title: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
  message_pagination: PaginationMeta;
}

export interface ChatAnswerResponse {
  session_id: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  grounding_status: GroundingStatus;
  retrieved_chunk_count: number;
}

export interface Feedback {
  id: string;
  message_id: string;
  rating: FeedbackRating;
  reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface FeedbackReportItem extends Feedback {
  user_id: string;
  department_id: string | null;
  /** BR-4 option (a): present only for an Admin caller. */
  user_full_name?: string;
  department_name?: string | null;
}

export interface AuditLogItem {
  id: string;
  event_type: string;
  outcome: "SUCCESS" | "FAILURE";
  actor_user_id: string | null;
  target_type: string | null;
  target_id: string | null;
  request_id: string | null;
  error_code: string | null;
  metadata: Record<string, string | number | boolean | null>;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface HealthLiveResponse {
  status: string;
}

export interface HealthReadyResponse {
  status: string;
  checks: Record<string, string>;
  /** API_SPEC §11: what ranks retrieval candidates right now. */
  reranker_mode?: "cross_encoder" | "lexical_fallback" | "disabled";
}

// BR-8: TASK-032 Admin Monitoring shapes (only the fields the UI reads).
export type AdminCheckStatus = "ok" | "degraded" | "unavailable" | "disabled" | "misconfigured" | "not_configured";

export interface AdminHealthCheck {
  name: string;
  status: AdminCheckStatus;
  enabled: boolean;
  message: string | null;
}

export interface AdminHealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  generated_at: string;
  checks: AdminHealthCheck[];
}

export interface AdminProviderStatus {
  provider_type: "llm" | "web_search";
  provider: string;
  status: "healthy" | "disabled" | "misconfigured" | "unhealthy";
  enabled: boolean;
  configured: boolean;
  display_name: string | null;
  model: string | null;
  connectivity_checked: boolean;
  message: string | null;
}

export interface AdminVersionResponse {
  app_name: string;
  version: string;
  environment: string;
  python_version: string;
  api_prefix: string;
  migration_head: string;
  database_revision: string | null;
  started_at: string | null;
  uptime_seconds: number;
}

export interface AdminSystemResponse {
  generated_at: string;
  version: AdminVersionResponse;
  uptime_seconds: number;
  health: AdminHealthResponse;
  providers: { llm: AdminProviderStatus; web_search: AdminProviderStatus };
}

export interface StreamStartedPayload {
  request_id: string;
  session_id: string;
  provider?: string | null;
  model?: string | null;
  strategy: "buffer_after_validation";
}

export interface MessageDeltaPayload {
  sequence: number;
  content: string;
}

export interface CitationsReadyPayload {
  citations: Citation[];
}

export interface MessageCompletedPayload {
  message_id: string;
  session_id: string;
  content: string;
  citations: Citation[];
  provider?: string | null;
  model?: string | null;
  usage?: Record<string, number> | null;
  grounding_status: GroundingStatus;
  retrieved_chunk_count: number;
  segments?: AnswerSegment[] | null;
}

export interface StreamErrorPayload {
  code: string;
  message: string;
  retryable: boolean;
}

export type StreamEventName =
  | "stream.started"
  | "heartbeat"
  | "message.delta"
  | "citations.ready"
  | "message.completed"
  | "stream.error"
  | "stream.cancelled";

export type StreamEvent =
  | { event: "stream.started"; id?: string; data: StreamStartedPayload }
  | { event: "heartbeat"; id?: string; data: Record<string, never> }
  | { event: "message.delta"; id?: string; data: MessageDeltaPayload }
  | { event: "citations.ready"; id?: string; data: CitationsReadyPayload }
  | { event: "message.completed"; id?: string; data: MessageCompletedPayload }
  | { event: "stream.error"; id?: string; data: StreamErrorPayload }
  | { event: "stream.cancelled"; id?: string; data: StreamErrorPayload };
