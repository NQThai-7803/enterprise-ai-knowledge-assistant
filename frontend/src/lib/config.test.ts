import { afterEach, describe, expect, it, vi } from "vitest";

// VITE_API_BASE_URL is read once, when config.ts is imported: each case loads the modules afresh.
async function requestedUrls(base: string | undefined): Promise<string[]> {
  vi.resetModules();
  vi.stubEnv("VITE_API_BASE_URL", base);
  const fetchMock = vi.fn<typeof fetch>(
    async () =>
      new Response(JSON.stringify({ error: { code: "SERVICE_UNAVAILABLE", message: "x", details: null, request_id: "r" } }), {
        status: 503,
        headers: { "Content-Type": "application/json" },
      }),
  );
  vi.stubGlobal("fetch", fetchMock);
  const { apiClient } = await import("../api/client");
  const { streamChatMessage } = await import("../api/sse");
  await apiClient.health.live().catch(() => undefined);
  await apiClient.auth.login({ email: "a@example.test", password: "x" }).catch(() => undefined);
  const signal = new AbortController().signal;
  await streamChatMessage({ sessionId: "s1", content: "x", signal, onEvent: () => undefined }).catch(() => undefined);
  return fetchMock.mock.calls.map(([input]) => String(input));
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe("VITE_API_BASE_URL", () => {
  it("unset: the dev API on 127.0.0.1:8000", async () => {
    expect(await requestedUrls(undefined)).toEqual([
      "http://127.0.0.1:8000/health/live",
      "http://127.0.0.1:8000/api/v1/auth/login",
      "http://127.0.0.1:8000/api/v1/chat/sessions/s1/messages/stream",
    ]);
  });

  it('"": the page\'s own origin (a same-origin proxy)', async () => {
    const urls = await requestedUrls("");
    expect(urls.slice(0, 2)).toEqual([`${window.location.origin}/health/live`, `${window.location.origin}/api/v1/auth/login`]);
    // The stream URL is relative, so fetch sends it to the same origin as well.
    expect(urls[2]).toBe("/api/v1/chat/sessions/s1/messages/stream");
    expect(new URL(urls[2], window.location.href).origin).toBe(window.location.origin);
  });

  it("absolute: kept as given, trailing slash trimmed (dev on 5173 calling another port)", async () => {
    expect(await requestedUrls("http://127.0.0.1:18300/")).toEqual([
      "http://127.0.0.1:18300/health/live",
      "http://127.0.0.1:18300/api/v1/auth/login",
      "http://127.0.0.1:18300/api/v1/chat/sessions/s1/messages/stream",
    ]);
  });
});
