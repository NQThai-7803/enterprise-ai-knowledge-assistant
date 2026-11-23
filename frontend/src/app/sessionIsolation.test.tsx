import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { refreshAccessToken } from "../api/client";
import type { AuthenticatedUser } from "../api/types";
import { ToastProvider } from "../components/feedback/ToastProvider";
import { AuthProvider } from "../features/auth/AuthProvider";
import { contractDocument } from "../test/fixtures/contract";
import { App } from "./App";

// Every piece of the admin's data carries this marker, so any leak shows up as text on the page.
const MARK = "ADMIN-MẬT";
const CREATED = "2026-11-20T08:00:00Z";

const users: Record<"admin" | "staff", AuthenticatedUser> = {
  admin: {
    id: "admin-1",
    email: "admin@example.test",
    full_name: `Quản trị ${MARK}`,
    role: "ADMIN",
    department_id: null,
    department_name: null,
    is_active: true,
  },
  staff: {
    id: "staff-1",
    email: "staff@example.test",
    full_name: "Nhân viên",
    role: "STAFF",
    department_id: "dept-1",
    department_name: "Kinh doanh",
    is_active: true,
  },
};

const adminSession = {
  id: "s-admin",
  title: `Phiên ${MARK}`,
  is_archived: false,
  message_count: 2,
  created_at: CREATED,
  updated_at: CREATED,
};

const adminMessages = [
  { id: "m1", role: "USER", content: `Câu hỏi ${MARK}`, response_time_ms: null, citations: [], created_at: CREATED, grounding_status: null },
  { id: "m2", role: "ASSISTANT", content: `Trả lời ${MARK}`, response_time_ms: 900, citations: [], created_at: CREATED, grounding_status: "ANSWERED" },
];

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function list(data: unknown[]) {
  return { data, meta: { page: 1, page_size: 50, total: data.length, total_pages: data.length ? 1 : 0 } };
}

function sseBody(answer: string) {
  const events: [string, unknown][] = [
    ["stream.started", { request_id: "req-1", session_id: "s-admin", provider: "p", model: "m", strategy: "buffer_after_validation" }],
    ["message.delta", { sequence: 1, content: answer }],
    [
      "message.completed",
      { message_id: "m3", session_id: "s-admin", content: answer, citations: [], provider: "p", model: "m", usage: null, grounding_status: "ANSWERED", retrieved_chunk_count: 0 },
    ],
  ];
  return events.map(([name, data], index) => `event: ${name}\nid: evt-${index}\ndata: ${JSON.stringify(data)}\n\n`).join("");
}

