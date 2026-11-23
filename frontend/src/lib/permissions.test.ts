import { describe, expect, it } from "vitest";
import type { AuthenticatedUser } from "../api/types";
import { canManageDepartments, canManageDocumentPermissions, canManageUsers, canUploadDocuments, canViewAuditLogs, canViewFeedbackReport, roleLabel, visibleDepartmentName } from "./permissions";

const user = (role: AuthenticatedUser["role"]): AuthenticatedUser => ({
  id: role.toLowerCase(),
  email: `${role.toLowerCase()}@example.com`,
  full_name: role,
  role,
  department_id: null,
  department_name: null,
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

  it("names the viewer's own department from /auth/me, others only from the response key", () => {
    const staff = { ...user("STAFF"), department_id: "d-hr", department_name: "Nhân sự" };

    expect(visibleDepartmentName("d-hr", undefined, staff)).toBe("Nhân sự");
    expect(visibleDepartmentName("d-other", undefined, staff)).toBeNull();
    expect(visibleDepartmentName("d-other", "Kế toán", user("ADMIN"))).toBe("Kế toán");
    expect(visibleDepartmentName(null, "Kế toán", user("ADMIN"))).toBeNull();
  });

  it("renders stable role labels", () => {
    expect(roleLabel("STAFF")).toBe("Nhân viên");
    expect(roleLabel("ADMIN")).toBe("Quản trị viên");
  });
});
