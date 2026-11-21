import type { AuthenticatedUser, DocumentItem } from "../../api/types";

// JSON examples copied from API_SPEC.md / docs/ui/backend-requests.md (BR-1, BR-4), with "uuid" kept.

export const contractDocument: DocumentItem = {
  id: "uuid",
  title: "Quy định nghỉ phép",
  description: null,
  document_code: "ND-HR-007",
  document_version: "1.0",
  effective_from: "2026-09-01",
  effective_to: null,
  lifecycle_status: "ACTIVE",
  supersedes_document_id: null,
  original_filename: "nghi-phep.pdf",
  mime_type: "application/pdf",
  file_size: 182340,
  status: "UPLOADED",
  access_scope: "DEPARTMENT",
  department_id: "uuid",
  uploaded_by: "uuid",
  created_at: "2026-11-20T08:00:00Z",
  updated_at: "2026-11-20T08:00:00Z",
  uploaded_by_me: false,
};

// BR-4 option (a): the same document as an Admin receives it (names only for Admin).
export const contractDocumentForAdmin: DocumentItem = {
  ...contractDocument,
  uploaded_by_name: "Nguyễn Văn A",
  department_name: "Nhân sự",
};

export const contractManager: AuthenticatedUser = {
  id: "uuid",
  email: "manager@example.com",
  full_name: "Manager Nhân sự",
  role: "MANAGER",
  department_id: "uuid",
  department_name: "Nhân sự",
  is_active: true,
};
