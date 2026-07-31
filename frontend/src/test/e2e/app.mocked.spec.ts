import { expect, type Page, test } from "@playwright/test";

type Role = "ADMIN" | "MANAGER" | "STAFF";

async function authenticatedPage(page: Page, role: Role = "ADMIN") {
  await page.addInitScript(() => {
    sessionStorage.setItem("enterprise_ai_access_token", "test-access-token");
    sessionStorage.setItem("enterprise_ai_refresh_token", "test-refresh-token");
  });
  await page.route("**/health/live", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route("**/health/ready", (route) =>
    route.fulfill({ json: { status: "ready", checks: { database: "ok", redis: "ok" } } }),
  );
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      json: {
        data: {
          id: `${role.toLowerCase()}-1`,
          email: `${role.toLowerCase()}@example.com`,
          full_name: `${role} User`,
          role,
          department_id: role === "STAFF" ? "dept-1" : null,
          is_active: true,
        },
        meta: null,
      },
    }),
  );
  await page.route("**/api/v1/auth/logout", (route) => route.fulfill({ status: 204, body: "" }));
}

async function mockChat(page: Page) {
  const sessions = {
    data: [
      {
        id: "s1",
        title: "Policy questions",
        is_archived: false,
        message_count: 0,
        created_at: "2026-07-29T00:00:00Z",
        updated_at: "2026-07-29T00:00:00Z",
      },
    ],
    meta: { page: 1, page_size: 50, total: 1, total_pages: 1 },
  };
  const session = {
    data: {
      id: "s1",
      title: "Policy questions",
      is_archived: false,
      created_at: "2026-07-29T00:00:00Z",
      updated_at: "2026-07-29T00:00:00Z",
      messages: [],
      message_pagination: { page: 1, page_size: 100, total: 0, total_pages: 0 },
    },
    meta: null,
  };

  await page.route("**/api/v1/chat/sessions?**", (route) => route.fulfill({ json: sessions }));
  await page.route("**/api/v1/chat/sessions/s1?**", (route) => route.fulfill({ json: session }));
  await page.route("**/api/v1/chat/sessions/s1/messages/stream", (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/event-stream; charset=utf-8",
      headers: {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
      },
      body: [
        'event: stream.started',
        'id: evt-1',
        'data: {"request_id":"req-1","session_id":"s1","provider":"test-provider","model":"test-model","strategy":"buffer_after_validation"}',
        '',
        'event: heartbeat',
        'id: evt-2',
        'data: {}',
        '',
        'event: message.delta',
        'id: evt-3',
        'data: {"sequence":1,"content":"Validated final answer"}',
        '',
        'event: citations.ready',
        'id: evt-4',
        'data: {"citations":[{"document_id":"doc-1","document_title":"Policy Handbook","chunk_id":"chunk-1","page_number":3,"excerpt":"Approved source excerpt","relevance_score":0.91,"citation_order":1}]}',
        '',
        'event: message.completed',
        'id: evt-5',
        'data: {"message_id":"m1","session_id":"s1","content":"Validated final answer","citations":[{"document_id":"doc-1","document_title":"Policy Handbook","chunk_id":"chunk-1","page_number":3,"excerpt":"Approved source excerpt","relevance_score":0.91,"citation_order":1}],"provider":"test-provider","model":"test-model","usage":null,"grounding_status":"ANSWERED","retrieved_chunk_count":1}',
        '',
        '',
      ].join("\n"),
    }),
  );
}

test("admin navigation exposes administrative routes", async ({ page }) => {
  await authenticatedPage(page, "ADMIN");
  await mockChat(page);
  await page.goto("/chat");

  await expect(page.getByRole("link", { name: "Users" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Departments" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Audit logs" })).toBeVisible();
});

test("staff navigation hides administrative routes", async ({ page }) => {
  await authenticatedPage(page, "STAFF");
  await mockChat(page);
  await page.goto("/chat");

  await expect(page.getByRole("link", { name: "Chat" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Users" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Audit logs" })).toHaveCount(0);
});


