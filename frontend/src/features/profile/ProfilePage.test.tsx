import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../api/client";
import type { AuthenticatedUser } from "../../api/types";
import { ToastProvider } from "../../components/feedback/ToastProvider";
import { AppShell } from "../../layouts/AppShell";
import { contractManager } from "../../test/fixtures/contract";
import { ProfilePage } from "./ProfilePage";

let currentUser: AuthenticatedUser = contractManager;
vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ user: currentUser, logout: vi.fn() }) }));
vi.mock("../../api/client", () => ({ apiClient: { health: { ready: vi.fn() } } }));

describe("BR-4 department_name", () => {
  beforeEach(() => {
    currentUser = contractManager;
    vi.mocked(apiClient.health.ready).mockResolvedValue({ status: "ready", checks: {} });
  });

  it("shows the caller's own department on the profile, from the /auth/me example", () => {
    render(<ProfilePage />);

    expect(screen.getByText("Manager Nhân sự")).toBeInTheDocument();
    expect(screen.getByText("Nhân sự")).toBeInTheDocument();
    expect(screen.getByText(/Bạn tải lên được tài liệu riêng tư hoặc cho phòng Nhân sự\./)).toBeInTheDocument();
  });

  it("says so when the user has no department", () => {
    currentUser = { ...contractManager, role: "STAFF", department_id: null, department_name: null };
    render(<ProfilePage />);

    expect(screen.getByText("Chưa thuộc phòng ban")).toBeInTheDocument();
  });

  it("shows role and department in the sidebar user card", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ToastProvider>
          <MemoryRouter>
            <AppShell />
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    );

    expect(screen.getByText("Quản lý · Nhân sự")).toBeInTheDocument();
  });
});
