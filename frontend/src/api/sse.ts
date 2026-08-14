import { appConfig } from "../lib/config";
import { ensureFreshAccessToken, refreshAccessToken } from "./client";
import { parseApiError } from "./errors";
import { getAccessToken } from "./tokenStore";
import type { StreamEvent, StreamEventName } from "./types";

export interface RawSseEvent {
  id?: string;
  event: string;
  data: string;
}

export class SseParser {
  private buffer = "";
  private eventName = "message";
  private eventId: string | undefined;
  private dataLines: string[] = [];

  feed(chunk: string): RawSseEvent[] {
    this.buffer += chunk;
    const events: RawSseEvent[] = [];
    let newlineIndex = this.findNewline();

    while (newlineIndex !== -1) {
      const line = this.buffer.slice(0, newlineIndex.lineEnd);
      this.buffer = this.buffer.slice(newlineIndex.nextStart);
      const event = this.consumeLine(line);
      if (event) {
        events.push(event);
      }
      newlineIndex = this.findNewline();
    }

    return events;
  }

  finish(): RawSseEvent[] {
    if (!this.buffer) {
      return [];
    }
    const event = this.consumeLine(this.buffer);
    this.buffer = "";
    if (event) {
      return [event];
    }
    const flushed = this.flushEvent();
    return flushed ? [flushed] : [];
  }

  private consumeLine(line: string): RawSseEvent | null {
    if (line === "") {
      return this.flushEvent();
    }
    if (line.startsWith(":")) {
      return null;
    }
    const colonIndex = line.indexOf(":");
    const field = colonIndex === -1 ? line : line.slice(0, colonIndex);
    const value = colonIndex === -1 ? "" : line.slice(colonIndex + 1).replace(/^ /, "");

    if (field === "event") {
      this.eventName = value;
    } else if (field === "id") {
      this.eventId = value;
    } else if (field === "data") {
      this.dataLines.push(value);
    }
    return null;
  }

  private flushEvent(): RawSseEvent | null {
    if (this.dataLines.length === 0 && this.eventName === "message" && !this.eventId) {
      this.resetEvent();
      return null;
    }
    const event: RawSseEvent = {
      event: this.eventName,
      data: this.dataLines.join("\n"),
    };
    if (this.eventId) {
      event.id = this.eventId;
    }
    this.resetEvent();
    return event;
  }

  private resetEvent(): void {
    this.eventName = "message";
    this.eventId = undefined;
    this.dataLines = [];
  }

  private findNewline(): { lineEnd: number; nextStart: number } | -1 {
    const lf = this.buffer.indexOf("\n");
    if (lf === -1) {
      return -1;
    }
    const lineEnd = lf > 0 && this.buffer[lf - 1] === "\r" ? lf - 1 : lf;
    return { lineEnd, nextStart: lf + 1 };
  }
}

export function parseStreamEvent(raw: RawSseEvent): StreamEvent {
  if (!isKnownStreamEvent(raw.event)) {
    throw new Error("Unknown stream event.");
  }
  let data: unknown;
  try {
    data = raw.data ? JSON.parse(raw.data) : {};
  } catch {
    throw new Error("Malformed stream event JSON.");
  }
  return { event: raw.event, id: raw.id, data } as StreamEvent;
}

export function isTerminalStreamEvent(event: StreamEvent): boolean {
  return (
    event.event === "message.completed" ||
    event.event === "stream.error" ||
    event.event === "stream.cancelled"
  );
}

export interface ChatStreamRequest {
  sessionId: string;
  content: string;
  signal: AbortSignal;
  onEvent: (event: StreamEvent) => void;
}

export async function streamChatMessage({
  sessionId,
  content,
  signal,
  onEvent,
}: ChatStreamRequest): Promise<void> {
  await ensureFreshAccessToken();
  let response = await fetchStreamResponse({ sessionId, content, signal });
  if (response.status === 401) {
    await response.body?.cancel().catch(() => undefined);
    if (await refreshAccessToken()) {
      response = await fetchStreamResponse({ sessionId, content, signal });
    }
  }

  if (!response.ok) {
    throw await parseApiError(response);
  }
  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  const parser = new SseParser();
  let terminal = false;

  try {
    while (!terminal) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      const rawEvents = parser.feed(decoder.decode(value, { stream: true }));
      for (const rawEvent of rawEvents) {
        if (terminal) {
          continue;
        }
        const event = parseStreamEvent(rawEvent);
        onEvent(event);
        terminal = isTerminalStreamEvent(event);
      }
      if (terminal) {
        await reader.cancel().catch(() => undefined);
      }
    }

    if (!terminal) {
      for (const rawEvent of parser.finish()) {
        const event = parseStreamEvent(rawEvent);
        onEvent(event);
        if (isTerminalStreamEvent(event)) {
          break;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

async function fetchStreamResponse({
  sessionId,
  content,
  signal,
}: Pick<ChatStreamRequest, "sessionId" | "content" | "signal">): Promise<Response> {
  const token = getAccessToken();
  return fetch(
    `${appConfig.apiBaseUrl}${appConfig.apiPrefix}/chat/sessions/${sessionId}/messages/stream`,
    {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
      signal,
    },
  );
}

function isKnownStreamEvent(value: string): value is StreamEventName {
  return (
    value === "stream.started" ||
    value === "heartbeat" ||
    value === "message.delta" ||
    value === "citations.ready" ||
    value === "message.completed" ||
    value === "stream.error" ||
    value === "stream.cancelled"
  );
}
