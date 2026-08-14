import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/errors";
import { apiClient } from "../../api/client";
import type { Department, DocumentItem, ListResponse } from "../../api/types";
import { ToastProvider } from "../../components/feedback/ToastProvider";
import { DocumentUploadPage } from "./DocumentUploadPage";

vi.mock("../../api/client", () => ({
  apiClient: {
    departments: {
      list: vi.fn(),
    },
    documents: {
      upload: vi.fn(),
    },
  },
}));

const department: Department = {
  id: "department-uuid-1",
  name: "UAT Knowledge Operations",
  code: "UAT-KNOWLEDGE",
  description: null,
  created_at: "2026-08-09T00:00:00Z",
};

const uploadedDocument: DocumentItem = {
  id: "document-uuid-1",
  title: "Policy",
  description: null,
  original_filename: "policy.pdf",
  mime_type: "application/pdf",
  file_size: 128,
  status: "UPLOADED",
  access_scope: "DEPARTMENT",
  department_id: department.id,
  uploaded_by: "user-uuid-1",
  created_at: "2026-08-09T00:00:00Z",
  updated_at: "2026-08-09T00:00:00Z",
};

function listResponse<T>(data: T[]): ListResponse<T> {
  return {
    data,
    meta: { page: 1, page_size: 100, total: data.length, total_pages: data.length ? 1 : 0 },
  };
}

function dataResponse(data: DocumentItem) {
  return { data, meta: null };
}

describe("DocumentUploadPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("crypto", { randomUUID: () => "toast-id" });
    vi.mocked(apiClient.departments.list).mockResolvedValue(listResponse([department]));
    vi.mocked(apiClient.documents.upload).mockResolvedValue(dataResponse(uploadedDocument));
  });

  it("hides the department selector for organization scope", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await user.selectOptions(screen.getByLabelText("Access scope"), "ORGANIZATION");

    expect(screen.queryByLabelText("Department")).not.toBeInTheDocument();
    expect(apiClient.departments.list).not.toHaveBeenCalled();
  });

  it("loads departments and sends the selected department UUID for department uploads", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await user.type(screen.getByLabelText("Title"), "Policy");
    await user.upload(fileInput(), new File(["pdf"], "policy.pdf", { type: "application/pdf" }));
    await user.selectOptions(screen.getByLabelText("Access scope"), "DEPARTMENT");
    await screen.findByRole("option", { name: "UAT Knowledge Operations (UAT-KNOWLEDGE)" });
    await user.selectOptions(screen.getByLabelText("Department"), department.id);
    await user.click(screen.getByRole("button", { name: "Upload" }));

    await waitFor(() => {
      expect(apiClient.documents.upload).toHaveBeenCalledWith(
        expect.objectContaining({ access_scope: "DEPARTMENT", department_id: department.id }),
      );
    });
  });

  it("blocks department uploads when no department is selected", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await user.type(screen.getByLabelText("Title"), "Policy");
    await user.upload(fileInput(), new File(["pdf"], "policy.pdf", { type: "application/pdf" }));
    await user.selectOptions(screen.getByLabelText("Access scope"), "DEPARTMENT");
    await screen.findByRole("option", { name: "UAT Knowledge Operations (UAT-KNOWLEDGE)" });
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(await screen.findByText("Vui lòng chọn phòng ban.")).toBeInTheDocument();
    expect(apiClient.documents.upload).not.toHaveBeenCalled();
  });

  it("handles department API errors with a retry state", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.departments.list).mockRejectedValueOnce(new Error("network"));
    renderUploadPage();

    await user.selectOptions(screen.getByLabelText("Access scope"), "DEPARTMENT");

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load departments.");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("does not send a department UUID for private uploads", async () => {
    const user = userEvent.setup();
    renderUploadPage();

    await user.type(screen.getByLabelText("Title"), "Private policy");
    await user.upload(fileInput(), new File(["pdf"], "private.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: "Upload" }));

    await waitFor(() => {
      expect(apiClient.documents.upload).toHaveBeenCalledWith(
        expect.objectContaining({ access_scope: "PRIVATE", department_id: null }),
      );
    });
  });

  it("shows a safe validation message for backend 422 upload errors", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.documents.upload).mockRejectedValueOnce(
      new ApiError({ code: "VALIDATION_ERROR", message: "Invalid UUID", status: 422, details: { loc: ["department_id"] } }),
    );
    renderUploadPage();

    await user.type(screen.getByLabelText("Title"), "Policy");
    await user.upload(fileInput(), new File(["pdf"], "policy.pdf", { type: "application/pdf" }));
    await user.selectOptions(screen.getByLabelText("Access scope"), "DEPARTMENT");
    await screen.findByRole("option", { name: "UAT Knowledge Operations (UAT-KNOWLEDGE)" });
    await user.selectOptions(screen.getByLabelText("Department"), department.id);
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(await screen.findByText("Vui lòng chọn phòng ban.")).toBeInTheDocument();
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

function fileInput() {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) {
    throw new Error("File input not found.");
  }
  return input;
}