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

// Vietnamese text for the documented codes (API_ERROR_CODES.md); unknown codes keep the server's message.
const ERROR_TEXT_VI: Record<string, string> = {
  VALIDATION_ERROR: "Dữ liệu gửi lên chưa hợp lệ.",
  INVALID_CREDENTIALS: "Email hoặc mật khẩu không đúng.",
  ACCESS_TOKEN_INVALID: "Phiên đăng nhập không hợp lệ. Hãy đăng nhập lại.",
  TOKEN_EXPIRED: "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.",
  REFRESH_TOKEN_INVALID: "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.",
  USER_INACTIVE: "Tài khoản đã bị vô hiệu hóa. Liên hệ quản trị viên.",
  FORBIDDEN: "Bạn không có quyền thực hiện thao tác này.",
  RESOURCE_NOT_FOUND: "Không tìm thấy dữ liệu, hoặc bạn không có quyền xem.",
  USER_EMAIL_ALREADY_EXISTS: "Email này đã được dùng.",
  DEPARTMENT_NAME_ALREADY_EXISTS: "Tên phòng ban đã tồn tại.",
  DEPARTMENT_CODE_ALREADY_EXISTS: "Mã phòng ban đã tồn tại.",
  DEPARTMENT_IN_USE: "Phòng ban vẫn còn người dùng đang hoạt động.",
  DEPARTMENT_HAS_DOCUMENTS: "Phòng ban vẫn còn tài liệu.",
  LAST_ACTIVE_ADMIN: "Không thể bỏ quản trị viên đang hoạt động cuối cùng.",
  SELF_MODIFICATION_NOT_ALLOWED: "Bạn không thể tự đổi vai trò hoặc trạng thái của chính mình.",
  DOCUMENT_NOT_READY: "Tài liệu chưa sẵn sàng.",
  DOCUMENT_PROCESSING: "Tài liệu đang được xử lý.",
  DOCUMENT_ALREADY_PROCESSING: "Tài liệu đang được xử lý lại.",
  DOCUMENT_FILE_TYPE_INVALID: "Định dạng tệp không được hỗ trợ.",
  DOCUMENT_FILE_TOO_LARGE: "Tệp vượt quá dung lượng cho phép.",
  DOCUMENT_FILE_EMPTY: "Tệp rỗng.",
  DOCUMENT_FILE_SIGNATURE_INVALID: "Tệp không phải PDF hợp lệ.",
  DOCUMENT_FILENAME_INVALID: "Tên tệp không hợp lệ.",
  REQUEST_TOO_LARGE: "Dữ liệu gửi lên quá lớn.",
  DUPLICATE_DOCUMENT: "Tệp này đã được tải lên trước đó.",
  DOCUMENT_FILE_UNAVAILABLE: "Tệp gốc của tài liệu không còn trên máy chủ.",
  DOCUMENT_PERMISSION_ALREADY_EXISTS: "Quyền này đã tồn tại.",
  FEEDBACK_TARGET_NOT_FOUND: "Không tìm thấy câu trả lời để đánh giá.",
  FEEDBACK_RATING_INVALID: "Đánh giá không hợp lệ.",
  FEEDBACK_REASON_TOO_LONG: "Ghi chú quá dài.",
  FEEDBACK_DATE_RANGE_INVALID: "Khoảng ngày không hợp lệ.",
  FEEDBACK_REPORT_FORBIDDEN: "Bạn không có quyền xem báo cáo phản hồi.",
  FEEDBACK_REPORT_SCOPE_UNAVAILABLE: "Bạn chưa thuộc phòng ban nào nên chưa xem được báo cáo này.",
  FEEDBACK_OPERATION_FAILED: "Không lưu được phản hồi. Thử lại sau.",
  AUDIT_REPORT_FORBIDDEN: "Bạn không có quyền xem nhật ký.",
  AUDIT_DATE_RANGE_INVALID: "Khoảng ngày không hợp lệ.",
  AUDIT_FILTER_INVALID: "Bộ lọc nhật ký không hợp lệ.",
  AUDIT_OPERATION_FAILED: "Không tải được nhật ký. Thử lại sau.",
  CHAT_SESSION_NOT_FOUND: "Không tìm thấy cuộc trò chuyện.",
  PROVIDER_UNAVAILABLE: "Dịch vụ mô hình tạm thời không phản hồi.",
  LLM_NOT_CONFIGURED: "Mô hình ngôn ngữ chưa được cấu hình.",
  LLM_PROVIDER_UNSUPPORTED: "Mô hình ngôn ngữ chưa được cấu hình đúng.",
  LLM_PROVIDER_AUTHENTICATION_FAILED: "Dịch vụ mô hình từ chối xác thực.",
  LLM_PROVIDER_RATE_LIMITED: "Dịch vụ mô hình đang quá tải. Thử lại sau.",
  LLM_PROVIDER_TIMEOUT: "Mô hình phản hồi quá lâu. Thử lại sau.",
  LLM_PROVIDER_UNAVAILABLE: "Dịch vụ mô hình tạm thời không phản hồi.",
  LLM_PROVIDER_BAD_RESPONSE: "Mô hình trả về dữ liệu không hợp lệ.",
  LLM_REQUEST_REJECTED: "Dịch vụ mô hình từ chối yêu cầu.",
  STREAM_TIMEOUT: "Câu trả lời mất quá nhiều thời gian nên đã dừng.",
  STREAM_INTERNAL_ERROR: "Không hoàn tất được câu trả lời.",
  STREAM_CANCELLED: "Câu trả lời đã bị dừng.",
  DATABASE_UNAVAILABLE: "Cơ sở dữ liệu tạm thời không phản hồi.",
  RATE_LIMIT_EXCEEDED: "Bạn gửi quá nhiều yêu cầu. Thử lại sau ít phút.",
  INTERNAL_ERROR: "Đã xảy ra lỗi trên máy chủ.",
};

/** The Vietnamese text of an error code, or the given message when the code is not documented. */
export function errorText(code: string, message: string): string {
  return ERROR_TEXT_VI[code] ?? message;
}

export function safeErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return errorText(error.code, error.message);
  }
  if (error instanceof Error && error.name === "AbortError") {
    return "Yêu cầu đã bị hủy.";
  }
  return "Đã xảy ra lỗi không mong muốn.";
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
  if (status === 401) return "Hãy đăng nhập lại.";
  if (status === 403) return "Bạn không có quyền thực hiện thao tác này.";
  if (status === 404) return "Không tìm thấy dữ liệu được yêu cầu.";
  if (status === 429) return "Bạn gửi quá nhiều yêu cầu.";
  if (status >= 500) return "Dịch vụ tạm thời không phản hồi.";
  return "Yêu cầu không thành công.";
}
