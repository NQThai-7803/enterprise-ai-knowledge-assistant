import type { Citation, MessageCompletedPayload, StreamErrorPayload, StreamEvent } from "../../api/types";

export type ChatStreamStatus =
  | "idle"
  | "connecting"
  | "started"
  | "receiving"
  | "completed"
  | "error"
  | "cancelled";

export interface ChatStreamState {
  status: ChatStreamStatus;
  requestId: string | null;
  provider: string | null;
  model: string | null;
  strategy: "buffer_after_validation" | null;
  content: string;
  citations: Citation[];
  completed: MessageCompletedPayload | null;
  error: StreamErrorPayload | null;
  lastEventId: string | null;
  sequence: number;
  terminal: boolean;
}

export const initialChatStreamState: ChatStreamState = {
  status: "idle",
  requestId: null,
  provider: null,
  model: null,
  strategy: null,
  content: "",
  citations: [],
  completed: null,
  error: null,
  lastEventId: null,
  sequence: 0,
  terminal: false,
};

export function connectingChatStreamState(): ChatStreamState {
  return { ...initialChatStreamState, status: "connecting" };
}

export function applyChatStreamEvent(
  state: ChatStreamState,
  event: StreamEvent,
): ChatStreamState {
  if (state.terminal) {
    return state;
  }

  if (event.event === "stream.started") {
    return {
      ...state,
      status: "started",
      requestId: event.data.request_id,
      provider: event.data.provider ?? null,
      model: event.data.model ?? null,
      strategy: event.data.strategy,
      lastEventId: event.id ?? state.lastEventId,
    };
  }

  if (event.event === "heartbeat") {
    return {
      ...state,
      lastEventId: event.id ?? state.lastEventId,
    };
  }

  if (event.event === "message.delta") {
    if (event.data.sequence <= state.sequence) {
      return {
        ...state,
        lastEventId: event.id ?? state.lastEventId,
      };
    }
    return {
      ...state,
      status: "receiving",
      sequence: event.data.sequence,
      content: state.content + event.data.content,
      lastEventId: event.id ?? state.lastEventId,
    };
  }

  if (event.event === "citations.ready") {
    return {
      ...state,
      citations: event.data.citations,
      lastEventId: event.id ?? state.lastEventId,
    };
  }

  if (event.event === "message.completed") {
    return {
      ...state,
      status: "completed",
      content: event.data.content,
      citations: event.data.citations,
      completed: event.data,
      lastEventId: event.id ?? state.lastEventId,
      terminal: true,
    };
  }

  if (event.event === "stream.error") {
    return {
      ...state,
      status: "error",
      error: event.data,
      lastEventId: event.id ?? state.lastEventId,
      terminal: true,
    };
  }

  return {
    ...state,
    status: "cancelled",
    error: event.data,
    lastEventId: event.id ?? state.lastEventId,
    terminal: true,
  };
}

export function cancelChatStreamState(state: ChatStreamState): ChatStreamState {
  if (state.terminal) {
    return state;
  }
  return {
    ...state,
    status: "cancelled",
    error: {
      code: "STREAM_CANCELLED",
      message: "The stream was cancelled.",
      retryable: true,
    },
    terminal: true,
  };
}
