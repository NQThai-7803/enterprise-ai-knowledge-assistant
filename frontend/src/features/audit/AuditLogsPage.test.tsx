import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../api/client";
import { ApiError } from "../../api/errors";
import { AuditLogsPage } from "./AuditLogsPage";

vi.mock("../../api/client", () => ({ apiClient: { audit: { list: vi.fn() } } }));

const emptyPage = { items: [], page: 1, page_size: 25, total: 0, total_pages: 0 };

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuditLogsPage />
    </QueryClientProvider>,
  );
}

describe("AuditLogsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.audit.list).mockResolvedValue(emptyPage);
  });

  it("offers the 23 BR-9 event types and sends the contract example filter", async () => {
    const user = userEvent.setup();
    renderPage();

    const select = screen.getByLabelText("Loại sự kiện");
    expect(within(select).getAllByRole("option")).toHaveLength(24);
    expect(within(select).getByRole("option", { name: "USER_DEACTIVATED (không còn ghi)" })).toBeInTheDocument();

    await user.selectOptions(select, "CHAT_NO_ANSWER_GENERATED");
    await user.selectOptions(screen.getByLabelText("Kết quả"), "SUCCESS");

    await waitFor(() =>
      expect(apiClient.audit.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ event_type: "CHAT_NO_ANSWER_GENERATED", outcome: "SUCCESS" }),
      ),
    );
  });

  it("explains 422 AUDIT_FILTER_INVALID and lets the user clear the filters", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.audit.list).mockImplementation(async (query) => {
      if (query.request_id) {
        throw new ApiError({ code: "AUDIT_FILTER_INVALID", message: "Invalid audit filter.", status: 422 });
      }
      return emptyPage;
    });
    renderPage();

    await user.type(screen.getByLabelText("Request ID"), "not-a-request-id");
    expect(await screen.findByText("Bộ lọc không hợp lệ")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Xóa bộ lọc" }));
    expect(await screen.findByText("Không có bản ghi phù hợp")).toBeInTheDocument();
  });

  it("shows a row's safe details on demand, never an IP address", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.audit.list).mockResolvedValue({
      ...emptyPage,
      total: 1,
      total_pages: 1,
      items: [
        {
          id: "audit-1",
          event_type: "DOCUMENT_PERMISSION_GRANTED",
          outcome: "SUCCESS",
          actor_user_id: null,
          target_type: "DOCUMENT_PERMISSION",
          target_id: "perm-1",
          request_id: "req-123",
          error_code: null,
          metadata: { permission: "VIEW" },
          created_at: "2026-11-16T14:02:03",
        },
      ],
    });
    renderPage();

    expect(await screen.findByText("16/11/2026 14:02:03")).toBeInTheDocument();
    expect(screen.getByText("Hệ thống")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Xem chi tiết" }));
    expect(screen.getByText("req-123")).toBeInTheDocument();
    expect(screen.queryByText(/Địa chỉ IP/)).not.toBeInTheDocument();
  });
});
