import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/errors";
import { EmptyState, ErrorState, LoadingState } from "./State";

describe("state components", () => {
  it("renders accessible loading status", () => {
    render(<LoadingState label="Loading documents" />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading documents");
  });

  it("renders empty state action without requiring mock data", () => {
    render(<EmptyState title="No documents" action={<button type="button">Upload</button>} />);

    expect(screen.getByText("No documents")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload" })).toBeInTheDocument();
  });

  it("supports retry from an error state", async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Too many requests" onRetry={onRetry} />);

    await userEvent.click(screen.getByRole("button", { name: "Thử lại" }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("shows the real request_id of an API error, and none without one", () => {
    const { rerender } = render(
      <ErrorState error={new ApiError({ code: "INTERNAL", message: "Lỗi máy chủ", status: 500, requestId: "req-42" })} />,
    );

    expect(screen.getByText("Không tải được dữ liệu")).toBeInTheDocument();
    expect(screen.getByText("Lỗi máy chủ")).toBeInTheDocument();
    expect(screen.getByText("request_id: req-42")).toBeInTheDocument();

    rerender(<ErrorState error={new Error("network")} />);
    expect(screen.queryByText(/request_id/)).not.toBeInTheDocument();
  });
});
