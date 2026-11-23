import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import type { UserRole } from "../../api/types";
import { LoadingState } from "../../components/ui/State";
import { hasRole } from "../../lib/permissions";
import { useAuth } from "./AuthProvider";

export function ProtectedRoute({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: UserRole[];
}) {
  const { status, user } = useAuth();
  const location = useLocation();
  // The user signed in on this route (derived state from earlier renders): tells an explicit logout
  // apart and binds an expired session's return path to that user.
  const [sessionUserId, setSessionUserId] = useState<string | null>(null);
  if (status === "authenticated" && user && user.id !== sessionUserId) {
    setSessionUserId(user.id);
  }

  if (status === "loading") {
    return <LoadingState label="Đang tải phiên đăng nhập" />;
  }

  if (status !== "authenticated" || !user) {
    // Return path: none after an explicit logout; for the same user only after an expired session
    // (LoginPage compares userId), none if whose session it was is unknown (a reload with a dead
    // token); for whoever signs in on a tab that never had a session (D-7 viewer without a token).
    const from = `${location.pathname}${location.search}`;
    let returnTo: { from: string; userId?: string } | null = null;
    if (status === "expired" && sessionUserId) {
      returnTo = { from, userId: sessionUserId };
    } else if (status !== "expired" && !sessionUserId) {
      returnTo = { from };
    }
    return <Navigate to="/login" replace state={returnTo} />;
  }

  if (roles && !hasRole(user, roles)) {
    return <Navigate to="/access-denied" replace />;
  }

  return <>{children}</>;
}