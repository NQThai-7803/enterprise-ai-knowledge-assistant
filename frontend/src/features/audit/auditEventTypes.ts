// BR-9: the 23 stable event_type values of API_SPEC §10 ("Audit event types"), grouped for the filter.
export const AUDIT_EVENT_GROUPS = [
  { label: "Xác thực", types: ["AUTH_LOGIN_SUCCEEDED", "AUTH_LOGIN_FAILED"] },
  {
    label: "Người dùng",
    types: ["USER_CREATED", "USER_UPDATED", "USER_STATUS_CHANGED", "USER_DEACTIVATED", "USER_REACTIVATED"],
  },
  { label: "Phòng ban", types: ["DEPARTMENT_CREATED", "DEPARTMENT_UPDATED", "DEPARTMENT_DELETED"] },
  { label: "Tài liệu", types: ["DOCUMENT_UPLOADED", "DOCUMENT_UPDATED", "DOCUMENT_DOWNLOADED", "DOCUMENT_DELETED"] },
  {
    label: "Quyền tài liệu",
    types: ["DOCUMENT_PERMISSION_GRANTED", "DOCUMENT_PERMISSION_UPDATED", "DOCUMENT_PERMISSION_REVOKED"],
  },
  {
    label: "Trò chuyện",
    types: [
      "CHAT_SESSION_CREATED",
      "CHAT_SESSION_DELETED",
      "CHAT_QUESTION_SUBMITTED",
      "CHAT_ANSWER_GENERATED",
      "CHAT_NO_ANSWER_GENERATED",
    ],
  },
  { label: "Phản hồi", types: ["FEEDBACK_UPSERTED"] },
] as const;

/** Accepted by the filter but never written: deactivation and reactivation log USER_STATUS_CHANGED. */
export const RESERVED_AUDIT_EVENTS: ReadonlySet<string> = new Set(["USER_DEACTIVATED", "USER_REACTIVATED"]);

export const auditTargetLabels: Record<string, string> = {
  USER: "Người dùng",
  DEPARTMENT: "Phòng ban",
  DOCUMENT: "Tài liệu",
  DOCUMENT_PERMISSION: "Quyền tài liệu",
  CHAT_SESSION: "Phiên chat",
  CHAT_MESSAGE: "Tin nhắn",
  FEEDBACK: "Phản hồi",
};
