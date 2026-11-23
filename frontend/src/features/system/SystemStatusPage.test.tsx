import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../api/client";
import type { AdminSystemResponse, AuthenticatedUser } from "../../api/types";
import { contractManager } from "../../test/fixtures/contract";
import { SystemStatusPage } from "./SystemStatusPage";

let currentUser: AuthenticatedUser = contractManager;
vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ user: currentUser }) }));
vi.mock("../../api/client", () => ({
  apiClient: { health: { live: vi.fn(), ready: vi.fn() }, admin: { system: vi.fn() } },
}));

// API_SPEC "TASK-032 Admin Monitoring API", GET /admin/system example (BR-8), fields the UI reads.
const adminSystem: AdminSystemResponse = {
  generated_at: "2026-11-20T11:09:09Z",
  version: {
    app_name: "Enterprise AI Knowledge Assistant",
    version: "0.1.0",
    environment: "production",
    python_version: "3.12.16",
    api_prefix: "/api/v1",
    migration_head: "20261120_0013",
    database_revision: "20261120_0013",
    started_at: "2026-11-20T11:09:05Z",
    uptime_seconds: 3,
  },
  uptime_seconds: 3,
  health: {
    status: "healthy",
    generated_at: "2026-11-20T11:09:09Z",
    checks: [{ name: "api", status: "ok", enabled: true, message: "API process is running." }],
  },
  providers: {
    llm: {
      provider_type: "llm",
      provider: "ollama",
      status: "healthy",
      enabled: true,
      configured: true,
      display_name: "Ollama",
      model: "qwen3.5-text:4b",
      connectivity_checked: false,
      message: "…",
    },
    web_search: {
      provider_type: "web_search",
      provider: "mock",
      status: "disabled",
      enabled: false,
      configured: false,
      display_name: "Mock Web Search",
      model: null,
      connectivity_checked: false,
      message: "Web search is disabled.",
    },
  },
  statistics: { documents: { total: 12, by_status: { READY: 12 } } },
};

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <SystemStatusPage />
    </QueryClientProvider>,
  );
}

describe("SystemStatusPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentUser = contractManager;
    vi.mocked(apiClient.health.live).mockResolvedValue({ status: "ok" });
    vi.mocked(apiClient.health.ready).mockResolvedValue({
      status: "ready",
      checks: { database: "ok", redis: "ok" },
      reranker_mode: "lexical_fallback",
    });
    vi.mocked(apiClient.admin.system).mockResolvedValue({ data: adminSystem, meta: null });
  });

  it("shows provider, model, checks and version to an Admin from /admin/system", async () => {
    currentUser = { ...contractManager, role: "ADMIN" };
    renderPage();

    expect(await screen.findByText("qwen3.5-text:4b")).toBeInTheDocument();
    expect(screen.getByText("Ollama")).toBeInTheDocument();
    expect(screen.getByText("Mock Web Search")).toBeInTheDocument();
    expect(screen.getByTitle("api: API process is running.")).toHaveTextContent("API");
    expect(screen.getByText("Enterprise AI Knowledge Assistant 0.1.0")).toBeInTheDocument();
    expect(screen.getByText("20261120_0013 / 20261120_0013")).toBeInTheDocument();
    // Handoff (8): Vietnamese labels, the raw codes only as tooltips.
    expect(screen.getByText("Theo từ khóa (dự phòng)")).toHaveAttribute("title", "lexical_fallback");
    expect(screen.getByText("Sẵn sàng · 12")).toHaveAttribute("title", "READY");
    expect(screen.getByText("Vận hành")).toHaveAttribute("title", "production");
    expect(screen.queryByText("lexical_fallback")).not.toBeInTheDocument();
  });

  it("does not call the Admin endpoint for other roles", async () => {
    renderPage();

    expect(await screen.findByText("Sẵn sàng")).toBeInTheDocument();
    expect(screen.getByText("Nhà cung cấp, mô hình và phiên bản chỉ hiện cho quản trị viên.")).toBeInTheDocument();
    expect(apiClient.admin.system).not.toHaveBeenCalled();
    expect(screen.queryByText("Ollama")).not.toBeInTheDocument();
  });
});
