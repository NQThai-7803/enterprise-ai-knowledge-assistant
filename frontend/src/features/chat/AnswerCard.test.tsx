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
};

const answeredMessage: ChatMessage = {
  id: "uuid-2",
  role: "ASSISTANT",
  content:
    "Ngân sách tuyển dụng là 1.200.000.000 đồng [1]. Chưa xác minh được từ tài liệu bạn được phép truy cập: ngân sách đào tạo.",
  response_time_ms: 900,
  citations: [
    {
      document_id: "doc-1",
      document_title: "Quy trình tuyển dụng",
      chunk_id: "chunk-1",
      page_number: 4,
      excerpt: "Ngân sách tuyển dụng năm 2026 là 1.200.000.000 đồng.",
      evidence_text: null,
      relevance_score: 0.9,
      citation_order: 1,
    },
  ],
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

  it("shows an ANSWERED message as verified, counts unverified sentences and greys them", () => {
    renderMessage(answeredMessage);

    expect(screen.getByText(/Đã xác minh nguồn · 1 ý chưa xác minh/)).toBeInTheDocument();
    expect(screen.getByText("1 trích dẫn · chỉ từ tài liệu bạn được phép xem")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mở trích dẫn 1" })).toBeInTheDocument();
    expect(
      screen.getByText("Chưa xác minh được từ tài liệu bạn được phép truy cập: ngân sách đào tạo."),
    ).toHaveClass("text-muted");
    expect(screen.getByRole("button", { name: /Quy trình tuyển dụng/ })).toHaveTextContent("Trang 4");
  });

  it("shows no verification label for an answer stored before grounding_status existed", () => {
    renderMessage({ ...answeredMessage, grounding_status: null });

    expect(screen.queryByText(/Đã xác minh nguồn/)).not.toBeInTheDocument();
    expect(screen.queryByText("Chưa xác minh được")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mở trích dẫn 1" })).toBeInTheDocument();
  });
});
