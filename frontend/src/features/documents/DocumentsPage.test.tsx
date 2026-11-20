import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../api/client";
import type { AuthenticatedUser } from "../../api/types";
import { DocumentStatusBadge } from "../../components/ui/StatusBadge";
import { contractDocument, contractManager } from "../../test/fixtures/contract";
import { DocumentsPage } from "./DocumentsPage";

let currentUser: AuthenticatedUser = contractManager;

vi.mock("../../api/client", () => ({ apiClient: { documents: { list: vi.fn() } } }));
vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ user: currentUser }) }));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DocumentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentUser = contractManager;
    vi.mocked(apiClient.documents.list).mockResolvedValue({
      data: [contractDocument, { ...contractDocument, id: "uuid-2", document_code: null, lifecycle_status: "DRAFT" }],
      meta: { page: 1, page_size: 20, total: 2, total_pages: 1 },
    });
  });

  it("shows BR-1 version fields, Vietnamese labels and the viewer's own department name", async () => {
    renderPage();

    expect(await screen.findByText("ND-HR-007 · v1.0 · 178.1 KB")).toBeInTheDocument();
    expect(screen.getByText("nghi-phep.pdf · v1.0 · 178.1 KB")).toBeInTheDocument();
    expect(screen.getByText("Bản nháp")).toBeInTheDocument();
    expect(screen.getAllByText("Nhân sự")).toHaveLength(2);
    expect(within(screen.getByRole("table")).getAllByText("Đã tải lên")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Tải tài liệu lên" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Phân quyền" })).not.toBeInTheDocument();
  });

  it("names no department the viewer does not belong to", async () => {
    currentUser = { ...contractManager, department_id: "other", department_name: "Kế toán" };
    renderPage();

    expect(await screen.findAllByText("Phòng ban")).not.toHaveLength(0);
    expect(screen.queryByText("Kế toán")).not.toBeInTheDocument();
  });
});

describe("DocumentStatusBadge", () => {
  it("animates only when the status changes on screen", () => {
    const { rerender } = render(<DocumentStatusBadge status="PROCESSING" />);
    expect(screen.getByText("Đang xử lý")).not.toHaveClass("pop");

    rerender(<DocumentStatusBadge status="READY" />);
    expect(screen.getByText("Sẵn sàng")).toHaveClass("pop");
  });
});