test("mobile navigation closes with Escape and does not block composer", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await authenticatedPage(page, "STAFF");
  await mockChat(page);
  await page.goto("/chat");

  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toHaveCount(0);

  await page.getByLabel("Message").fill("What is the policy?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Validated final answer")).toBeVisible();
});
test("chat renders completed SSE answer and citations", async ({ page }) => {
  await authenticatedPage(page, "STAFF");
  await mockChat(page);
  await page.goto("/chat");

  await page.getByLabel("Message").fill("What is the policy?");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Validated final answer")).toBeVisible();
  await expect(page.getByText("Policy Handbook")).toBeVisible();
  await expect(page.getByText("Approved source excerpt")).toBeVisible();
  await expect(page.getByLabel("Mark answer helpful")).toBeVisible();
});
async function mockUsersApi(page: Page) {
  const now = "2026-07-30T00:00:00Z";
  let users: Array<{
    id: string;
    email: string;
    full_name: string;
    role: Role;
    department_id: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
  }> = [
    {
      id: "staff-1",
      email: "staff.admin-ui@example.test",
      full_name: "Admin UI Staff",
      role: "STAFF",
      department_id: "dept-1",
      is_active: true,
      created_at: now,
      updated_at: now,
    },
  ];

  await page.route("**/api/v1/users**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (url.pathname === "/api/v1/users" && request.method() === "GET") {
      const search = url.searchParams.get("search")?.toLowerCase() ?? "";
      const rows = users.filter(
        (user) => !search || user.email.includes(search) || user.full_name.toLowerCase().includes(search),
      );
      return route.fulfill({
        json: {
          data: rows,
          meta: { page: 1, page_size: 20, total: rows.length, total_pages: rows.length ? 1 : 0 },
        },
      });
    }

    if (url.pathname === "/api/v1/users" && request.method() === "POST") {
      const payload = request.postDataJSON() as {
        email: string;
        full_name: string;
        role: Role;
        department_id: string | null;
      };
      if (users.some((user) => user.email === payload.email)) {
        return route.fulfill({
          status: 409,
          json: { error: { code: "USER_EMAIL_ALREADY_EXISTS", message: "Email is already in use.", details: null, request_id: "req-user-conflict" } },
        });
      }
      const created = {
        id: `user-${users.length + 1}`,
        email: payload.email,
        full_name: payload.full_name,
        role: payload.role,
        department_id: payload.department_id,
        is_active: true,
        created_at: now,
        updated_at: now,
      };
      users = [created, ...users];
      return route.fulfill({ status: 201, json: { data: created, meta: null } });
    }

    if (url.pathname.startsWith("/api/v1/users/")) {
      const userId = url.pathname.split("/users/")[1];
      const existing = users.find((user) => user.id === userId);
      if (!existing) {
        return route.fulfill({ status: 404, json: { error: { code: "RESOURCE_NOT_FOUND", message: "Not found.", details: null, request_id: "req-user-missing" } } });
      }
      if (request.method() === "DELETE") {
        existing.is_active = false;
        existing.updated_at = now;
        return route.fulfill({ status: 204, body: "" });
      }
      if (request.method() === "PATCH") {
        const payload = request.postDataJSON() as Partial<typeof existing>;
        Object.assign(existing, payload, { updated_at: now });
        return route.fulfill({ json: { data: existing, meta: null } });
      }
    }

    return route.fallback();
  });
}
async function mockDepartmentsApi(page: Page) {
  const now = "2026-07-30T00:00:00Z";
  let departments: Array<{
    id: string;
    name: string;
    code: string;
    description: string | null;
    created_at: string;
  }> = [
    {
      id: "dept-1",
      name: "Knowledge Operations",
      code: "KNOWLEDGE",
      description: "Seeded department.",
      created_at: now,
    },
  ];

  await page.route("**/api/v1/departments**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (url.pathname === "/api/v1/departments" && request.method() === "GET") {
      const search = url.searchParams.get("search")?.toLowerCase() ?? "";
      const rows = departments.filter(
        (department) => !search || department.code.toLowerCase().includes(search) || department.name.toLowerCase().includes(search),
      );
      return route.fulfill({
        json: {
          data: rows,
          meta: { page: 1, page_size: 20, total: rows.length, total_pages: rows.length ? 1 : 0 },
        },
      });
    }

    if (url.pathname === "/api/v1/departments" && request.method() === "POST") {
      const payload = request.postDataJSON() as { name: string; code: string; description: string | null };
      if (departments.some((department) => department.code === payload.code)) {
        return route.fulfill({
          status: 409,
          json: { error: { code: "DEPARTMENT_CODE_ALREADY_EXISTS", message: "Department code already exists.", details: null, request_id: "req-dept-conflict" } },
        });
      }
      const created = {
        id: `dept-${departments.length + 1}`,
        name: payload.name,
        code: payload.code,
        description: payload.description,
        created_at: now,
      };
      departments = [created, ...departments];
      return route.fulfill({ status: 201, json: { data: created, meta: null } });
    }

    if (url.pathname.startsWith("/api/v1/departments/")) {
      const departmentId = url.pathname.split("/departments/")[1];
      const existing = departments.find((department) => department.id === departmentId);
      if (!existing) {
        return route.fulfill({ status: 404, json: { error: { code: "RESOURCE_NOT_FOUND", message: "Not found.", details: null, request_id: "req-dept-missing" } } });
      }
      if (request.method() === "PATCH") {
        const payload = request.postDataJSON() as Partial<typeof existing>;
        Object.assign(existing, payload);
        return route.fulfill({ json: { data: existing, meta: null } });
      }
      if (request.method() === "DELETE") {
        departments = departments.filter((department) => department.id !== departmentId);
        return route.fulfill({ status: 204, body: "" });
      }
    }

    return route.fallback();
  });
}
test("admin user management supports conflict, edit, deactivate, and reactivate", async ({ page }) => {
  await authenticatedPage(page, "ADMIN");
  await mockUsersApi(page);
  await page.goto("/users");

  await page.getByLabel("Email").fill("staff.admin-ui@example.test");
  await page.getByLabel("Full name").fill("Duplicate Staff");
  await page.getByLabel("Temporary password").fill("MockPassword123!");
  await page.locator("#new-role").selectOption("STAFF");
  await page.getByLabel("Department ID").fill("dept-1");
  await page.getByRole("button", { name: "Create user" }).click();
  await expect(page.getByText("Create user failed")).toBeVisible();

  await page.getByRole("button", { name: "Edit" }).first().click();
  await page.getByLabel("Edit full name").fill("Edited Admin UI Staff");
  await page.getByRole("button", { name: "Update user" }).click();
  await expect(page.getByText("Edited Admin UI Staff")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();

  await page.getByRole("button", { name: "Deactivate" }).first().click();
  await page.getByRole("button", { name: "Deactivate" }).last().click();
  await expect(page.getByText("INACTIVE")).toBeVisible();
  await page.getByRole("button", { name: "Reactivate" }).first().click();
  await expect(page.getByText("ACTIVE")).toBeVisible();
});

test("admin department management supports conflict, edit, and delete", async ({ page }) => {
  await authenticatedPage(page, "ADMIN");
  await mockDepartmentsApi(page);
  await page.goto("/departments");

  await page.getByLabel("Name").fill("Duplicate Knowledge");
  await page.getByLabel("Code").fill("KNOWLEDGE");
  await page.getByLabel("Description").fill("Duplicate department.");
  await page.getByRole("button", { name: "Create department" }).click();
  await expect(page.getByText("Create department failed")).toBeVisible();
  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

  await authenticatedPage(page, "ADMIN");
  await page.goto("/departments");
  await page.getByRole("button", { name: "Edit" }).first().click();
  await page.getByLabel("Edit name").fill("Edited Knowledge Operations");
  await page.getByLabel("Edit code").fill("KNOWLEDGE-EDIT");
  await page.getByRole("button", { name: "Update department" }).click();
  await expect(page.getByText("KNOWLEDGE-EDIT")).toBeVisible();

  await page.getByRole("button", { name: "Delete" }).first().click();
  await page.getByRole("button", { name: "Delete" }).last().click();
  await expect(page.getByText("Department deleted")).toBeVisible();
});