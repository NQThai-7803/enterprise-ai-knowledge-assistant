import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/errors";
import { apiClient } from "../../api/client";
import type { AuthenticatedUser, Department, ListResponse } from "../../api/types";
import { ToastProvider } from "../../components/feedback/ToastProvider";
import { contractDocument, contractManager } from "../../test/fixtures/contract";
import { DocumentUploadPage } from "./DocumentUploadPage";

vi.mock("../../api/client", () => ({
  apiClient: {
    departments: { list: vi.fn() },
    documents: { upload: vi.fn(), list: vi.fn() },
  },
}));

const admin: AuthenticatedUser = { ...contractManager, id: "admin-uuid", role: "ADMIN", department_id: null, department_name: null };
let currentUser: AuthenticatedUser = admin;
vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ user: currentUser }) }));

const department: Department = {
  id: "department-uuid-1",
  name: "UAT Knowledge Operations",
  code: "UAT-KNOWLEDGE",
  description: null,
  created_at: "2026-08-09T00:00:00Z",
};

function listResponse<T>(data: T[]): ListResponse<T> {
  return { data, meta: { page: 1, page_size: 100, total: data.length, total_pages: data.length ? 1 : 0 } };
}

const pdf = () => new File(["pdf"], "nghi-phep.pdf", { type: "application/pdf" });
const fileInput = () => screen.getByLabelText("Tệp PDF");
const scope = (name: RegExp) => screen.getByRole("radio", { name });

async function fillRequired(user: ReturnType<typeof userEvent.setup>) {
  await user.upload(fileInput(), pdf());
  await user.type(screen.getByLabelText("Tiêu đề"), "Quy định nghỉ phép");
}

