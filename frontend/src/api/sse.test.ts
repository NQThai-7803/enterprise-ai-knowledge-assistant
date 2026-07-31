import { describe, expect, it, vi, afterEach } from "vitest";
import { parseStreamEvent, SseParser, streamChatMessage } from "./sse";

describe("SseParser", () => {
  it("handles split chunks and parses event fields", () => {
    const parser = new SseParser();

    expect(parser.feed('event: message.delta\nid: evt-1\ndata: {"sequence":1,')).toEqual([]);
    const raw = parser.feed('"content":"Xin chao"}\n\n');

    expect(raw).toHaveLength(1);
    expect(raw[0]).toEqual({ event: "message.delta", id: "evt-1", data: '{"sequence":1,"content":"Xin chao"}' });
    expect(parseStreamEvent(raw[0])).toMatchObject({ event: "message.delta", data: { sequence: 1, content: "Xin chao" } });
  });

  it("handles multiple events in one chunk", () => {
    const parser = new SseParser();
    const raw = parser.feed([
      'event: stream.started',
      'data: {"request_id":"req-1","session_id":"s1","strategy":"buffer_after_validation"}',
      '',
      'event: message.delta',
      'data: {"sequence":1,"content":"Done"}',
      '',
      '',
    ].join("\n"));

    expect(raw.map((event) => event.event)).toEqual(["stream.started", "message.delta"]);
  });

  it("supports unicode and JSON newline escaping without raw SSE injection", () => {
    const parser = new SseParser();
    const raw = parser.feed('event: message.delta\ndata: {"sequence":1,"content":"Tieng Viet: xin chao\\nDong 2"}\n\n');
    const parsed = parseStreamEvent(raw[0]);

    expect(parsed).toMatchObject({ event: "message.delta", data: { content: "Tieng Viet: xin chao\nDong 2" } });
  });

  it("ignores comment heartbeat frames", () => {
    const parser = new SseParser();

    expect(parser.feed(': heartbeat\n\n')).toEqual([]);
  });

  it("flushes a final event without a trailing blank line", () => {
    const parser = new SseParser();

    expect(parser.feed('event: heartbeat\ndata: {}')).toEqual([]);
    expect(parser.finish()).toEqual([{ event: "heartbeat", data: "{}" }]);
  });

  it("rejects unknown events and malformed JSON safely", () => {
    expect(() => parseStreamEvent({ event: "provider.raw", data: "{}" })).toThrow("Unknown stream event.");
    expect(() => parseStreamEvent({ event: "message.delta", data: "not json" })).toThrow("Malformed stream event JSON.");
  });
});

describe("streamChatMessage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the stream request without putting tokens in the URL", async () => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('event: message.completed\ndata: {"message_id":"m1","session_id":"s1","content":"Final","citations":[],"grounding_status":"ANSWERED","retrieved_chunk_count":1}\n\n'));
        controller.close();
      },
    });
    const fetchMock = vi.fn(async () => new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } }));
    vi.stubGlobal("fetch", fetchMock);

    const events: string[] = [];
    await streamChatMessage({
      sessionId: "s1",
      content: "Question",
      signal: new AbortController().signal,
      onEvent: (event) => events.push(event.event),
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toContain("/chat/sessions/s1/messages/stream");
    expect(url).not.toContain("token=");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>).Accept).toBe("text/event-stream");
    expect(events).toEqual(["message.completed"]);
  });

  it("ignores events after the first terminal event", async () => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode([
          'event: message.completed',
          'data: {"message_id":"m1","session_id":"s1","content":"Final","citations":[],"grounding_status":"ANSWERED","retrieved_chunk_count":1}',
          '',
          'event: message.delta',
          'data: {"sequence":2,"content":"late"}',
          '',
          '',
        ].join("\n")));
        controller.close();
      },
    });
    vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { status: 200 })));

    const events: string[] = [];
    await streamChatMessage({
      sessionId: "s1",
      content: "Question",
      signal: new AbortController().signal,
      onEvent: (event) => events.push(event.event),
    });

    expect(events).toEqual(["message.completed"]);
  });
});
