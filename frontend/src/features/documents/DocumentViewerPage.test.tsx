import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../api/client";
import { ApiError } from "../../api/errors";
import { DocumentViewerPage } from "./DocumentViewerPage";

vi.mock("../../api/client", () => ({
  apiClient: {
    documents: {
      detail: vi.fn(),
      preview: vi.fn(),
    },
  },
}));

function renderViewer(path = "/documents/doc-1/view?page=4") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/documents/:documentId/view" element={<DocumentViewerPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function apiError(status: number, code: string) {
  return new ApiError({ code, message: code, status });
}

describe("DocumentViewerPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.documents.detail).mockRejectedValue(apiError(404, "RESOURCE_NOT_FOUND"));
    URL.createObjectURL = vi.fn(() => "blob:preview");
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a PDF from /preview at the requested page", async () => {
    vi.mocked(apiClient.documents.preview).mockResolvedValue({
      blob: new Blob(["%PDF"], { type: "application/pdf" }),
      filename: "nghi-phep.pdf",
    });

    renderViewer();

    const frame = await screen.findByTitle("Tài liệu, trang 4");
    expect(frame).toHaveAttribute("src", "blob:preview#page=4");
    expect(screen.getByText("Trang 4")).toBeInTheDocument();
    expect(apiClient.documents.preview).toHaveBeenCalledWith("doc-1");
  });

  it("shows an image without a page fragment", async () => {
    vi.mocked(apiClient.documents.preview).mockResolvedValue({
      blob: new Blob(["png"], { type: "image/png" }),
      filename: "scan.png",
    });

    renderViewer();

    expect(await screen.findByRole("img", { name: "Tài liệu" })).toHaveAttribute("src", "blob:preview");
    expect(screen.queryByText("Trang 4")).not.toBeInTheDocument();
  });

  it("explains a 404 without revealing whether the document exists", async () => {
    vi.mocked(apiClient.documents.preview).mockRejectedValue(apiError(404, "RESOURCE_NOT_FOUND"));

    renderViewer();

    expect(
      await screen.findByText("Không tìm thấy tài liệu, hoặc bạn không có quyền xem tài liệu này."),
    ).toBeInTheDocument();
  });

  it("explains a 410 when the stored file is gone", async () => {
    vi.mocked(apiClient.documents.preview).mockRejectedValue(apiError(410, "DOCUMENT_FILE_UNAVAILABLE"));

    renderViewer();

    expect(await screen.findByText("Tệp gốc của tài liệu này không còn trên máy chủ.")).toBeInTheDocument();
  });
});