describe("DocumentUploadPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentUser = admin;
    vi.stubGlobal("crypto", { randomUUID: () => "toast-id" });
    vi.mocked(apiClient.departments.list).mockResolvedValue(listResponse([department]));
    vi.mocked(apiClient.documents.list).mockResolvedValue(listResponse([contractDocument]));
    vi.mocked(apiClient.documents.upload).mockResolvedValue({ data: contractDocument, meta: null });
  });

  it("lets an Admin pick any department and sends its id", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await fillRequired(user);
    await user.click(scope(/^Phòng ban/));
    await screen.findByRole("option", { name: "UAT Knowledge Operations (UAT-KNOWLEDGE)" });
    await user.selectOptions(screen.getByLabelText("Phòng ban"), department.id);
    await user.click(screen.getByRole("button", { name: "Tải lên" }));

    await waitFor(() =>
      expect(apiClient.documents.upload).toHaveBeenCalledWith(
        expect.objectContaining({ access_scope: "DEPARTMENT", department_id: department.id }),
      ),
    );
  });

  it("blocks a department upload without a department", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await fillRequired(user);
    await user.click(scope(/^Phòng ban/));
    await screen.findByRole("option", { name: "UAT Knowledge Operations (UAT-KNOWLEDGE)" });
    await user.click(screen.getByRole("button", { name: "Tải lên" }));

    expect(await screen.findByText("Chọn phòng ban.")).toBeInTheDocument();
    expect(apiClient.documents.upload).not.toHaveBeenCalled();
  });

  it("shows a retry state when departments cannot load", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.departments.list).mockRejectedValueOnce(new Error("network"));
    renderUploadPage();

    await user.click(scope(/^Phòng ban/));

    expect(await screen.findByRole("alert")).toHaveTextContent("Không tải được danh sách phòng ban.");
    expect(screen.getByRole("button", { name: "Thử lại" })).toBeInTheDocument();
  });

  it("sends no department for a private upload", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: "Tải lên" }));

    await waitFor(() =>
      expect(apiClient.documents.upload).toHaveBeenCalledWith(
        expect.objectContaining({ access_scope: "PRIVATE", department_id: null, lifecycle_status: "ACTIVE" }),
      ),
    );
  });

  it("limits a Manager to PRIVATE or their own department, chosen by hand (BR-1 rule 3)", async () => {
    currentUser = contractManager;
    const user = userEvent.setup();
    renderUploadPage();

    expect(scope(/^Toàn công ty/)).toBeDisabled();
    await fillRequired(user);
    await user.click(scope(/^Phòng ban/));
    const select = screen.getByLabelText("Phòng ban");
    expect(select).toHaveValue("");
    expect(within(select).getAllByRole("option").map((option) => option.textContent)).toEqual(["Chọn phòng ban", "Nhân sự"]);
    expect(apiClient.departments.list).not.toHaveBeenCalled();

    await user.selectOptions(select, "uuid");
    await user.click(screen.getByRole("button", { name: "Tải lên" }));

    await waitFor(() =>
      expect(apiClient.documents.upload).toHaveBeenCalledWith(
        expect.objectContaining({ access_scope: "DEPARTMENT", department_id: "uuid" }),
      ),
    );
  });

  it("disables the department scope for a Manager without a department", () => {
    currentUser = { ...contractManager, department_id: null, department_name: null };
    renderUploadPage();

    expect(scope(/^Phòng ban/)).toBeDisabled();
    expect(screen.getByText("Bạn chưa thuộc phòng ban nào")).toBeInTheDocument();
  });

  it("sends the BR-1 version fields from the contract example", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await fillRequired(user);
    await user.type(screen.getByLabelText("Mã tài liệu"), "ND-HR-007");
    await user.type(screen.getByLabelText("Phiên bản"), "1.0");
    fireEvent.change(screen.getByLabelText("Hiệu lực từ"), { target: { value: "2026-09-01" } });
    await user.selectOptions(screen.getByLabelText("Vòng đời"), "DRAFT");
    expect(screen.getByText("Bản nháp vẫn hiện trong danh sách nhưng không được dùng để trả lời.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tải lên" }));

    await waitFor(() =>
      expect(apiClient.documents.upload).toHaveBeenCalledWith(
        expect.objectContaining({
          document_code: "ND-HR-007",
          document_version: "1.0",
          effective_from: "2026-09-01",
          effective_to: null,
          lifecycle_status: "DRAFT",
          supersedes_document_id: null,
        }),
      ),
    );
  });

  it("checks the effective dates before sending", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await fillRequired(user);
    fireEvent.change(screen.getByLabelText("Hiệu lực từ"), { target: { value: "2026-09-01" } });
    fireEvent.change(screen.getByLabelText("Hiệu lực đến"), { target: { value: "2026-08-01" } });
    await user.click(screen.getByRole("button", { name: "Tải lên" }));

    expect(await screen.findByText("Ngày hết hiệu lực không được trước ngày bắt đầu hiệu lực.")).toBeInTheDocument();
    expect(apiClient.documents.upload).not.toHaveBeenCalled();
  });

  it("puts BR-10 422 details on their fields (contract example) and keeps the rest as a form error", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.documents.upload).mockRejectedValueOnce(
      new ApiError({
        code: "VALIDATION_ERROR",
        message: "effective_to must not precede effective_from.",
        status: 422,
        details: [
          { field: "effective_to", code: "INVALID_RANGE", message: "effective_to must not precede effective_from." },
          { field: "title", code: "TOO_LONG", message: "title is too long." },
          { field: null, code: "INVALID", message: "Request is invalid." },
        ],
      }),
    );
    renderUploadPage();

    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: "Tải lên" }));

    expect(await screen.findByText("Ngày hết hiệu lực không được trước ngày bắt đầu hiệu lực.")).toBeInTheDocument();
    expect(screen.getByText("Nội dung quá dài.")).toBeInTheDocument();
    expect(screen.getAllByRole("alert").map((node) => node.textContent)).toContain("Giá trị không hợp lệ.");
    expect(screen.queryByText(/must not precede/)).not.toBeInTheDocument();
  });

  it("shows any other 422 and a 403 as a form error", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.documents.upload)
      .mockRejectedValueOnce(new ApiError({ code: "VALIDATION_ERROR", message: "Request is invalid", status: 422 }))
      .mockRejectedValueOnce(new ApiError({ code: "FORBIDDEN", message: "Forbidden", status: 403 }));
    renderUploadPage();

    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: "Tải lên" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Dữ liệu gửi lên chưa hợp lệ.");

    await user.click(screen.getByRole("button", { name: "Tải lên" }));
    expect(await screen.findByText("Bạn không được tải lên với phạm vi hoặc phòng ban này.")).toBeInTheDocument();
  });

  it("removes the chosen file", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await user.upload(fileInput(), pdf());
    expect(screen.getByText("nghi-phep.pdf")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Bỏ tệp đã chọn" }));

    expect(screen.queryByText("nghi-phep.pdf")).not.toBeInTheDocument();
  });
});

function renderUploadPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter>
          <DocumentUploadPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}
