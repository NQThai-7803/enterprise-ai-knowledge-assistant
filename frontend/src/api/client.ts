import { appConfig } from "../lib/config";
import { parseApiError } from "./errors";
import {
  clearStoredTokens,
  getAccessToken,
  getRefreshToken,
  setStoredTokens,
} from "./tokenStore";
import type {
  AuditLogListResponse,
  AuthenticatedUser,
  ChatAnswerResponse,
  ChatSessionDetail,
  ChatSessionSummary,
  DataResponse,
  Department,
  DocumentAccessScope,
  DocumentItem,
  DocumentPermission,
  DocumentPermissionLevel,
  DocumentStatusResponse,
  Feedback,
  FeedbackRating,
  FeedbackReportItem,
  HealthLiveResponse,
  HealthReadyResponse,
  ListResponse,
  TokenPairData,
  User,
  UserRole,
} from "./types";

type QueryPrimitive = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryPrimitive>;

interface ApiRequestOptions extends Omit<RequestInit, "body" | "headers"> {
  auth?: boolean;
  body?: unknown;
  formData?: FormData;
  headers?: HeadersInit;
  query?: QueryParams;
  skipRefresh?: boolean;
  timeoutMs?: number;
}

interface DownloadResponse {
  blob: Blob;
  filename: string | null;
}

let refreshPromise: Promise<TokenPairData> | null = null;
const ACCESS_TOKEN_REFRESH_SKEW_SECONDS = 30;

