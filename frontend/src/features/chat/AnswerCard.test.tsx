import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ChatMessage } from "../../api/types";
import { AnswerCard } from "./AnswerCard";

// API_SPEC §8 / BR-3 example of a stored NO_ANSWER message.
const noAnswerMessage: ChatMessage = {
  id: "uuid",
  role: "ASSISTANT",
  content: "Chưa có câu trả lời…",
  response_time_ms: 900,
  citations: [],
  created_at: "2026-11-20T08:00:00Z",
  grounding_status: "NO_ANSWER",
  segments: null,
};

const citation = {
  document_id: "doc-1",
  document_title: "Quy định nghỉ phép",
  chunk_id: "chunk-1",
  page_number: 4,
  excerpt: "Nhân viên được nghỉ 12 ngày phép năm.",
  evidence_text: null,
  relevance_score: 0.9,
  citation_order: 1,
};

// API_SPEC §8 BR-3 follow-up example: content and its segments.
const answeredMessage: ChatMessage = {
  id: "uuid-2",
  role: "ASSISTANT",
  content:
    "Nhân viên được nghỉ 12 ngày phép năm. [1] Chưa xác minh được từ tài liệu bạn được phép truy cập: mức phụ cấp.",
  segments: [
    { kind: "verified", text: "Nhân viên được nghỉ 12 ngày phép năm.", citation_ids: [1] },
    {
      kind: "unverified",
      text: "Chưa xác minh được từ tài liệu bạn được phép truy cập: mức phụ cấp.",
      citation_ids: [],
    },
  ],
  response_time_ms: 900,
  citations: [citation],
  created_at: "2026-11-20T08:00:00Z",
  grounding_status: "ANSWERED",
};

function renderMessage(message: ChatMessage) {
  return render(
    <AnswerCard
      content={message.content}
      citations={message.citations}
      citationMap={new Map([[1, 1]])}
      groundingStatus={message.grounding_status}
      segments={message.segments}
      createdAt={message.created_at}
      onCitationClick={vi.fn()}
      onFeedback={vi.fn()}
    />,
  );
}

describe("AnswerCard", () => {
  it("shows a NO_ANSWER message as a neutral unverified card without citations", () => {
    renderMessage(noAnswerMessage);

    expect(screen.getByText("Chưa xác minh được")).toBeInTheDocument();
    expect(screen.getByText("Chưa có câu trả lời…")).toBeInTheDocument();
    expect(screen.queryByText(/Đã xác minh nguồn/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Mở trích dẫn/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Câu trả lời hữu ích" })).toBeInTheDocument();
  });

  it("renders the server's segments: unverified grey without numbers, verified with its chips", () => {
    renderMessage(answeredMessage);

    expect(screen.getByText(/Đã xác minh nguồn · 1 ý chưa xác minh/)).toBeInTheDocument();
    expect(screen.getByText("1 trích dẫn · chỉ từ tài liệu bạn được phép xem")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mở trích dẫn 1" })).toBeInTheDocument();
    expect(
      screen.getByText("Chưa xác minh được từ tài liệu bạn được phép truy cập: mức phụ cấp."),
    ).toHaveClass("text-muted");
    expect(screen.getByRole("button", { name: /Quy định nghỉ phép/ })).toHaveTextContent("Trang 4");
  });

  it("does not classify sentences by wording when segments are null", () => {
    renderMessage({ ...answeredMessage, segments: null });

    expect(screen.getByText("Đã xác minh nguồn")).toBeInTheDocument();
    expect(screen.queryByText(/ý chưa xác minh/)).not.toBeInTheDocument();
    expect(document.querySelector(".text-muted p, p .text-muted")).toBeNull();
    expect(screen.getByRole("button", { name: "Mở trích dẫn 1" })).toBeInTheDocument();
  });

  it("shows no verification label for an answer stored before grounding_status existed", () => {
    renderMessage({ ...answeredMessage, grounding_status: null, segments: null });

    expect(screen.queryByText(/Đã xác minh nguồn/)).not.toBeInTheDocument();
    expect(screen.queryByText("Chưa xác minh được")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mở trích dẫn 1" })).toBeInTheDocument();
  });
});

describe("AnswerCard BR-12 break_after", () => {
  // The answer text box, with chip buttons dropped so only the rebuilt text is compared.
  function answerText(container: HTMLElement): string {
    const box = container.querySelector("article p")!.cloneNode(true) as HTMLElement;
    box.querySelectorAll("button").forEach((chip) => chip.remove());
    return box.textContent ?? "";
  }

  function renderSegments(segments: NonNullable<ChatMessage["segments"]>) {
    return render(
      <AnswerCard
        content={segments.map((segment) => segment.text).join(" ")}
        citations={[citation, { ...citation, citation_order: 2 }]}
        citationMap={new Map([[1, 1], [2, 2]])}
        groundingStatus="ANSWERED"
        segments={segments}
        onCitationClick={vi.fn()}
      />,
    );
  }

  it("rebuilds a bulleted list and a paragraph break (API_SPEC §8 example)", () => {
    const { container } = renderSegments([
      { kind: "verified", text: "Quy trình gồm:", citation_ids: [], break_after: "line" },
      { kind: "verified", text: "- Bước 1: nộp đơn.", citation_ids: [1], break_after: "line" },
      { kind: "verified", text: "- Bước 2: trưởng phòng duyệt.", citation_ids: [2], break_after: "paragraph" },
      {
        kind: "unverified",
        text: "Chưa xác minh được từ tài liệu bạn được phép truy cập: thời hạn.",
        citation_ids: [],
        break_after: "none",
      },
    ]);

    expect(answerText(container)).toBe(
      "Quy trình gồm:\n- Bước 1: nộp đơn.\n- Bước 2: trưởng phòng duyệt.\n\nChưa xác minh được từ tài liệu bạn được phép truy cập: thời hạn.",
    );
    expect(screen.getAllByRole("button", { name: /Mở trích dẫn/ })).toHaveLength(2);
  });

  it("rebuilds several paragraphs", () => {
    const { container } = renderSegments([
      { kind: "verified", text: "Đoạn một.", citation_ids: [1], break_after: "paragraph" },
      { kind: "verified", text: "Đoạn hai, câu một.", citation_ids: [], break_after: "none" },
      { kind: "verified", text: "Câu hai.", citation_ids: [2], break_after: "none" },
    ]);

    expect(answerText(container)).toBe("Đoạn một.\n\nĐoạn hai, câu một. Câu hai.");
  });

  it("keeps a numbered list as written when '1.' is its own segment with break_after none", () => {
    const { container } = renderSegments([
      { kind: "verified", text: "Các bước:", citation_ids: [], break_after: "line" },
      { kind: "verified", text: "1.", citation_ids: [], break_after: "none" },
      { kind: "verified", text: "Nộp đơn.", citation_ids: [1], break_after: "line" },
      { kind: "verified", text: "2.", citation_ids: [], break_after: "none" },
      { kind: "verified", text: "Trưởng phòng duyệt.", citation_ids: [2] },
    ]);

    expect(answerText(container)).toBe("Các bước:\n1. Nộp đơn.\n2. Trưởng phòng duyệt.");
  });
});
