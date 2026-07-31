import { describe, expect, it } from "vitest";
import type { StreamEvent } from "../../api/types";
import { applyChatStreamEvent, cancelChatStreamState, connectingChatStreamState, initialChatStreamState } from "./streamState";

const completedEvent: StreamEvent = {
  event: "message.completed",
  id: "evt-complete",
  data: {
    message_id: "m1",
    session_id: "s1",
    content: "Validated final answer",
    citations: [],
    grounding_status: "ANSWERED",
    retrieved_chunk_count: 2,
  },
};

describe("chat stream state machine", () => {
  it("starts with stream.started and captures safe metadata", () => {
    const state = applyChatStreamEvent(connectingChatStreamState(), {
      event: "stream.started",
      id: "evt-start",
      data: { request_id: "req-1", session_id: "s1", provider: "openai-compatible", model: "test", strategy: "buffer_after_validation" },
    });

    expect(state.status).toBe("started");
    expect(state.requestId).toBe("req-1");
    expect(state.strategy).toBe("buffer_after_validation");
    expect(state.terminal).toBe(false);
  });

  it("keeps delta sequence monotonic and ignores stale deltas", () => {
    const first = applyChatStreamEvent(initialChatStreamState, { event: "message.delta", id: "d1", data: { sequence: 1, content: "A" } });
    const stale = applyChatStreamEvent(first, { event: "message.delta", id: "d0", data: { sequence: 1, content: "B" } });

    expect(first.content).toBe("A");
    expect(stale.content).toBe("A");
    expect(stale.sequence).toBe(1);
  });

  it("uses completed content as the source of truth and emits terminal once", () => {
    const receiving = applyChatStreamEvent(initialChatStreamState, { event: "message.delta", id: "d1", data: { sequence: 1, content: "Partial" } });
    const completed = applyChatStreamEvent(receiving, completedEvent);
    const ignored = applyChatStreamEvent(completed, { event: "message.delta", id: "late", data: { sequence: 2, content: "late" } });

    expect(completed.status).toBe("completed");
    expect(completed.content).toBe("Validated final answer");
    expect(completed.terminal).toBe(true);
    expect(ignored).toBe(completed);
  });

  it("terminates on safe stream errors", () => {
    const state = applyChatStreamEvent(initialChatStreamState, { event: "stream.error", data: { code: "LLM_PROVIDER_TIMEOUT", message: "Timed out", retryable: true } });

    expect(state.status).toBe("error");
    expect(state.terminal).toBe(true);
    expect(state.error?.code).toBe("LLM_PROVIDER_TIMEOUT");
  });

  it("can be cancelled and ignores later events", () => {
    const cancelled = cancelChatStreamState(initialChatStreamState);
    const ignored = applyChatStreamEvent(cancelled, completedEvent);

    expect(cancelled.status).toBe("cancelled");
    expect(cancelled.terminal).toBe(true);
    expect(ignored).toBe(cancelled);
  });
});
