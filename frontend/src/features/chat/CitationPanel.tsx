import { clsx } from "clsx";
import { ExternalLink } from "lucide-react";
import type { ReactNode } from "react";
import type { Citation, EvidenceSpan } from "../../api/types";

export type ConversationCitation = Citation & {
  globalOrder: number;
  messageId: string | null;
};

export function CitationPanel({
  items,
  selectedOrder,
}: {
  items: ConversationCitation[];
  selectedOrder: number | null;
}) {
  return (
    <aside
      aria-label="Trích dẫn"
      className="app-scrollbar flex min-h-0 flex-col gap-3.5 overflow-y-auto border-border bg-surface p-5 max-xl:rounded-xl max-xl:border xl:border-l"
    >
      <h2 className="text-sm font-semibold">Trích dẫn</h2>
      {items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border px-4 py-6 text-center text-[13px] text-muted">
          Trích dẫn của câu trả lời sẽ hiện ở đây, kèm đoạn văn gốc.
        </p>
      ) : (
        <p className="text-[13px] text-muted">Bấm vào số trích dẫn trong câu trả lời để xem đoạn văn gốc.</p>
      )}
      {items.map((citation) => {
        const selected = selectedOrder === citation.globalOrder;
        return (
          <article
            id={`citation-${citation.globalOrder}`}
            key={`${citation.messageId ?? "stream"}-${citation.globalOrder}`}
            className={clsx(
              "flex flex-col gap-2.5 rounded-xl border p-4",
              selected ? "slide-in border-accent ring-2 ring-accent/15" : "border-border/70",
            )}
          >
            <p className="font-mono text-xs text-muted">
              [{citation.globalOrder}] · Trang {citation.page_number}
            </p>
            <h3 className="text-sm font-semibold leading-snug text-ink">{citation.document_title}</h3>
            <p className={clsx("text-[13px] leading-relaxed text-ink/80", !selected && "line-clamp-5")}>
              <CitationEvidenceText
                excerpt={citation.excerpt}
                evidenceText={citation.evidence_text}
                evidenceSpans={citation.evidence_spans}
              />
            </p>
            <a
              href={`/documents/${encodeURIComponent(citation.document_id)}/view?page=${citation.page_number}`}
              target="_blank"
              // The viewer reads the access token from sessionStorage; only an opener-linked tab gets a copy.
              rel="opener"
              className="inline-flex items-center gap-1.5 self-start text-[13px] font-medium text-accent transition hover:text-accent-strong"
            >
              Mở tài liệu tại trang {citation.page_number}
              <ExternalLink className="h-3.5 w-3.5" aria-hidden={true} />
              <span className="sr-only">(mở trong tab mới)</span>
            </a>
          </article>
        );
      })}
    </aside>
  );
}

function CitationEvidenceText({
  excerpt,
  evidenceText,
  evidenceSpans,
}: {
  excerpt: string;
  evidenceText?: string | null;
  evidenceSpans?: EvidenceSpan[];
}) {
  if (evidenceSpans) {
    return highlightSpans(excerpt, evidenceSpans);
  }
  // An API without evidence_spans (before BR-15): look for evidence_text in the excerpt.
  const evidence = evidenceText?.trim();
  if (!evidence) {
    return <>{excerpt}</>;
  }

  const exactIndex = excerpt.indexOf(evidence);
  if (exactIndex >= 0) {
    return highlight(excerpt, exactIndex, exactIndex + evidence.length);
  }

  // The evidence can be right while the excerpt normalised whitespace differently ("8 giờ / ngày").
  const escapedParts = evidence
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (escapedParts.length === 0) {
    return <>{excerpt}</>;
  }
  const match = new RegExp(escapedParts.join("\\s+"), "iu").exec(excerpt);
  if (!match) {
    // No real match: never highlight an approximate span.
    return <>{excerpt}</>;
  }
  return highlight(excerpt, match.index, match.index + match[0].length);
}

// Spans count code points (API_SPEC §8A): Array.from keeps them aligned past characters outside the BMP.
function highlightSpans(excerpt: string, spans: EvidenceSpan[]) {
  const characters = Array.from(excerpt);
  const parts: ReactNode[] = [];
  let cursor = 0;
  for (const { start, end } of [...spans].sort((a, b) => a.start - b.start)) {
    const from = Math.max(start, cursor);
    const to = Math.min(end, characters.length);
    if (from >= to) continue; // an empty, overlapping or out-of-range span never repeats or invents text
    parts.push(
      characters.slice(cursor, from).join(""),
      <span key={from} className="citation-evidence">
        {characters.slice(from, to).join("")}
      </span>,
    );
    cursor = to;
  }
  parts.push(characters.slice(cursor).join(""));
  return <>{parts}</>;
}

function highlight(excerpt: string, start: number, end: number) {
  return (
    <>
      {excerpt.slice(0, start)}
      <span className="citation-evidence">{excerpt.slice(start, end)}</span>
      {excerpt.slice(end)}
    </>
  );
}
