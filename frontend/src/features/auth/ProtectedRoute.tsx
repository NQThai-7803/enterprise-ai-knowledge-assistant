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

  if (status === "loading") {
    return <LoadingState label="Loading session" />;
  }

  if (status !== "authenticated" || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (roles && !hasRole(user, roles)) {
    return <Navigate to="/access-denied" replace />;
  }

  return <>{children}</>;
}