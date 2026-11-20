import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../api/client";
import { ToastProvider } from "../../components/feedback/ToastProvider";
import { contractDocument, contractManager } from "../../test/fixtures/contract";
import { DocumentDetailPage } from "./DocumentDetailPage";

vi.mock("../../api/client", () => ({
  apiClient: { documents: { detail: vi.fn(), status: vi.fn(), download: vi.fn(), delete: vi.fn() } },
}));
vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ user: contractManager }) }));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={["/documents/uuid"]}>
          <Routes>
            <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("DocumentDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("crypto", { randomUUID: () => "toast-id" });
    vi.mocked(apiClient.documents.detail).mockResolvedValue({ data: contractDocument, meta: null });
    vi.mocked(apiClient.documents.status).mockResolvedValue({
      data: { id: "uuid", status: "PROCESSING", error_message: null, updated_at: "2026-11-20T08:00:00Z" },
      meta: null,
    });
  });

  it("shows the BR-1 version fields and a status-derived timeline", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { level: 1, name: "Quy định nghỉ phép" })).toBeInTheDocument();
    expect(screen.getAllByText("ND-HR-007")).toHaveLength(2);
    expect(screen.getByText("1.0")).toBeInTheDocument();
    expect(screen.getByText("01/09/2026 – nay")).toBeInTheDocument();
    expect(screen.getByText("Đang hiệu lực")).toBeInTheDocument();
    expect(screen.getByText("178.1 KB")).toBeInTheDocument();
    expect(screen.getAllByText("Nhân sự")).not.toHaveLength(0);
    expect(await screen.findByRole("img", { name: "Đang chạy" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Phân quyền" })).not.toBeInTheDocument();
  });

  it("asks before deleting, in the artboard's words", async () => {
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Xóa" }));
    expect(screen.getByRole("dialog", { name: "Xóa tài liệu này?" })).toBeInTheDocument();
  });
});
