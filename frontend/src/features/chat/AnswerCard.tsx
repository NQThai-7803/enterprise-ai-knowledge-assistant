import { clsx } from "clsx";
import { Check, FileText, Info, ThumbsDown, ThumbsUp } from "lucide-react";
import { Fragment, type ReactNode } from "react";
import type { Citation, FeedbackRating } from "../../api/types";
import { formatDateTime } from "../../lib/format";
import { splitAnswerSegments } from "./answerSegments";

export function AnswerCard({
  content,
  citations,
  citationMap,
  noAnswer,
  createdAt,
  animate = false,
  onCitationClick,
  onFeedback,
}: {
  content: string;
  citations: Citation[];
  citationMap?: ReadonlyMap<number, number>;
  noAnswer: boolean;
  createdAt?: string;
  animate?: boolean;
  onCitationClick: (globalOrder: number) => void;
  onFeedback?: (rating: FeedbackRating) => void;
}) {
  if (noAnswer) {
    // Neutral, not an error: the backend found nothing it could verify and says so in its own words.
    return (
      <article
        className={clsx(
          "flex flex-col gap-3.5 rounded-xl border border-dashed border-border bg-elevated px-5 py-4",
          animate && "fade-up",
        )}
      >
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-border/50 px-2.5 py-0.5 font-medium text-ink/80">
            <Info className="h-3.5 w-3.5" aria-hidden={true} />
            Chưa xác minh được
          </span>
          <span className="text-muted">Không có trích dẫn · chỉ tìm trong tài liệu bạn được phép xem</span>
        </div>
        <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-ink/80">{content}</p>
        <AnswerFooter createdAt={createdAt} onFeedback={onFeedback} />
      </article>
    );
  }

  const segments = splitAnswerSegments(content);
  const unverifiedCount = segments.filter((segment) => segment.unverified).length;
  const sources = sourceButtons(citations, citationMap);

  return (
    <article
      className={clsx(
        "flex flex-col gap-3.5 rounded-xl border border-border/70 bg-surface px-5 py-5",
        animate && "fade-up",
      )}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-2.5 py-0.5 font-medium text-success">
          <Check className="h-3.5 w-3.5" aria-hidden={true} />
          Đã xác minh nguồn
          {unverifiedCount > 0 ? ` · ${unverifiedCount} ý chưa xác minh` : null}
        </span>
        <span className="text-muted">{citations.length} trích dẫn · chỉ từ tài liệu bạn được phép xem</span>
      </div>
      <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-ink">
        {segments.map((segment, index) =>
          segment.unverified ? (
            <span key={index} className="text-muted">
              {segment.text}
            </span>
          ) : (
            <Fragment key={index}>{withCitationChips(segment.text, citationMap, onCitationClick)}</Fragment>
          ),
        )}
      </p>
      <AnswerFooter createdAt={createdAt} onFeedback={onFeedback}>
        {sources.map((source) => (
          <button
            key={source.key}
            type="button"
            className="inline-flex min-h-9 max-w-full items-center gap-2 rounded-token border border-border/70 bg-surface px-3 text-[13px] transition hover:bg-canvas"
            onClick={() => onCitationClick(source.globalOrder)}
          >
            <FileText className="h-4 w-4 shrink-0 text-muted" aria-hidden={true} />
            <span className="truncate">{source.title}</span>
            <span className="shrink-0 text-muted">· Trang {source.page}</span>
          </button>
        ))}
      </AnswerFooter>
    </article>
  );
}

function AnswerFooter({
  createdAt,
  onFeedback,
  children,
}: {
  createdAt?: string;
  onFeedback?: (rating: FeedbackRating) => void;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/50 pt-3">
      <div className="flex min-w-0 flex-wrap gap-2">{children}</div>
      <div className="flex items-center gap-1.5">
        {createdAt ? <span className="mr-1 text-xs text-muted">{formatDateTime(createdAt)}</span> : null}
        {onFeedback ? (
          <>
            <FeedbackButton label="Câu trả lời hữu ích" onClick={() => onFeedback("HELPFUL")}>
              <ThumbsUp className="h-4 w-4" aria-hidden={true} />
            </FeedbackButton>
            <FeedbackButton label="Câu trả lời chưa hữu ích" onClick={() => onFeedback("NOT_HELPFUL")}>
              <ThumbsDown className="h-4 w-4" aria-hidden={true} />
            </FeedbackButton>
          </>
        ) : null}
      </div>
    </div>
  );
}

function FeedbackButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      className="flex h-9 w-9 items-center justify-center rounded-token border border-border/70 bg-surface text-muted transition hover:bg-canvas hover:text-ink"
      onClick={onClick}
      aria-label={label}
      title={label}
    >
      {children}
    </button>
  );
}

function withCitationChips(
  text: string,
  citationMap: ReadonlyMap<number, number> | undefined,
  onCitationClick: (globalOrder: number) => void,
): ReactNode[] {
  const parts: ReactNode[] = [];
  const citationPattern = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = citationPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const globalOrder = citationMap?.get(Number(match[1]));
    if (globalOrder !== undefined) {
      parts.push(
        <button
          key={`${match.index}-${globalOrder}`}
          type="button"
          className="citation-chip"
          onClick={() => onCitationClick(globalOrder)}
          aria-label={`Mở trích dẫn ${globalOrder}`}
          title={`Mở trích dẫn ${globalOrder}`}
        >
          {globalOrder}
        </button>,
      );
    } else {
      parts.push(match[0]);
    }
    lastIndex = citationPattern.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
}

function sourceButtons(citations: Citation[], citationMap: ReadonlyMap<number, number> | undefined) {
  const seen = new Set<string>();
  const sources: { key: string; title: string; page: number; globalOrder: number }[] = [];
  for (const citation of [...citations].sort((left, right) => left.citation_order - right.citation_order)) {
    const globalOrder = citationMap?.get(citation.citation_order);
    const key = `${citation.document_id}:${citation.page_number}`;
    if (globalOrder === undefined || seen.has(key)) {
      continue;
    }
    seen.add(key);
    sources.push({ key, title: citation.document_title, page: citation.page_number, globalOrder });
  }
  return sources;
}
