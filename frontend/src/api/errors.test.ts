import { describe, expect, it } from "vitest";
import { parseApiError, parseRetryAfter, safeErrorMessage } from "./errors";

describe("API error parsing", () => {
  it("maps backend error envelopes with request id and retry metadata", async () => {
    const response = new Response(JSON.stringify({ error: { code: "RATE_LIMIT_EXCEEDED", message: "Slow down", request_id: "req-1", details: { limit: 1 } } }), {
      status: 429,
      headers: { "Retry-After": "15" },
    });

    const error = await parseApiError(response);

    expect(error.code).toBe("RATE_LIMIT_EXCEEDED");
    expect(error.message).toBe("Slow down");
    expect(error.requestId).toBe("req-1");
    expect(error.retryable).toBe(true);
    expect(error.retryAfterSeconds).toBe(15);
  });

  it("falls back to safe client messages for malformed bodies", async () => {
    const response = new Response("not json", { status: 503, headers: { "X-Request-ID": "req-2" } });

    const error = await parseApiError(response);

    expect(error.code).toBe("INTERNAL_ERROR");
    expect(error.message).toBe("The service is temporarily unavailable.");
    expect(error.requestId).toBe("req-2");
  });

  it("does not expose unknown errors directly", () => {
    expect(safeErrorMessage(new Error("raw stack detail"))).toBe("Unexpected error.");
    expect(parseRetryAfter("0")).toBeNull();
    expect(parseRetryAfter("20")).toBe(20);
  });
});
