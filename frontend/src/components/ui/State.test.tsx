import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
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

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
