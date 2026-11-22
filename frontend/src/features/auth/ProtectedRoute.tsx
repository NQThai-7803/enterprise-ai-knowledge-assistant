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
  // Remember a signed-in session (derived state from earlier renders) to tell an explicit logout apart.
  const [wasAuthenticated, setWasAuthenticated] = useState(false);
  if (status === "authenticated" && !wasAuthenticated) {
    setWasAuthenticated(true);
  }

  if (status === "loading") {
    return <LoadingState label="Đang tải phiên đăng nhập" />;
  }

  if (status !== "authenticated" || !user) {
    // After an explicit logout the next person signs in fresh, not on the previous user's last page;
    // an expired session or a tab opened without a token (D-7 viewer) still returns where it was.
    const loggedOut = wasAuthenticated && status === "unauthenticated";
    return (
      <Navigate to="/login" replace state={loggedOut ? null : { from: `${location.pathname}${location.search}` }} />
    );
  }

  if (roles && !hasRole(user, roles)) {
    return <Navigate to="/access-denied" replace />;
  }

  return <>{children}</>;
}