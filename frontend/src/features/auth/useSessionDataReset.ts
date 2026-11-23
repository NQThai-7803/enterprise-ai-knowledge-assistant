import { useQueryClient } from "@tanstack/react-query";
import { useLayoutEffect, useState } from "react";
import { useToast } from "../../components/feedback/ToastProvider";
import { useAuth } from "./AuthProvider";

/**
 * Session boundary: when the signed-in user changes (login, logout, expired session), queries in
 * flight are cancelled and the whole React Query cache (queries and mutations) is cleared, so the
 * next user never sees cached data of the previous one. Returns false while the cache still belongs
 * to another user; App renders nothing then, so a new user's pages mount on an empty cache.
 * Toasts are cleared when a user signs in (a failed-logout toast stays on the login page until then).
 * Other per-user state lives in pages under ProtectedRoute (chat drafts, SSE streams, which abort on
 * unmount) and in sessionStorage tokens, which AuthProvider removes.
 */
export function useSessionDataReset(): boolean {
  const { status, user } = useAuth();
  const queryClient = useQueryClient();
  const { clearToasts } = useToast();
  const sessionUserId = status === "authenticated" ? (user?.id ?? null) : null;
  const [cacheOwner, setCacheOwner] = useState(sessionUserId);

  // Layout effect: runs before paint, so the gated frame is never visible.
  useLayoutEffect(() => {
    if (cacheOwner === sessionUserId) {
      return;
    }
    void queryClient.cancelQueries();
    queryClient.clear();
    if (sessionUserId !== null) {
      clearToasts();
    }
    setCacheOwner(sessionUserId);
  }, [cacheOwner, clearToasts, queryClient, sessionUserId]);

  // A signed-out tree renders at once: the old pages unmount and ProtectedRoute keeps its state.
  return cacheOwner === sessionUserId || sessionUserId === null;
}
