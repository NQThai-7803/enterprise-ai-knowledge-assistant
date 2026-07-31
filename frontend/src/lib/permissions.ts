import type { AuthenticatedUser, UserRole } from "../api/types";

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
  const labels: Record<UserRole, string> = {
    ADMIN: "Admin",
    MANAGER: "Manager",
    STAFF: "Staff",
  };
  return labels[role];
}