function setup({ path: initialPath = "/login", seed }: { path?: string; seed?: (client: QueryClient) => void } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  seed?.(queryClient);
  const cachedKeys = () =>
    queryClient
      .getQueryCache()
      .getAll()
      .filter((query) => query.state.data !== undefined)
      .map((query) => query.queryKey);

  let releaseStaff!: () => void;
  const staffGate = new Promise<void>((resolve) => {
    releaseStaff = resolve;
  });
  let releaseRefresh!: () => void;
  const refreshGate = new Promise<void>((resolve) => {
    releaseRefresh = resolve;
  });
  // The cache as the staff's first request leaves: before any of the staff's data can arrive.
  const atFirstStaffRequest: { cached: unknown[]; mutations: number } = { cached: [], mutations: -1 };

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url);
      const path = url.pathname;
      const token = new Headers(init?.headers).get("Authorization");

      if (path === "/api/v1/auth/login") {
        const who = String(JSON.parse(String(init?.body)).email).startsWith("admin") ? "admin" : "staff";
        return json({
          data: { access_token: `${who}-access`, refresh_token: `${who}-refresh`, token_type: "bearer", expires_in: 900, user: users[who] },
          meta: null,
        });
      }
      if (path === "/api/v1/auth/logout") return new Response(null, { status: 204 });
      if (path === "/api/v1/auth/me" && token === "Bearer staff-access") return json({ data: users.staff, meta: null });
      if (path === "/api/v1/auth/me" && token === "Bearer admin-access-2") return json({ data: users.admin, meta: null });
      if (path === "/api/v1/auth/refresh") {
        await refreshGate;
        return json({
          data: { access_token: "admin-access-2", refresh_token: "admin-refresh-2", token_type: "bearer", expires_in: 900, user: users.admin },
          meta: null,
        });
      }
      if (path.startsWith("/health")) return json({ status: "ready", checks: {} });

      if (token === "Bearer staff-access") {
        if (atFirstStaffRequest.mutations === -1) {
          atFirstStaffRequest.cached = cachedKeys();
          atFirstStaffRequest.mutations = queryClient.getMutationCache().getAll().length;
        }
        await staffGate;
        if (path === "/api/v1/chat/sessions") return json(list([]));
        if (path === "/api/v1/documents") return json(list([{ ...contractDocument, id: "doc-staff", title: "Sổ tay nhân viên" }]));
      }
      if (token === "Bearer admin-access") {
        if (path === "/api/v1/chat/sessions") return json(list([adminSession]));
        if (path === "/api/v1/users" || path === "/api/v1/departments") return json(list([]));
        if (path === "/api/v1/messages/m2/feedback") {
          return json({ data: { id: "f1", message_id: "m2", rating: "HELPFUL", reason: null, created_at: CREATED, updated_at: CREATED }, meta: null });
        }
        if (path === "/api/v1/chat/sessions/s-admin") {
          return json({
            data: { ...adminSession, messages: adminMessages, message_pagination: { page: 1, page_size: 100, total: 2, total_pages: 1 } },
            meta: null,
          });
        }
        if (path === "/api/v1/chat/sessions/s-admin/messages/stream") {
          return new Response(sseBody(`Lương ${MARK}`), { headers: { "Content-Type": "text/event-stream" } });
        }
        if (path === "/api/v1/documents") return json(list([{ ...contractDocument, id: "doc-admin", title: `Bảng lương ${MARK}` }]));
      }
      return json({ error: { code: "RESOURCE_NOT_FOUND", message: "Not found.", details: null, request_id: "req-test" } }, 404);
    }),
  );

  const renderApp = (path: string, client: QueryClient) =>
    render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <AuthProvider>
            <MemoryRouter initialEntries={[path]}>
              <App />
            </MemoryRouter>
          </AuthProvider>
        </ToastProvider>
      </QueryClientProvider>,
    );
  let view = renderApp(initialPath, queryClient);
  // A tab reload: a fresh app on the same sessionStorage.
  const reload = (path: string) => {
    view.unmount();
    view = renderApp(path, new QueryClient({ defaultOptions: { queries: { retry: false } } }));
  };
  return { user: userEvent.setup(), queryClient, cachedKeys, releaseStaff, releaseRefresh, atFirstStaffRequest, reload };
}

async function signIn(user: ReturnType<typeof userEvent.setup>, email: string) {
  await user.type(await screen.findByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Mật khẩu"), "mat-khau-thu");
  await user.click(screen.getByRole("button", { name: "Đăng nhập" }));
}

async function adminLoadsDocumentsAndChats(user: ReturnType<typeof userEvent.setup>) {
  await signIn(user, users.admin.email);
  expect(await screen.findByText(`Trả lời ${MARK}`)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Câu trả lời hữu ích" }));
  expect(await screen.findByText("Đã lưu đánh giá")).toBeInTheDocument();
  await user.type(screen.getByRole("textbox", { name: "Câu hỏi" }), "Lương tháng này?");
  await user.click(screen.getByRole("button", { name: "Gửi câu hỏi" }));
  expect(await screen.findByText(`Lương ${MARK}`)).toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "Tài liệu" }));
  expect(await screen.findByText(`Bảng lương ${MARK}`)).toBeInTheDocument();
}

// Records every node or text the page ever shows, so even a frame that is replaced at once counts:
// callbacks run later, so removed nodes and old text values are checked as well as added ones.
function watchForAdminData() {
  const seen = { adminDataRendered: false };
  const observer = new MutationObserver((records) => {
    for (const record of records) {
      const nodes = [...record.addedNodes, ...record.removedNodes];
      const texts = [record.oldValue, record.target.textContent, ...nodes.map((node) => node.textContent)];
      seen.adminDataRendered ||= texts.some((text) => text?.includes(MARK));
    }
  });
  observer.observe(document.body, { childList: true, subtree: true, characterData: true, characterDataOldValue: true });
  return { seen, stop: () => observer.disconnect() };
}

beforeAll(() => {
  // jsdom has no element scrolling; the chat column scrolls to its newest message.
  if (!Element.prototype.scrollTo) {
    Element.prototype.scrollTo = () => {};
  }
});

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

