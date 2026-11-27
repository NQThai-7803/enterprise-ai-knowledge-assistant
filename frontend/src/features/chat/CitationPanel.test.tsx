import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EvidenceSpan } from "../../api/types";
import { CitationPanel } from "./CitationPanel";

function renderExcerpt(excerpt: string, evidenceSpans?: EvidenceSpan[], evidenceText: string | null = null) {
  const { container } = render(
    <CitationPanel
      selectedOrder={1}
      items={[
        {
          document_id: "doc-1",
          document_title: "Nội quy lao động",
          chunk_id: "chunk-1",
          page_number: 5,
          excerpt,
          evidence_text: evidenceText,
          evidence_spans: evidenceSpans,
          relevance_score: 0.9,
          citation_order: 1,
          globalOrder: 1,
          messageId: "m1",
        },
      ]}
    />,
  );
  const paragraph = container.querySelector("article > p:nth-of-type(2)")!;
  return {
    text: paragraph.textContent,
    highlighted: Array.from(paragraph.querySelectorAll(".citation-evidence"), (node) => node.textContent),
  };
}

describe("CitationPanel evidence highlight (evidence_spans, API_SPEC §8A)", () => {
  it("highlights one span", () => {
    const excerpt = "Nhân viên được nghỉ 12 ngày phép năm.";
    const start = excerpt.indexOf("12 ngày");
    expect(renderExcerpt(excerpt, [{ start, end: start + "12 ngày".length }])).toEqual({
      text: excerpt,
      highlighted: ["12 ngày"],
    });
  });

  it("highlights every piece of evidence that skips words of the excerpt (API_SPEC example)", () => {
    const excerpt = "…công nghệ Điều 5. Thời giờ làm việc tiêu chuẩn •Thời gian…";
    const spans = [
      { start: 19, end: 47 },
      { start: 1, end: 10 },
    ];
    expect(renderExcerpt(excerpt, spans)).toEqual({
      text: excerpt,
      highlighted: ["công nghệ", "Thời giờ làm việc tiêu chuẩn"],
    });
  });

  it("shows no highlight for [] even when evidence_text is found in the excerpt", () => {
    const excerpt = "Nhân viên được nghỉ 12 ngày phép năm.";
    expect(renderExcerpt(excerpt, [], "12 ngày")).toEqual({ text: excerpt, highlighted: [] });
  });

  it("leaves the … outside a span that starts or ends next to it", () => {
    const excerpt = "…NHÂN SỰ 02 THỜI GIỜ LÀM VIỆC…";
    const { text, highlighted } = renderExcerpt(excerpt, [{ start: 1, end: excerpt.length - 1 }]);
    expect(text).toBe(excerpt);
    expect(highlighted).toEqual(["NHÂN SỰ 02 THỜI GIỜ LÀM VIỆC"]);
  });

  it("falls back to finding evidence_text when the API sends no evidence_spans", () => {
    const excerpt = "Nhân viên được nghỉ 12 ngày phép năm.";
    expect(renderExcerpt(excerpt, undefined, "12 ngày").highlighted).toEqual(["12 ngày"]);
  });

  it("counts code points, so a character outside the BMP does not shift the span", () => {
    const excerpt = "𝟙 Nhân viên được nghỉ 12 ngày.";
    // "𝟙" is one code point but two JavaScript string indices.
    expect(renderExcerpt(excerpt, [{ start: 22, end: 29 }]).highlighted).toEqual(["12 ngày"]);
  });

  it("never repeats or invents text for overlapping or out-of-range spans", () => {
    const excerpt = "Thời gian làm việc tiêu chuẩn";
    const { text, highlighted } = renderExcerpt(excerpt, [
      { start: 0, end: 9 },
      { start: 5, end: 13 },
      { start: 24, end: 99 },
      { start: 40, end: 50 },
    ]);
    expect(text).toBe(excerpt);
    expect(highlighted).toEqual(["Thời gian", " làm", "chuẩn"]);
  });
});
