import type { AuthenticatedUser, UserRole } from "../api/types";
import { roleLabels } from "./labels";

export function hasRole(user: AuthenticatedUser | null, roles: UserRole[]): boolean {
  return Boolean(user && roles.includes(user.role));
}

export function canManageUsers(user: AuthenticatedUser | null): boolean {
  return hasRole(user, ["ADMIN"]);
}

export function canManageDepartments(user: AuthenticatedUser | null): boolean {
  return hasRole(user, ["ADMIN"]);
}

export function canUploadDocuments(user: AuthenticatedUser | null): boolean {
  return hasRole(user, ["ADMIN", "MANAGER"]);
}

export function canManageDocumentPermissions(user: AuthenticatedUser | null): boolean {
  return hasRole(user, ["ADMIN"]);
}

export function canViewFeedbackReport(user: AuthenticatedUser | null): boolean {
  return hasRole(user, ["ADMIN", "MANAGER"]);
}

export function canViewAuditLogs(user: AuthenticatedUser | null): boolean {
  return hasRole(user, ["ADMIN"]);
}

export function roleLabel(role: UserRole): string {
  return roleLabels[role];
}

/**
 * BR-4: a department name the viewer may see. Their own department is named from /auth/me; any other
 * only when the response carries the key (Admin callers). Never looked up through another call.
 */
export function visibleDepartmentName(
  departmentId: string | null,
  responseName: string | null | undefined,
  user: AuthenticatedUser | null,
): string | null {
  if (!departmentId) {
    return null;
  }
  if (user?.department_id === departmentId && user.department_name) {
    return user.department_name;
  }
  return responseName ?? null;
}
