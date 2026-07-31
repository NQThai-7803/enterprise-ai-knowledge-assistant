import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Plus, Send, Square, ThumbsDown, ThumbsUp, UserRound } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "../../api/client";
import { ApiError, safeErrorMessage } from "../../api/errors";
import { streamChatMessage } from "../../api/sse";
import type { ChatMessage, Citation } from "../../api/types";
import { useToast } from "../../components/feedback/ToastProvider";
import { PageHeader } from "../../components/layout/PageHeader";
import { ShimmerText } from "../../components/motion/ShimmerText";
import { SpotlightPanel } from "../../components/motion/SpotlightPanel";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { TextArea } from "../../components/ui/Field";
import { Panel } from "../../components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatDateTime } from "../../lib/format";
import {
  applyChatStreamEvent,
  cancelChatStreamState,
  connectingChatStreamState,
  initialChatStreamState,
} from "./streamState";

export function ChatPage() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);
  const [streamState, setStreamState] = useState(initialChatStreamState);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const sessionsQuery = useQuery({
    queryKey: ["chat", "sessions"],
    queryFn: () => apiClient.chat.listSessions({ page: 1, page_size: 50 }),
  });

  const sessions = sessionsQuery.data?.data ?? [];
  const selectedSessionId = activeSessionId ?? sessions[0]?.id ?? null;

  const sessionQuery = useQuery({
    queryKey: ["chat", "session", selectedSessionId],
    queryFn: () => apiClient.chat.session(selectedSessionId as string, { message_page: 1, message_page_size: 100 }),
    enabled: Boolean(selectedSessionId),
  });

  const createSessionMutation = useMutation({
    mutationFn: (title: string | null) => apiClient.chat.createSession({ title }),
    onSuccess: async (response) => {
      setActiveSessionId(response.data.id);
      await queryClient.invalidateQueries({ queryKey: ["chat", "sessions"] });
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: ({ messageId, rating }: { messageId: string; rating: "HELPFUL" | "NOT_HELPFUL" }) =>
      apiClient.feedback.upsert(messageId, { rating }),
    onSuccess: () => pushToast({ tone: "success", title: "Feedback saved" }),
    onError: (error) => pushToast({ tone: "error", title: "Feedback failed", message: safeErrorMessage(error) }),
  });

  const activeCitations = useMemo<Citation[]>(() => {
    if (streamState.completed?.citations.length) {
      return streamState.completed.citations;
    }
    const messages = sessionQuery.data?.data.messages ?? [];
    return [...messages].reverse().find((message) => message.role === "ASSISTANT" && message.citations.length > 0)?.citations ?? [];
  }, [sessionQuery.data?.data.messages, streamState.completed?.citations]);

  const startNewSession = async () => {
    const response = await createSessionMutation.mutateAsync("New chat");
    setActiveSessionId(response.data.id);
    setStreamState(initialChatStreamState);
    setPendingUserMessage(null);
  };

  const sendMessage = async () => {
    const content = draft.trim();
    if (!content || streamState.status === "connecting" || streamState.status === "started" || streamState.status === "receiving") {
      return;
    }

    setDraft("");
    setPendingUserMessage(content);
    setStreamState(connectingChatStreamState());

    try {
      let sessionId = selectedSessionId;
      if (!sessionId) {
        const created = await createSessionMutation.mutateAsync(content.slice(0, 80));
        sessionId = created.data.id;
        setActiveSessionId(sessionId);
      }

      const controller = new AbortController();
      abortRef.current = controller;
      await streamChatMessage({
        sessionId,
        content,
        signal: controller.signal,
        onEvent: (event) => setStreamState((current) => applyChatStreamEvent(current, event)),
      });
      await queryClient.invalidateQueries({ queryKey: ["chat"] });
      setPendingUserMessage(null);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setStreamState((current) => cancelChatStreamState(current));
        pushToast({ tone: "info", title: "Stream cancelled" });
      } else if (error instanceof ApiError) {
        setStreamState((current) => ({
          ...current,
          status: "error",
          error: { code: error.code, message: error.message, retryable: error.retryable },
          terminal: true,
        }));
      } else {
        setStreamState((current) => ({
          ...current,
          status: "error",
          error: { code: "STREAM_INTERNAL_ERROR", message: safeErrorMessage(error), retryable: false },
          terminal: true,
        }));
      }
    } finally {
      abortRef.current = null;
    }
  };

  const abortStream = () => {
    abortRef.current?.abort();
    setStreamState((current) => cancelChatStreamState(current));
  };

  const messages = sessionQuery.data?.data.messages ?? [];
  const streamingActive = ["connecting", "started", "receiving"].includes(streamState.status);

  return (
    <div>
      <PageHeader
        title="AI Chat workspace"
        description="Grounded answers use selected document context and validated citations before content is shown."
        actions={
          <Button type="button" variant="secondary" onClick={startNewSession} loading={createSessionMutation.isPending} icon={<Plus className="h-4 w-4" aria-hidden="true" />}>
            New session
          </Button>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[18rem_minmax(0,1fr)_22rem]">
        <Panel className="min-h-[28rem] overflow-hidden">
          <div className="border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold">Sessions</h3>
          </div>
          <div className="app-scrollbar max-h-[calc(100dvh-13rem)] overflow-y-auto p-2">
            {sessionsQuery.isLoading ? <LoadingState label="Loading sessions" /> : null}
            {sessionsQuery.isError ? <ErrorState message={safeErrorMessage(sessionsQuery.error)} onRetry={() => void sessionsQuery.refetch()} /> : null}
            {!sessionsQuery.isLoading && sessions.length === 0 ? <EmptyState title="No chat sessions" /> : null}
            {sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={`mb-2 w-full rounded-token border px-3 py-2 text-left text-sm transition ${selectedSessionId === session.id ? "border-accent bg-accent/10" : "border-border bg-surface hover:bg-elevated"}`}
                onClick={() => {
                  setActiveSessionId(session.id);
                  setStreamState(initialChatStreamState);
                  setPendingUserMessage(null);
                }}
              >
                <span className="block truncate font-semibold text-ink">{session.title ?? "Untitled chat"}</span>
                <span className="mt-1 block text-xs text-muted">{session.message_count} messages</span>
              </button>
            ))}
          </div>
        </Panel>

        <SpotlightPanel className="min-h-[34rem] border border-border bg-surface shadow-sm">
          <div className="flex min-h-[34rem] flex-col">
            <div className="border-b border-border px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-semibold">Conversation</h3>
                  <p className="text-xs text-muted">SSE strategy: buffer_after_validation</p>
                </div>
                {streamingActive ? <Badge tone="warning">Checking sources</Badge> : null}
              </div>
            </div>

            <div className="app-scrollbar flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
              {sessionQuery.isLoading && selectedSessionId ? <LoadingState label="Loading messages" /> : null}
              {sessionQuery.isError ? <ErrorState message={safeErrorMessage(sessionQuery.error)} onRetry={() => void sessionQuery.refetch()} /> : null}
              {!sessionQuery.isLoading && !selectedSessionId ? <EmptyState title="Start a chat session" description="Create a session or send a question to begin." /> : null}
              {!sessionQuery.isLoading && selectedSessionId && messages.length === 0 && !pendingUserMessage && streamState.status === "idle" ? (
                <EmptyState title="No messages yet" description="Ask a question about documents you can access." />
              ) : null}

              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} onFeedback={(rating) => feedbackMutation.mutate({ messageId: message.id, rating })} />
              ))}
              {pendingUserMessage ? <UserBubble content={pendingUserMessage} /> : null}
              {streamingActive ? <AssistantWaiting status={streamState.status} /> : null}
              {streamState.content && (streamingActive || !messages.some((message) => message.id === streamState.completed?.message_id)) ? (
                <AssistantStreamBubble
                  content={streamState.content}
                  citations={streamState.citations}
                  completedMessageId={streamState.completed?.message_id ?? null}
                  onFeedback={(rating) => {
                    const messageId = streamState.completed?.message_id;
                    if (messageId) {
                      feedbackMutation.mutate({ messageId, rating });
                    }
                  }}
                />
              ) : null}
              {streamState.status === "error" && streamState.error ? <ErrorState title={streamState.error.code} message={streamState.error.message} /> : null}
              {streamState.status === "cancelled" ? <ErrorState title="STREAM_CANCELLED" message="The active request was cancelled before completion." /> : null}
            </div>

            <div className="border-t border-border p-4">
              <label htmlFor="chat-composer" className="sr-only">Message</label>
              <TextArea
                id="chat-composer"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Ask a grounded question"
                disabled={streamingActive}
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                    void sendMessage();
                  }
                }}
              />
              <div className="mt-3 flex flex-wrap justify-between gap-2">
                <p className="text-xs text-muted">Validated answer content appears after grounding and citation checks.</p>
                <div className="flex gap-2">
                  {streamingActive ? (
                    <Button type="button" variant="secondary" onClick={abortStream} icon={<Square className="h-4 w-4" aria-hidden="true" />}>
                      Stop
                    </Button>
                  ) : null}
                  <Button type="button" onClick={sendMessage} disabled={!draft.trim() || streamingActive} icon={<Send className="h-4 w-4" aria-hidden="true" />}>
                    Send
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </SpotlightPanel>

        <Panel className="min-h-[28rem] overflow-hidden">
          <div className="border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold">Citations</h3>
          </div>
          <div className="app-scrollbar max-h-[calc(100dvh-13rem)] space-y-3 overflow-y-auto p-4">
            {activeCitations.length === 0 ? <EmptyState title="No citations" description="Citations appear when the validated answer includes sources." /> : null}
            {activeCitations.map((citation) => (
              <article key={`${citation.document_id}-${citation.citation_order}`} className="rounded-token border border-border bg-elevated p-3 text-sm">
                <div className="flex items-start justify-between gap-3">
                  <h4 className="font-semibold text-ink">[{citation.citation_order}] {citation.document_title}</h4>
                  <Badge tone="accent">Page {citation.page_number}</Badge>
                </div>
                <p className="mt-2 line-clamp-5 text-muted">{citation.excerpt}</p>
              </article>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function MessageBubble({ message, onFeedback }: { message: ChatMessage; onFeedback: (rating: "HELPFUL" | "NOT_HELPFUL") => void }) {
  if (message.role === "USER") {
    return <UserBubble content={message.content} timestamp={message.created_at} />;
  }
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-token bg-accent/10 text-accent">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </div>
      <article className="min-w-0 flex-1 rounded-token border border-border bg-elevated p-3">
        <p className="whitespace-pre-wrap text-sm leading-6 text-ink">{message.content}</p>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
          <span>{formatDateTime(message.created_at)}</span>
          <div className="flex gap-1">
            <button className="rounded-token p-1 hover:bg-surface" type="button" onClick={() => onFeedback("HELPFUL")} aria-label="Mark answer helpful">
              <ThumbsUp className="h-4 w-4" aria-hidden="true" />
            </button>
            <button className="rounded-token p-1 hover:bg-surface" type="button" onClick={() => onFeedback("NOT_HELPFUL")} aria-label="Mark answer not helpful">
              <ThumbsDown className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </article>
    </div>
  );
}

function UserBubble({ content, timestamp }: { content: string; timestamp?: string }) {
  return (
    <div className="flex justify-end gap-3">
      <article className="max-w-[min(42rem,85%)] rounded-token bg-accent px-3 py-2 text-sm leading-6 text-accent-contrast">
        <p className="whitespace-pre-wrap">{content}</p>
        {timestamp ? <p className="mt-2 text-xs opacity-80">{formatDateTime(timestamp)}</p> : null}
      </article>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-token bg-elevated text-muted">
        <UserRound className="h-4 w-4" aria-hidden="true" />
      </div>
    </div>
  );
}

function AssistantWaiting({ status }: { status: string }) {
  const label = status === "connecting" ? "Finding relevant documents" : "Generating and validating citations";
  return (
    <div className="flex gap-3" role="status">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-token bg-accent/10 text-accent">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </div>
      <div className="rounded-token border border-border bg-elevated px-3 py-2 text-sm text-muted">
        <ShimmerText>{label}</ShimmerText>
      </div>
    </div>
  );
}

function AssistantStreamBubble({ content, citations, completedMessageId, onFeedback }: { content: string; citations: Citation[]; completedMessageId: string | null; onFeedback: (rating: "HELPFUL" | "NOT_HELPFUL") => void }) {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-token bg-accent/10 text-accent">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </div>
      <article className="min-w-0 flex-1 rounded-token border border-accent/25 bg-accent/5 p-3">
        <p className="whitespace-pre-wrap text-sm leading-6 text-ink">{content}</p>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
          {citations.length ? <span>{citations.length} validated citations</span> : <span>Completed</span>}
          {completedMessageId ? (
            <div className="flex gap-1">
              <button className="rounded-token p-1 hover:bg-surface" type="button" onClick={() => onFeedback("HELPFUL")} aria-label="Mark answer helpful">
                <ThumbsUp className="h-4 w-4" aria-hidden="true" />
              </button>
              <button className="rounded-token p-1 hover:bg-surface" type="button" onClick={() => onFeedback("NOT_HELPFUL")} aria-label="Mark answer not helpful">
                <ThumbsDown className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          ) : null}
        </div>
      </article>
    </div>
  );
}