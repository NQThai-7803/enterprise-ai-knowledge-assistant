import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../api/client";
import type { AuthenticatedUser, FeedbackReportItem } from "../../api/types";
import { contractManager } from "../../test/fixtures/contract";
import { FeedbackPage } from "./FeedbackPage";

let currentUser: AuthenticatedUser = contractManager;
vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ user: currentUser }) }));
vi.mock("../../api/client", () => ({ apiClient: { feedback: { list: vi.fn() }, departments: { list: vi.fn() } } }));

const item: FeedbackReportItem = {
  id: "fb-1",
  message_id: "m-1",
  rating: "NOT_HELPFUL",
  reason: "Chính sách nghỉ có nêu thâm niên nhưng hệ thống không trả lời.",
  user_id: "uuid",
  department_id: "uuid",
  created_at: "2026-11-15T09:42:00Z",
  updated_at: "2026-11-15T09:42:00Z",
};

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <FeedbackPage />
    </QueryClientProvider>,
  );
}

describe("FeedbackPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.departments.list).mockResolvedValue({ data: [], meta: { page: 1, page_size: 100, total: 0, total_pages: 0 } });
  });

  it("shows the submitter and department names an Admin receives (BR-4 option a)", async () => {
    currentUser = { ...contractManager, role: "ADMIN", department_id: null, department_name: null };
    vi.mocked(apiClient.feedback.list).mockResolvedValue({
      data: [{ ...item, user_full_name: "Staff UAT", department_name: "UAT-KNOWLEDGE" }],
      meta: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    });
    renderPage();

    expect(await screen.findByText("Staff UAT · UAT-KNOWLEDGE")).toBeInTheDocument();
    expect(screen.getByText("Chưa hữu ích", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("1 phản hồi")).toBeInTheDocument();
  });

  it("shows a Manager no user name, only their own department", async () => {
    currentUser = contractManager;
    vi.mocked(apiClient.feedback.list).mockResolvedValue({
      data: [item],
      meta: { page: 1, page_size: 20, total: 1, total_pages: 1 },
    });
    renderPage();

    expect(await screen.findByText("Nhân sự")).toBeInTheDocument();
    expect(screen.queryByText(/Staff UAT/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Phòng ban")).not.toBeInTheDocument();
  });
});
