import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiClient } from "../../api/client";
import {
  clearStoredTokens,
  getRefreshToken,
  getStoredTokens,
  setStoredTokens,
} from "../../api/tokenStore";
import type { AuthenticatedUser } from "../../api/types";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "expired";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthenticatedUser | null;
  login: (payload: { email: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
  reloadCurrentUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthenticatedUser | null>(null);

  const loadCurrentUser = useCallback(async () => {
    const tokens = getStoredTokens();
    if (!tokens) {
      setUser(null);
      setStatus("unauthenticated");
      return;
    }
    try {
      const response = await apiClient.auth.me();
      setUser(response.data);
      setStatus("authenticated");
    } catch {
      clearStoredTokens();
      setUser(null);
      setStatus("expired");
    }
  }, []);

  useEffect(() => {
    void loadCurrentUser();
    const onExpired = () => {
      clearStoredTokens();
      setUser(null);
      setStatus("expired");
    };
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, [loadCurrentUser]);

  const login = useCallback(async (payload: { email: string; password: string }) => {
    const response = await apiClient.auth.login(payload);
    setStoredTokens({
      accessToken: response.data.access_token,
      refreshToken: response.data.refresh_token,
    });
    setUser(response.data.user);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) {
        await apiClient.auth.logout(refreshToken);
      }
    } finally {
      clearStoredTokens();
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, logout, reloadCurrentUser: loadCurrentUser }),
    [loadCurrentUser, login, logout, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}