export const apiClient = {
  auth: {
    login(payload: { email: string; password: string }) {
      return request<DataResponse<TokenPairData>>("/auth/login", {
        method: "POST",
        auth: false,
        body: payload,
      });
    },
    refresh(refreshToken: string) {
      return request<DataResponse<TokenPairData>>("/auth/refresh", {
        method: "POST",
        auth: false,
        skipRefresh: true,
        body: { refresh_token: refreshToken },
      });
    },
    logout(refreshToken: string) {
      return request<void>("/auth/logout", {
        method: "POST",
        body: { refresh_token: refreshToken },
      });
    },
    me() {
      return request<DataResponse<AuthenticatedUser>>("/auth/me");
    },
  },
  users: {
    list(query: {
      page?: number;
      page_size?: number;
      search?: string;
      role?: UserRole;
      department_id?: string;
      is_active?: boolean;
    }) {
      return request<ListResponse<User>>("/users", { query });
    },
    create(payload: {
      email: string;
      full_name: string;
      password: string;
      role: UserRole;
      department_id?: string | null;
    }) {
      return request<DataResponse<User>>("/users", { method: "POST", body: payload });
    },
    update(
      userId: string,
      payload: Partial<{
        email: string;
        full_name: string;
        role: UserRole;
        department_id: string | null;
        is_active: boolean;
      }>,
    ) {
      return request<DataResponse<User>>(`/users/${userId}`, {
        method: "PATCH",
        body: payload,
      });
    },
    deactivate(userId: string) {
      return request<void>(`/users/${userId}`, { method: "DELETE" });
    },
  },
  departments: {
    list(query: { page?: number; page_size?: number; search?: string }) {
      return request<ListResponse<Department>>("/departments", { query });
    },
    create(payload: { name: string; code: string; description?: string | null }) {
      return request<DataResponse<Department>>("/departments", {
        method: "POST",
        body: payload,
      });
    },
    update(
      departmentId: string,
      payload: Partial<{ name: string; code: string; description: string | null }>,
    ) {
      return request<DataResponse<Department>>(`/departments/${departmentId}`, {
        method: "PATCH",
        body: payload,
      });
    },
    delete(departmentId: string) {
      return request<void>(`/departments/${departmentId}`, { method: "DELETE" });
    },
  },
  documents: {
    list(query: {
      page?: number;
      page_size?: number;
      search?: string;
      status?: string;
      access_scope?: DocumentAccessScope;
      department_id?: string;
    }) {
      return request<ListResponse<DocumentItem>>("/documents", { query });
    },
    detail(documentId: string) {
      return request<DataResponse<DocumentItem>>(`/documents/${documentId}`);
    },
    status(documentId: string) {
      return request<DataResponse<DocumentStatusResponse>>(`/documents/${documentId}/status`);
    },
    upload(payload: {
      file: File;
      title: string;
      description?: string | null;
      access_scope: DocumentAccessScope;
      department_id?: string | null;
    }) {
      const formData = new FormData();
      formData.append("file", payload.file);
      formData.append("title", payload.title);
      formData.append("access_scope", payload.access_scope);
      if (payload.description) {
        formData.append("description", payload.description);
      }
      if (payload.department_id) {
        formData.append("department_id", payload.department_id);
      }
      return request<DataResponse<DocumentItem>>("/documents/upload", {
        method: "POST",
        formData,
        timeoutMs: 120_000,
      });
    },
    update(
      documentId: string,
      payload: Partial<{
        title: string;
        description: string | null;
        access_scope: DocumentAccessScope;
        department_id: string | null;
      }>,
    ) {
      return request<DataResponse<DocumentItem>>(`/documents/${documentId}`, {
        method: "PATCH",
        body: payload,
      });
    },
    delete(documentId: string) {
      return request<void>(`/documents/${documentId}`, { method: "DELETE" });
    },
    download(documentId: string) {
      return download(`/documents/${documentId}/download`);
    },
    permissions(documentId: string) {
      return request<DataResponse<DocumentPermission[]>>(`/documents/${documentId}/permissions`);
    },
    grantPermission(
      documentId: string,
      payload: {
        user_id?: string | null;
        department_id?: string | null;
        permission: DocumentPermissionLevel;
      },
    ) {
      return request<DataResponse<DocumentPermission>>(`/documents/${documentId}/permissions`, {
        method: "POST",
        body: payload,
      });
    },
    updatePermission(
      documentId: string,
      permissionId: string,
      payload: { permission: DocumentPermissionLevel },
    ) {
      return request<DataResponse<DocumentPermission>>(
        `/documents/${documentId}/permissions/${permissionId}`,
        { method: "PATCH", body: payload },
      );
    },
    revokePermission(documentId: string, permissionId: string) {
      return request<void>(`/documents/${documentId}/permissions/${permissionId}`, {
        method: "DELETE",
      });
    },
  },
  chat: {
    listSessions(query: { page?: number; page_size?: number; include_archived?: boolean }) {
      return request<ListResponse<ChatSessionSummary>>("/chat/sessions", { query });
    },
    createSession(payload: { title?: string | null }) {
      return request<DataResponse<ChatSessionSummary>>("/chat/sessions", {
        method: "POST",
        body: payload,
      });
    },
    session(sessionId: string, query?: { message_page?: number; message_page_size?: number }) {
      return request<DataResponse<ChatSessionDetail>>(`/chat/sessions/${sessionId}`, { query });
    },
    sendMessage(sessionId: string, payload: { content: string }) {
      return request<DataResponse<ChatAnswerResponse>>(`/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        body: payload,
        timeoutMs: 150_000,
      });
    },
  },
  feedback: {
    upsert(messageId: string, payload: { rating: FeedbackRating; reason?: string | null }) {
      return request<DataResponse<Feedback>>(`/messages/${messageId}/feedback`, {
        method: "PUT",
        body: payload,
      });
    },
    list(query: {
      page?: number;
      page_size?: number;
      rating?: FeedbackRating;
      department_id?: string;
      user_id?: string;
      date_from?: string;
      date_to?: string;
    }) {
      return request<ListResponse<FeedbackReportItem>>("/feedback", { query });
    },
  },
  audit: {
    list(query: {
      page?: number;
      page_size?: number;
      event_type?: string;
      outcome?: "SUCCESS" | "FAILURE";
      actor_user_id?: string;
      target_type?: string;
      target_id?: string;
      request_id?: string;
      error_code?: string;
      date_from?: string;
      date_to?: string;
    }) {
      return request<AuditLogListResponse>("/audit-logs", { query });
    },
  },
  health: {
    live() {
      return request<HealthLiveResponse>("/health/live", { auth: false, apiPrefix: false });
    },
    ready() {
      return request<HealthReadyResponse>("/health/ready", { auth: false, apiPrefix: false });
    },
  },
};

async function request<T>(
  path: string,
  options: ApiRequestOptions & { apiPrefix?: boolean } = {},
): Promise<T> {
  const {
    auth = true,
    body,
    formData,
    headers,
    query,
    skipRefresh = false,
    timeoutMs = 30_000,
    apiPrefix = true,
    ...requestInit
  } = options;

  const response = await fetchWithTimeout(buildUrl(path, query, apiPrefix), {
    ...requestInit,
    headers: buildHeaders({ auth, headers, hasJsonBody: body !== undefined, hasFormData: !!formData }),
    body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
    timeoutMs,
  });

  if (response.ok) {
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  if (auth && response.status === 401 && !skipRefresh) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request<T>(path, { ...options, skipRefresh: true });
    }
  }

  throw await parseApiError(response);
}

async function download(path: string): Promise<DownloadResponse> {
  const response = await fetchWithTimeout(buildUrl(path, undefined, true), {
    method: "GET",
    headers: buildHeaders({ auth: true }),
    timeoutMs: 120_000,
  });
  if (!response.ok) {
    throw await parseApiError(response);
  }
  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get("Content-Disposition")),
  };
}

export async function ensureFreshAccessToken(): Promise<boolean> {
  const accessToken = getAccessToken();
  if (accessToken && !isAccessTokenExpired(accessToken)) {
    return true;
  }
  return refreshAccessToken();
}

export async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearStoredTokens();
    window.dispatchEvent(new CustomEvent("auth:expired"));
    return false;
  }

  refreshPromise ??= apiClient.auth
    .refresh(refreshToken)
    .then((response) => {
      setStoredTokens({
        accessToken: response.data.access_token,
        refreshToken: response.data.refresh_token,
      });
      return response.data;
    })
    .finally(() => {
      refreshPromise = null;
    });

  try {
    await refreshPromise;
    return true;
  } catch {
    clearStoredTokens();
    window.dispatchEvent(new CustomEvent("auth:expired"));
    return false;
  }
}

export function isAccessTokenExpired(
  token: string,
  nowSeconds = Math.floor(Date.now() / 1000),
  skewSeconds = ACCESS_TOKEN_REFRESH_SKEW_SECONDS,
): boolean {
  const payload = decodeJwtPayload(token);
  if (typeof payload?.exp !== "number") {
    return false;
  }
  return payload.exp <= nowSeconds + skewSeconds;
}

function decodeJwtPayload(token: string): { exp?: unknown } | null {
  const payload = token.split(".")[1];
  if (!payload) {
    return null;
  }
  try {
    return JSON.parse(base64UrlDecode(payload)) as { exp?: unknown };
  } catch {
    return null;
  }
}

function base64UrlDecode(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(
    normalized.length + ((4 - (normalized.length % 4)) % 4),
    "=",
  );
  return window.atob(padded);
}

function buildHeaders({
  auth,
  headers,
  hasJsonBody = false,
  hasFormData = false,
}: {
  auth: boolean;
  headers?: HeadersInit;
  hasJsonBody?: boolean;
  hasFormData?: boolean;
}): Headers {
  const built = new Headers(headers);
  built.set("Accept", built.get("Accept") ?? "application/json");
  if (hasJsonBody && !hasFormData) {
    built.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getAccessToken();
    if (token) {
      built.set("Authorization", `Bearer ${token}`);
    }
  }
  return built;
}

function buildUrl(path: string, query?: QueryParams, apiPrefix = true): string {
  const url = new URL(`${appConfig.apiBaseUrl}${apiPrefix ? appConfig.apiPrefix : ""}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit & { timeoutMs: number },
): Promise<Response> {
  const { timeoutMs, signal, ...requestOptions } = options;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  signal?.addEventListener("abort", onAbort, { once: true });

  try {
    return await fetch(url, {
      ...requestOptions,
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timeout);
    signal?.removeEventListener("abort", onAbort);
  }
}

function filenameFromDisposition(disposition: string | null): string | null {
  if (!disposition) {
    return null;
  }
  const match = /filename="([^"]+)"/i.exec(disposition);
  return match?.[1] ?? null;
}
