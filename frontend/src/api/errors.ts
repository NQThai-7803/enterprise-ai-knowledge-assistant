import type { ApiErrorEnvelope, ApiErrorPayload } from "./types";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId: string | null;
  readonly details: unknown;
  readonly retryable: boolean;
  readonly retryAfterSeconds: number | null;

  constructor({
    code,
    message,
    status,
    requestId = null,
    details = null,
    retryable = false,
    retryAfterSeconds = null,
  }: {
    code: string;
    message: string;
    status: number;
    requestId?: string | null;
    details?: unknown;
    retryable?: boolean;
    retryAfterSeconds?: number | null;
  }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.details = details;
    this.retryable = retryable;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

const RETRYABLE_STATUS = new Set([408, 409, 429, 500, 502, 503, 504]);

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

export function parseRetryAfter(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const seconds = Number.parseInt(value, 10);
  return Number.isFinite(seconds) && seconds > 0 ? seconds : null;
}

export async function parseApiError(response: Response): Promise<ApiError> {
  const retryAfterSeconds = parseRetryAfter(response.headers.get("Retry-After"));
  let payload: ApiErrorPayload | null;

  try {
    const body = (await response.json()) as Partial<ApiErrorEnvelope>;
    payload = body.error ?? null;
  } catch {
    payload = null;
  }

  return new ApiError({
    code: payload?.code ?? fallbackCodeForStatus(response.status),
    message: payload?.message ?? fallbackMessageForStatus(response.status),
    status: response.status,
    requestId: payload?.request_id ?? response.headers.get("X-Request-ID"),
    details: payload?.details ?? null,
    retryable: response.status === 429 || RETRYABLE_STATUS.has(response.status),
    retryAfterSeconds,
  });
}

export function safeErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.message;
  }
  if (error instanceof Error && error.name === "AbortError") {
    return "Request was cancelled.";
  }
  return "Unexpected error.";
}

function fallbackCodeForStatus(status: number): string {
  if (status === 401) return "ACCESS_TOKEN_INVALID";
  if (status === 403) return "FORBIDDEN";
  if (status === 404) return "RESOURCE_NOT_FOUND";
  if (status === 409) return "CONFLICT";
  if (status === 422) return "VALIDATION_ERROR";
  if (status === 429) return "RATE_LIMIT_EXCEEDED";
  if (status >= 500) return "INTERNAL_ERROR";
  return "HTTP_ERROR";
}

function fallbackMessageForStatus(status: number): string {
  if (status === 401) return "Please sign in again.";
  if (status === 403) return "You do not have permission to perform this action.";
  if (status === 404) return "The requested resource was not found.";
  if (status === 429) return "Too many requests.";
  if (status >= 500) return "The service is temporarily unavailable.";
  return "The request failed.";
}
