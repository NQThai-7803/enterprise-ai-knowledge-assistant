export type UserRole = "ADMIN" | "MANAGER" | "STAFF";

export type DocumentStatus = "UPLOADED" | "PROCESSING" | "READY" | "FAILED" | "ARCHIVED";
export type DocumentAccessScope = "PRIVATE" | "DEPARTMENT" | "ORGANIZATION";
export type DocumentPermissionLevel = "VIEW" | "EDIT" | "MANAGE";
export type FeedbackRating = "HELPFUL" | "NOT_HELPFUL";
export type ChatMessageRole = "USER" | "ASSISTANT";
export type GroundingStatus = "ANSWERED" | "NO_ANSWER";

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
  original_filename: string;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  access_scope: DocumentAccessScope;
  department_id: string | null;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
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
  relevance_score: number | null;
  citation_order: number;
}

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  response_time_ms: number | null;
  citations: Citation[];
  created_at: string;
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