describe("session boundary", () => {
  it("staff signing in after an admin's logout starts on an empty cache and never sees the admin's data", async () => {
    const { user, queryClient, cachedKeys, releaseStaff, atFirstStaffRequest } = setup();
    await adminLoadsDocumentsAndChats(user);
    expect(cachedKeys().length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "Đăng xuất" }));
    expect(await screen.findByRole("button", { name: "Đăng nhập" })).toBeInTheDocument();
    expect(cachedKeys()).toEqual([]);
    expect(queryClient.getMutationCache().getAll()).toHaveLength(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.body.textContent).not.toContain(MARK);

    const watch = watchForAdminData();

    await signIn(user, users.staff.email);
    await waitFor(() => expect(atFirstStaffRequest.mutations).not.toBe(-1));
    expect(atFirstStaffRequest).toEqual({ cached: [], mutations: 0 });
    expect(document.body.textContent).not.toContain(MARK);
    // The admin's toast (5 s) is gone as soon as staff signs in.
    expect(screen.queryByText("Đã lưu đánh giá")).not.toBeInTheDocument();

    releaseStaff();
    await user.click(await screen.findByRole("link", { name: "Tài liệu" }));
    expect(await screen.findByText("Sổ tay nhân viên")).toBeInTheDocument();
    watch.stop();
    expect(watch.seen.adminDataRendered).toBe(false);
    expect(document.body.textContent).not.toContain(MARK);
  });

  it("data left in the cache is cleared before a restored session's page renders", async () => {
    // A restored session renders /chat in the same commit as the user change, unlike the login form,
    // whose navigation renders later; whatever the cache holds then (here: another user's sessions)
    // must not reach the page.
    sessionStorage.setItem("enterprise_ai_access_token", "staff-access");
    sessionStorage.setItem("enterprise_ai_refresh_token", "staff-refresh");
    const watch = watchForAdminData();
    const { cachedKeys, releaseStaff, atFirstStaffRequest } = setup({
      path: "/chat",
      seed: (client) => client.setQueryData(["chat", "sessions"], list([adminSession])),
    });

    await waitFor(() => expect(atFirstStaffRequest.mutations).not.toBe(-1));
    expect(atFirstStaffRequest.cached).toEqual([]);
    releaseStaff();
    await waitFor(() => expect(cachedKeys()).toContainEqual(["chat", "sessions"]));
    watch.stop();
    expect(watch.seen.adminDataRendered).toBe(false);
    expect(document.body.textContent).not.toContain(MARK);
  });

  it("an expired session clears the cache too", async () => {
    const { user, cachedKeys } = setup();
    await adminLoadsDocumentsAndChats(user);

    window.dispatchEvent(new CustomEvent("auth:expired"));
    expect(await screen.findByRole("button", { name: "Đăng nhập" })).toBeInTheDocument();
    expect(cachedKeys()).toEqual([]);
    expect(document.body.textContent).not.toContain(MARK);
  });
});

describe("token refresh during a logout", () => {
  it("a refresh answered after the logout leaves no tokens, and a reload opens the sign-in page", async () => {
    const { user, releaseRefresh, reload } = setup();
    await signIn(user, users.admin.email);
    expect(await screen.findByText(`Trả lời ${MARK}`)).toBeInTheDocument();

    // A request found its access token expired and is refreshing when the user logs out.
    const refreshing = refreshAccessToken();
    await user.click(screen.getByRole("button", { name: "Đăng xuất" }));
    expect(await screen.findByRole("button", { name: "Đăng nhập" })).toBeInTheDocument();
    releaseRefresh();
    expect(await refreshing).toBe(false);
    expect(sessionStorage.length).toBe(0);

    reload("/chat");
    expect(await screen.findByRole("button", { name: "Đăng nhập" })).toBeInTheDocument();
    expect(screen.queryByText(`Trả lời ${MARK}`)).not.toBeInTheDocument();
  });
});

describe("return path after an expired session", () => {
  async function adminOnUsersPageThenExpires(user: ReturnType<typeof userEvent.setup>) {
    await signIn(user, users.admin.email);
    await user.click(await screen.findByRole("link", { name: "Người dùng" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Người dùng" })).toBeInTheDocument();
    window.dispatchEvent(new CustomEvent("auth:expired"));
    expect(await screen.findByRole("button", { name: "Đăng nhập" })).toBeInTheDocument();
  }

  it("brings the same user back to the page they were on", async () => {
    const { user } = setup();
    await adminOnUsersPageThenExpires(user);
    await signIn(user, users.admin.email);
    expect(await screen.findByRole("heading", { level: 1, name: "Người dùng" })).toBeInTheDocument();
  });

  it("sends another user to the home page, not to the expired session's page", async () => {
    const { user, releaseStaff } = setup();
    releaseStaff();
    await adminOnUsersPageThenExpires(user);
    await signIn(user, users.staff.email);
    expect(await screen.findByRole("button", { name: "Cuộc trò chuyện mới" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Bạn không có quyền xem trang này" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Người dùng" })).not.toBeInTheDocument();
  });
});
