import type {
  AuditLogItem,
  DocumentAccessScope,
  DocumentPermissionLevel,
  DocumentStatus,
  FeedbackRating,
  UserRole,
} from "../api/types";

// Vietnamese display labels. Enum values stay the internal contract; only these strings are shown.

export const roleLabels: Record<UserRole, string> = {
  ADMIN: "Quản trị viên",
  MANAGER: "Quản lý",
  STAFF: "Nhân viên",
};

export const documentStatusLabels: Record<DocumentStatus, string> = {
  UPLOADED: "Đã tải lên",
  PROCESSING: "Đang xử lý",
  READY: "Sẵn sàng",
  FAILED: "Lỗi",
  ARCHIVED: "Lưu trữ",
};

export const accessScopeLabels: Record<DocumentAccessScope, string> = {
  ORGANIZATION: "Toàn công ty",
  DEPARTMENT: "Phòng ban",
  PRIVATE: "Riêng tư",
};

export const permissionLevelLabels: Record<DocumentPermissionLevel, string> = {
  VIEW: "Xem",
  EDIT: "Sửa",
  MANAGE: "Quản lý",
};

export const feedbackRatingLabels: Record<FeedbackRating, string> = {
  HELPFUL: "Hữu ích",
  NOT_HELPFUL: "Chưa hữu ích",
};

export const auditOutcomeLabels: Record<AuditLogItem["outcome"], string> = {
  SUCCESS: "Thành công",
  FAILURE: "Thất bại",
};
