import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clsx } from "clsx";
import { ArrowRight, Plus, Square, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "../../api/client";
import { ApiError, safeErrorMessage } from "../../api/errors";
import { streamChatMessage } from "../../api/sse";
import type { ChatSessionSummary, FeedbackRating, ListResponse } from "../../api/types";
import { useToast } from "../../components/feedback/ToastProvider";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { AnswerCard } from "./AnswerCard";
import { CitationPanel, type ConversationCitation } from "./CitationPanel";
import {
  applyChatStreamEvent,
  cancelChatStreamState,
  connectingChatStreamState,
  initialChatStreamState,
} from "./streamState";

const UNTITLED_SESSION = "Cuộc trò chuyện chưa đặt tên";

export function ChatPage() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);
  const [streamState, setStreamState] = useState(initialChatStreamState);
  const abortRef = useRef<AbortController | null>(null);
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const [autoFollowConversation, setAutoFollowConversation] = useState(true);
  const [selectedCitation, setSelectedCitation] = useState<{ sessionId: string | null; order: number } | null>(
    null,
  );
  const [sessionToDelete, setSessionToDelete] = useState<ChatSessionSummary | null>(null);

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
    queryFn: () =>
      apiClient.chat.session(selectedSessionId as string, {
        message_page: 1,
        message_page_size: 100,
      }),
    enabled: Boolean(selectedSessionId),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.code === "CHAT_SESSION_NOT_FOUND") {
        return false;
      }

      return failureCount < 2;
    },
  });

  const createSessionMutation = useMutation({
    mutationFn: (title: string | null) => apiClient.chat.createSession({ title }),
    onSuccess: async (response) => {
      setActiveSessionId(response.data.id);
      await queryClient.invalidateQueries({ queryKey: ["chat", "sessions"] });
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: ({ messageId, rating }: { messageId: string; rating: FeedbackRating }) =>
      apiClient.feedback.upsert(messageId, { rating }),
    onSuccess: () => pushToast({ tone: "success", title: "Đã lưu đánh giá" }),
    onError: (error) => pushToast({ tone: "error", title: "Lưu đánh giá thất bại", message: safeErrorMessage(error) }),
  });

  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => apiClient.chat.deleteSession(sessionId),

    onSuccess: async (_, deletedSessionId) => {
      queryClient.setQueryData<ListResponse<ChatSessionSummary>>(["chat", "sessions"], (current) => {
        if (!current) {
          return current;
        }

        const nextData = current.data.filter((session) => session.id !== deletedSessionId);

        const nextTotal = Math.max(0, current.meta.total - 1);

        return {
          ...current,
          data: nextData,
          meta: {
            ...current.meta,
            total: nextTotal,
            total_pages: nextTotal === 0 ? 0 : Math.ceil(nextTotal / current.meta.page_size),
          },
        };
      });

      queryClient.removeQueries({
        queryKey: ["chat", "session", deletedSessionId],
        exact: true,
      });

      if (selectedSessionId === deletedSessionId) {
        setActiveSessionId(null);
        setPendingUserMessage(null);
        setStreamState(initialChatStreamState);
        setAutoFollowConversation(true);
      }

      setSessionToDelete(null);
      pushToast({
        tone: "success",
        title: "Đã xóa cuộc trò chuyện",
      });

      await queryClient.invalidateQueries({
        queryKey: ["chat", "sessions"],
      });
    },

    onError: (error, deletedSessionId) => {
      setSessionToDelete(null);
      if (error instanceof ApiError && error.code === "CHAT_SESSION_NOT_FOUND") {
        queryClient.setQueryData<ListResponse<ChatSessionSummary>>(["chat", "sessions"], (current) => {
          if (!current) {
            return current;
          }

          const nextData = current.data.filter((session) => session.id !== deletedSessionId);

          const removed = nextData.length !== current.data.length;

          if (!removed) {
            return current;
          }

          const nextTotal = Math.max(0, current.meta.total - 1);

          return {
            ...current,
            data: nextData,
            meta: {
              ...current.meta,
              total: nextTotal,
              total_pages: nextTotal === 0 ? 0 : Math.ceil(nextTotal / current.meta.page_size),
            },
          };
        });

        queryClient.removeQueries({
          queryKey: ["chat", "session", deletedSessionId],
          exact: true,
        });

        if (activeSessionId === deletedSessionId || selectedSessionId === deletedSessionId) {
          setActiveSessionId(null);
          setPendingUserMessage(null);
          setStreamState(initialChatStreamState);
          setAutoFollowConversation(true);
        }

        pushToast({
          tone: "info",
          title: "Cuộc trò chuyện đã được xóa trước đó",
        });

        void queryClient.invalidateQueries({
          queryKey: ["chat", "sessions"],
        });

        return;
      }

      pushToast({
        tone: "error",
        title: "Xóa thất bại",
        message: safeErrorMessage(error),
      });
    },
  });

  const messages = useMemo(() => sessionQuery.data?.data.messages ?? [], [sessionQuery.data]);
  // Global citation numbers restart per conversation, so a selection only counts for its own session.
  const selectedOrder = selectedCitation?.sessionId === selectedSessionId ? selectedCitation.order : null;

  const focusCitation = (globalOrder: number) => {
    setSelectedCitation({ sessionId: selectedSessionId, order: globalOrder });

    window.requestAnimationFrame(() => {
      document.getElementById(`citation-${globalOrder}`)?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        block: "center",
      });
    });
  };

  const citationView = useMemo(() => {
    const items: ConversationCitation[] = [];
    const byMessage = new Map<string, Map<number, number>>();
    const streamMap = new Map<number, number>();

    let nextGlobalOrder = 1;

    for (const message of messages) {
      if (message.role !== "ASSISTANT" || message.citations.length === 0) {
        continue;
      }

      const localMap = new Map<number, number>();

      const orderedCitations = [...message.citations].sort(
        (left, right) => left.citation_order - right.citation_order,
      );

      for (const citation of orderedCitations) {
        const globalOrder = nextGlobalOrder++;

        localMap.set(citation.citation_order, globalOrder);

        items.push({
          ...citation,
          globalOrder,
          messageId: message.id,
        });
      }

      byMessage.set(message.id, localMap);
    }

    const completedMessageId = streamState.completed?.message_id ?? null;

    const streamAlreadyInHistory =
      completedMessageId !== null && messages.some((message) => message.id === completedMessageId);

    if (!streamAlreadyInHistory && streamState.citations.length > 0) {
      const orderedStreamCitations = [...streamState.citations].sort(
        (left, right) => left.citation_order - right.citation_order,
      );

      for (const citation of orderedStreamCitations) {
        const globalOrder = nextGlobalOrder++;

        streamMap.set(citation.citation_order, globalOrder);

        items.push({
          ...citation,
          globalOrder,
          messageId: completedMessageId,
        });
      }
    }

    return {
      items,
      byMessage,
      streamMap,
    };
  }, [messages, streamState.citations, streamState.completed?.message_id]);

  const startNewSession = async () => {
    const response = await createSessionMutation.mutateAsync("Cuộc trò chuyện mới");
    setActiveSessionId(response.data.id);
    setStreamState(initialChatStreamState);
    setPendingUserMessage(null);
    setAutoFollowConversation(true);
  };

  const sendMessage = async () => {
    const content = draft.trim();
    if (
      !content ||
      streamState.status === "connecting" ||
      streamState.status === "started" ||
      streamState.status === "receiving"
    ) {
      return;
    }

    setDraft("");
    setAutoFollowConversation(true);
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
        pushToast({ tone: "info", title: "Đã dừng câu trả lời" });
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

  const streamingActive = ["connecting", "started", "receiving"].includes(streamState.status);
  const sessionNotFound =
    (sessionQuery.error instanceof ApiError && sessionQuery.error.code === "CHAT_SESSION_NOT_FOUND") ||
    streamState.error?.code === "CHAT_SESSION_NOT_FOUND";

  useEffect(() => {
    if (!selectedSessionId || !sessionNotFound) {
      return;
    }

    const staleSessionId = selectedSessionId;

    queryClient.setQueryData<ListResponse<ChatSessionSummary>>(["chat", "sessions"], (current) => {
      if (!current) {
        return current;
      }

      const nextData = current.data.filter((session) => session.id !== staleSessionId);

      if (nextData.length === current.data.length) {
        return current;
      }

      const nextTotal = Math.max(0, current.meta.total - 1);

      return {
        ...current,
        data: nextData,
        meta: {
          ...current.meta,
          total: nextTotal,
          total_pages: nextTotal === 0 ? 0 : Math.ceil(nextTotal / current.meta.page_size),
        },
      };
    });

    queryClient.removeQueries({
      queryKey: ["chat", "session", staleSessionId],
      exact: true,
    });

    setActiveSessionId((current) => (current === staleSessionId ? null : current));

    setPendingUserMessage(null);
    setStreamState(initialChatStreamState);
    setAutoFollowConversation(true);

    void queryClient.invalidateQueries({
      queryKey: ["chat", "sessions"],
    });
  }, [queryClient, selectedSessionId, sessionNotFound]);

  useEffect(() => {
    const container = messagesContainerRef.current;

    if (!container || !autoFollowConversation) {
      return;
    }

    const frameId = window.requestAnimationFrame(() => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "auto",
      });
    });

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, [
    autoFollowConversation,
    messages.length,
    pendingUserMessage,
    selectedSessionId,
    streamState.content,
    streamState.status,
  ]);

  const completed = streamState.completed;
  // buffer_after_validation: the answer only appears once message.completed arrives, in one piece.
  const showStreamAnswer =
    streamState.status === "completed" &&
    completed !== null &&
    !messages.some((message) => message.id === completed.message_id);
  const sessionTitle = selectedSessionId
    ? (sessions.find((session) => session.id === selectedSessionId)?.title ?? UNTITLED_SESSION)
    : "Cuộc trò chuyện mới";

  return (
    <div className="flex flex-col gap-4 xl:-m-10 xl:grid xl:h-[100dvh] xl:grid-cols-[14rem_minmax(0,1fr)_20rem] xl:gap-0">
      <h1 className="sr-only">Trò chuyện</h1>

      <section
        aria-label="Danh sách cuộc trò chuyện"
        className="flex min-h-0 flex-col bg-surface max-xl:rounded-xl max-xl:border max-xl:border-border xl:border-r xl:border-border/70"
      >
        <div className="flex items-center justify-between gap-2 px-4 py-4">
          <h2 className="text-sm font-semibold">Cuộc trò chuyện</h2>
          <button
            type="button"
            className="flex h-8 w-8 items-center justify-center rounded-token border border-border/70 text-ink transition hover:bg-canvas disabled:opacity-50"
            onClick={() => void startNewSession()}
            disabled={createSessionMutation.isPending}
            aria-label="Cuộc trò chuyện mới"
            title="Cuộc trò chuyện mới"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <div className="app-scrollbar min-h-0 flex-1 overflow-y-auto px-2 pb-3 max-xl:max-h-64">
          {sessionsQuery.isLoading ? <LoadingState label="Đang tải danh sách" /> : null}
          {sessionsQuery.isError ? (
            <ErrorState
              title="Không tải được danh sách"
              message={safeErrorMessage(sessionsQuery.error)}
              onRetry={() => void sessionsQuery.refetch()}
            />
          ) : null}
          {!sessionsQuery.isLoading && !sessionsQuery.isError && sessions.length === 0 ? (
            <p className="px-2 py-4 text-[13px] text-muted">Chưa có cuộc trò chuyện nào.</p>
          ) : null}
          {sessions.map((session) => {
            const isSelected = selectedSessionId === session.id;
            const title = session.title ?? UNTITLED_SESSION;
            const deleteDisabled = deleteSessionMutation.isPending || (streamingActive && isSelected);

            return (
              <div
                key={session.id}
                className={clsx(
                  "mb-0.5 flex items-stretch rounded-token text-sm transition",
                  isSelected ? "bg-accent/10" : "hover:bg-canvas",
                )}
              >
                <button
                  type="button"
                  className="min-w-0 flex-1 px-2.5 py-2 text-left"
                  aria-current={isSelected ? "true" : undefined}
                  onClick={() => {
                    setActiveSessionId(session.id);
                    setStreamState(initialChatStreamState);
                    setPendingUserMessage(null);
                    setAutoFollowConversation(true);
                  }}
                >
                  <span
                    className={clsx(
                      "block truncate",
                      isSelected ? "font-medium text-accent-strong" : "text-ink/80",
                    )}
                  >
                    {title}
                  </span>
                  <span className="mt-0.5 block text-xs text-muted">{session.message_count} tin nhắn</span>
                </button>

                <button
                  type="button"
                  className="flex w-9 shrink-0 items-center justify-center rounded-token text-muted transition hover:text-danger disabled:cursor-not-allowed disabled:opacity-40"
                  disabled={deleteDisabled}
                  title={
                    streamingActive && isSelected
                      ? "Dừng câu trả lời đang chạy trước khi xóa cuộc trò chuyện này"
                      : "Xóa cuộc trò chuyện"
                  }
                  aria-label={`Xóa ${title}`}
                  onClick={() => setSessionToDelete(session)}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <section
        aria-label="Cuộc trò chuyện"
        className="flex h-[75dvh] min-h-[32rem] min-w-0 flex-col overflow-hidden bg-canvas max-xl:rounded-xl max-xl:border max-xl:border-border xl:h-auto xl:min-h-0"
      >
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-border/70 bg-surface px-5 py-4 sm:px-7">
          <div className="min-w-0">
            <h2 className="truncate text-[15px] font-semibold">{sessionTitle}</h2>
            <p className="text-xs text-muted">Chỉ trả lời từ tài liệu bạn được phép xem</p>
          </div>
        </header>

        <div
          ref={messagesContainerRef}
          className="app-scrollbar min-h-0 flex-1 overflow-y-auto overscroll-contain"
          aria-live="polite"
          onScroll={(event) => {
            const container = event.currentTarget;
            const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
            setAutoFollowConversation(distanceFromBottom <= 96);
          }}
        >
          <div className="mx-auto flex w-full max-w-[760px] flex-col gap-5 px-5 py-7 sm:px-7">
            {sessionQuery.isLoading && selectedSessionId ? <LoadingState label="Đang tải tin nhắn" /> : null}
            {sessionQuery.isError && selectedSessionId && !sessionNotFound ? (
              <ErrorState
                title="Không tải được cuộc trò chuyện"
                message={safeErrorMessage(sessionQuery.error)}
                onRetry={() => void sessionQuery.refetch()}
              />
            ) : null}
            {!sessionQuery.isLoading && !selectedSessionId && !pendingUserMessage ? (
              <EmptyState
                title="Bắt đầu cuộc trò chuyện"
                description="Đặt câu hỏi về chính sách, quy trình nội bộ trong tài liệu bạn được phép xem."
              />
            ) : null}
            {!sessionQuery.isLoading &&
            selectedSessionId &&
            messages.length === 0 &&
            !pendingUserMessage &&
            streamState.status === "idle" ? (
              <EmptyState title="Chưa có tin nhắn" description="Hỏi về tài liệu bạn được phép xem." />
            ) : null}

            {messages.map((message) =>
              message.role === "USER" ? (
                <UserBubble key={message.id} content={message.content} />
              ) : (
                <AnswerCard
                  key={message.id}
                  content={message.content}
                  citations={message.citations}
                  citationMap={citationView.byMessage.get(message.id)}
                  // TODO(BR-3): history has no grounding_status; NO_ANSWER always comes with no citations.
                  noAnswer={message.citations.length === 0}
                  createdAt={message.created_at}
                  onCitationClick={focusCitation}
                  onFeedback={(rating) => feedbackMutation.mutate({ messageId: message.id, rating })}
                />
              ),
            )}
            {pendingUserMessage ? <UserBubble content={pendingUserMessage} /> : null}
            {streamingActive ? <WaitingLine model={streamState.model} /> : null}
            {showStreamAnswer ? (
              <AnswerCard
                animate
                content={streamState.content}
                citations={streamState.citations}
                citationMap={citationView.streamMap}
                noAnswer={completed.grounding_status === "NO_ANSWER"}
                onCitationClick={focusCitation}
                onFeedback={(rating) => feedbackMutation.mutate({ messageId: completed.message_id, rating })}
              />
            ) : null}
            {streamState.status === "error" && streamState.error && selectedSessionId && !sessionNotFound ? (
              <ErrorState title="Không nhận được câu trả lời" message={streamState.error.message} />
            ) : null}
            {streamState.status === "cancelled" ? (
              <p className="text-center text-xs text-muted">Đã dừng câu trả lời trước khi hoàn tất.</p>
            ) : null}
          </div>
        </div>

        <form
          className="shrink-0 px-5 pb-5 pt-3 sm:px-7"
          onSubmit={(event) => {
            event.preventDefault();
            void sendMessage();
          }}
        >
          <div className="mx-auto flex w-full max-w-[760px] items-end gap-2 rounded-xl border border-border bg-surface p-2 pl-4 transition focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/15">
            <label htmlFor="chat-composer" className="sr-only">
              Câu hỏi
            </label>
            <textarea
              id="chat-composer"
              rows={1}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Hỏi về chính sách, quy trình nội bộ…"
              disabled={streamingActive}
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                  event.preventDefault();
                  void sendMessage();
                }
              }}
              className="max-h-40 min-h-10 flex-1 resize-none self-center bg-transparent py-2 text-sm text-ink outline-none [field-sizing:content] placeholder:text-muted focus-visible:outline-none disabled:opacity-60"
            />
            {streamingActive ? (
              <button
                type="button"
                className="flex h-10 shrink-0 items-center gap-2 rounded-token border border-border px-3 text-sm text-ink transition hover:bg-canvas"
                onClick={abortStream}
              >
                <Square className="h-4 w-4" aria-hidden="true" />
                Dừng
              </button>
            ) : null}
            <button
              type="submit"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-token bg-accent text-accent-contrast transition hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!draft.trim() || streamingActive}
              aria-label="Gửi câu hỏi"
              title="Gửi câu hỏi"
            >
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          <p className="mx-auto mt-2 w-full max-w-[760px] text-xs text-muted">
            Ctrl + Enter để gửi. Câu trả lời chỉ hiện sau khi đã kiểm tra nguồn.
          </p>
        </form>
      </section>

      <CitationPanel items={citationView.items} selectedOrder={selectedOrder} />

      <ConfirmDialog
        open={sessionToDelete !== null}
        title="Xóa cuộc trò chuyện?"
        message={`"${sessionToDelete?.title ?? UNTITLED_SESSION}" và toàn bộ tin nhắn của nó sẽ bị xóa vĩnh viễn.`}
        confirmLabel="Xóa"
        loading={deleteSessionMutation.isPending}
        onCancel={() => setSessionToDelete(null)}
        onConfirm={() => sessionToDelete && deleteSessionMutation.mutate(sessionToDelete.id)}
      />
    </div>
  );
}

function UserBubble({ content }: { content: string }) {
  return (
    <p className="max-w-[80%] self-end whitespace-pre-wrap rounded-[12px_12px_4px_12px] bg-ink px-4 py-3 text-sm leading-6 text-surface">
      {content}
    </p>
  );
}

function WaitingLine({ model }: { model: string | null }) {
  // No staged progress: the SSE stream has no stage events yet (TODO(BR-6)), so one honest status line.
  return (
    <div
      role="status"
      className="fade-up flex max-w-[520px] items-center gap-3 rounded-xl border border-border/70 bg-surface px-4 py-3.5"
    >
      <span
        className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-border border-t-accent"
        aria-hidden="true"
      />
      <div className="flex min-w-0 flex-col">
        <span className="text-sm font-medium">Đang tìm và kiểm tra nguồn…</span>
        {model ? <span className="truncate font-mono text-xs text-muted">Mô hình: {model}</span> : null}
      </div>
    </div>
  );
}
