import { afterEach, describe, expect, it, vi } from "vitest";
import { refreshAccessToken } from "./client";
import { clearStoredTokens, getStoredTokens, setStoredTokens } from "./tokenStore";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const newTokens = json({
  data: {
    access_token: "new-access",
    refresh_token: "new-refresh",
    token_type: "bearer",
    expires_in: 900,
    user: { id: "admin-1", email: "admin@example.test", full_name: "Admin", role: "ADMIN", department_id: null, department_name: null, is_active: true },
  },
  meta: null,
});

const refreshRefused = json(
  { error: { code: "REFRESH_TOKEN_INVALID", message: "Refresh token is invalid.", details: null, request_id: "req-1" } },
  401,
);

/** Holds POST /auth/refresh until the test answers it, so the session can change meanwhile. */
async function startHeldRefresh() {
  let answer!: (response: Response) => void;
  const fetchMock = vi.fn(() => new Promise<Response>((resolve) => (answer = resolve)));
  vi.stubGlobal("fetch", fetchMock);
  const refreshing = refreshAccessToken();
  await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  return { refreshing, answer: (response: Response) => answer(response) };
}

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe("refreshAccessToken compare-and-set", () => {
  it("stores the new tokens when the session did not change", async () => {
    setStoredTokens({ accessToken: "old-access", refreshToken: "old-refresh" });
    const { refreshing, answer } = await startHeldRefresh();
    answer(newTokens.clone());

    expect(await refreshing).toBe(true);
    expect(getStoredTokens()).toEqual({ accessToken: "new-access", refreshToken: "new-refresh" });
  });

  it("drops tokens that arrive after a logout", async () => {
    setStoredTokens({ accessToken: "old-access", refreshToken: "old-refresh" });
    const { refreshing, answer } = await startHeldRefresh();
    clearStoredTokens(); // the logout, while the refresh runs
    answer(newTokens.clone());

    expect(await refreshing).toBe(false);
    expect(sessionStorage.length).toBe(0);
  });

  it("leaves a newer session alone when the old refresh fails", async () => {
    const expired = vi.fn();
    window.addEventListener("auth:expired", expired);
    setStoredTokens({ accessToken: "old-access", refreshToken: "old-refresh" });
    const { refreshing, answer } = await startHeldRefresh();
    setStoredTokens({ accessToken: "staff-access", refreshToken: "staff-refresh" }); // logout, then staff signs in
    answer(refreshRefused.clone());

    expect(await refreshing).toBe(false);
    expect(getStoredTokens()).toEqual({ accessToken: "staff-access", refreshToken: "staff-refresh" });
    expect(expired).not.toHaveBeenCalled();
    window.removeEventListener("auth:expired", expired);
  });

  it("still ends its own session when the refresh fails", async () => {
    const expired = vi.fn();
    window.addEventListener("auth:expired", expired);
    setStoredTokens({ accessToken: "old-access", refreshToken: "old-refresh" });
    const { refreshing, answer } = await startHeldRefresh();
    answer(refreshRefused.clone());

    expect(await refreshing).toBe(false);
    expect(sessionStorage.length).toBe(0);
    expect(expired).toHaveBeenCalledTimes(1);
    window.removeEventListener("auth:expired", expired);
  });
});
