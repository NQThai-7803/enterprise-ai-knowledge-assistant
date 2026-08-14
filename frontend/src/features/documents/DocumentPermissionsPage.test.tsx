import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../api/client";
import { ApiError } from "../../api/errors";
import type { Department, DocumentPermission, ListResponse, User } from "../../api/types";
import { ToastProvider } from "../../components/feedback/ToastProvider";
import { DocumentPermissionsPage } from "./DocumentPermissionsPage";

vi.mock("../../api/client", () => ({
  apiClient: {
    users: {
      list: vi.fn(),
    },
    departments: {
      list: vi.fn(),
    },
    documents: {
      permissions: vi.fn(),
      grantPermission: vi.fn(),
      revokePermission: vi.fn(),
    },
  },
}));

const ids = {
  document: "00000000-0000-4000-8000-000000000001",
  admin: "00000000-0000-4000-8000-000000000002",
  manager: "00000000-0000-4000-8000-000000000003",
  staff: "00000000-0000-4000-8000-000000000004",
  department: "00000000-0000-4000-8000-000000000005",
  permission: "00000000-0000-4000-8000-000000000006",
};

const manager: User = {
  id: ids.manager,
  email: "manager.uat@example.test",
  full_name: "UAT Manager",
  role: "MANAGER",
  department_id: ids.department,
  is_active: true,
  created_at: "2026-08-09T00:00:00Z",
  updated_at: "2026-08-09T00:00:00Z",
};

const staff: User = {
  id: ids.staff,
  email: "staff.uat@example.test",
  full_name: "UAT Staff",
  role: "STAFF",
  department_id: ids.department,
  is_active: true,
  created_at: "2026-08-09T00:00:00Z",
  updated_at: "2026-08-09T00:00:00Z",
};

const department: Department = {
  id: ids.department,
  name: "UAT Knowledge Operations",
  code: "UAT-KNOWLEDGE",
  description: null,
  created_at: "2026-08-09T00:00:00Z",
};

const grantedPermission: DocumentPermission = {
  id: ids.permission,
  document_id: ids.document,
  user_id: ids.manager,
  department_id: null,
  permission: "VIEW",
  created_by: ids.admin,
  created_at: "2026-08-09T00:00:00Z",
};

function listResponse<T>(data: T[]): ListResponse<T> {
  return {
    data,
    meta: { page: 1, page_size: 100, total: data.length, total_pages: data.length ? 1 : 0 },
  };
}

function dataResponse<T>(data: T) {
  return { data, meta: null };
}

describe("DocumentPermissionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("crypto", { randomUUID: () => "toast-id" });
    vi.mocked(apiClient.users.list).mockResolvedValue(listResponse([manager, staff]));
    vi.mocked(apiClient.departments.list).mockResolvedValue(listResponse([department]));
    vi.mocked(apiClient.documents.permissions).mockResolvedValue(dataResponse([]));
    vi.mocked(apiClient.documents.grantPermission).mockResolvedValue(dataResponse(grantedPermission));
    vi.mocked(apiClient.documents.revokePermission).mockResolvedValue(undefined);
  });

  it("loads the user selector and sends the selected user UUID", async () => {
    const user = userEvent.setup();
    renderPermissionsPage();

    await screen.findByRole("option", { name: "UAT Manager — manager.uat@example.test" });
    expect(screen.queryByLabelText("Grantee ID")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("User"), ids.manager);
    await user.click(screen.getByRole("button", { name: "Grant" }));

    await waitFor(() => {
      expect(apiClient.documents.grantPermission).toHaveBeenCalledWith(ids.document, {
        user_id: ids.manager,
        department_id: null,
        permission: "VIEW",
      });
    });
    await waitFor(() => expect(apiClient.documents.permissions).toHaveBeenCalledTimes(2));
  });

  it("loads the department grantee selector and clears stale user selections when type changes", async () => {
    const user = userEvent.setup();
    renderPermissionsPage();

    await screen.findByRole("option", { name: "UAT Manager — manager.uat@example.test" });
    await user.selectOptions(screen.getByLabelText("User"), ids.manager);
    await user.selectOptions(screen.getByLabelText("Grantee type"), "department");

    const departmentSelect = await screen.findByLabelText("Department");
    expect(departmentSelect).toHaveValue("");
    await screen.findByRole("option", { name: "UAT Knowledge Operations (UAT-KNOWLEDGE)" });

    await user.selectOptions(departmentSelect, ids.department);
    await user.selectOptions(screen.getByLabelText("Permission"), "EDIT");
    await user.click(screen.getByRole("button", { name: "Grant" }));

    await waitFor(() => {
      expect(apiClient.documents.grantPermission).toHaveBeenCalledWith(ids.document, {
        user_id: null,
        department_id: ids.department,
        permission: "EDIT",
      });
    });
  });

  it("blocks grant submission when no grantee is selected", async () => {
    const user = userEvent.setup();
    renderPermissionsPage();

    await screen.findByRole("option", { name: "UAT Manager — manager.uat@example.test" });
    await user.click(screen.getByRole("button", { name: "Grant" }));

    expect(await screen.findByText("Vui lòng chọn người dùng hoặc phòng ban.")).toBeInTheDocument();
    expect(apiClient.documents.grantPermission).not.toHaveBeenCalled();
  });

  it("shows a safe message when grant fails", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.documents.grantPermission).mockRejectedValueOnce(
      new ApiError({ code: "RESOURCE_NOT_FOUND", message: "raw backend id error", status: 404 }),
    );
    renderPermissionsPage();

    await screen.findByRole("option", { name: "UAT Manager — manager.uat@example.test" });
    await user.selectOptions(screen.getByLabelText("User"), ids.manager);
    await user.click(screen.getByRole("button", { name: "Grant" }));

    expect(await screen.findByText("Người dùng hoặc phòng ban được chọn không hợp lệ.")).toBeInTheDocument();
  });

  it("resolves permission list display names from cached users", async () => {
    vi.mocked(apiClient.documents.permissions).mockResolvedValueOnce(dataResponse([grantedPermission]));
    renderPermissionsPage();

    expect(await screen.findByText("User UAT Manager — manager.uat@example.test")).toBeInTheDocument();
  });

  it("shows a retry state when department grantees cannot be loaded", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.departments.list).mockRejectedValueOnce(new Error("network"));
    renderPermissionsPage();

    await user.selectOptions(screen.getByLabelText("Grantee type"), "department");

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load departments.");
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

function renderPermissionsPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[`/documents/${ids.document}/permissions`]}>
          <Routes>
            <Route path="/documents/:documentId/permissions" element={<DocumentPermissionsPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}