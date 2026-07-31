import { describe, expect, it } from "vitest";
import type { AuthenticatedUser } from "../api/types";
import { canManageDepartments, canManageDocumentPermissions, canManageUsers, canUploadDocuments, canViewAuditLogs, canViewFeedbackReport, roleLabel } from "./permissions";

const user = (role: AuthenticatedUser["role"]): AuthenticatedUser => ({
  id: role.toLowerCase(),
  email: `${role.toLowerCase()}@example.com`,
  full_name: role,
  role,
  department_id: null,
  is_active: true,
});

describe("permission helpers", () => {
  it("keeps admin-only routes admin-only", () => {
    expect(canManageUsers(user("ADMIN"))).toBe(true);
    expect(canManageUsers(user("MANAGER"))).toBe(false);
    expect(canManageDepartments(user("STAFF"))).toBe(false);
    expect(canManageDocumentPermissions(user("ADMIN"))).toBe(true);
    expect(canViewAuditLogs(user("MANAGER"))).toBe(false);
  });

  it("allows document upload and feedback reports for the intended roles", () => {
    expect(canUploadDocuments(user("ADMIN"))).toBe(true);
    expect(canUploadDocuments(user("MANAGER"))).toBe(true);
    expect(canUploadDocuments(user("STAFF"))).toBe(false);
    expect(canViewFeedbackReport(user("MANAGER"))).toBe(true);
  });

  it("renders stable role labels", () => {
    expect(roleLabel("STAFF")).toBe("Staff");
  });
});
