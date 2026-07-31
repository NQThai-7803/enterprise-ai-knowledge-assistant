import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

type Role = "ADMIN" | "MANAGER" | "STAFF";

interface LoginResponse {
  data: {
    access_token: string;
    refresh_token: string;
    user: {
      id: string;
      email: string;
      full_name: string;
      role: Role;
      department_id: string | null;
      is_active: boolean;
    };
  };
}

interface ListResponse<T> {
  data: T[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

interface DataResponse<T> {
  data: T;
}

interface Department {
  id: string;
  name: string;
  code: string;
}

interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  department_id: string | null;
  is_active: boolean;
}

interface DocumentStatus {
  id: string;
  status: "UPLOADED" | "PROCESSING" | "READY" | "FAILED" | "ARCHIVED";
  error_message: string | null;
}

const apiBaseUrl = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000";
const screenshotsDir = resolve(process.cwd(), "..", "artifacts", "uat", "screenshots");
const uniqueSuffix = `${Date.now()}`;

const accounts = {
  admin: {
    email: process.env.UAT_ADMIN_EMAIL ?? "admin.uat@example.test",
    password: requiredEnv("UAT_ADMIN_PASSWORD"),
  },
  manager: {
    email: process.env.UAT_MANAGER_EMAIL ?? "manager.uat@example.test",
    password: requiredEnv("UAT_MANAGER_PASSWORD"),
  },
  staff: {
    email: process.env.UAT_STAFF_EMAIL ?? "staff.uat@example.test",
    password: requiredEnv("UAT_STAFF_PASSWORD"),
  },
};

let knowledgeDepartment: Department;
let managerUser: User;
let adminAccessToken = "";
const browserIssuesByPage = new WeakMap<Page, string[]>();
const expectedAuth401ByPage = new WeakSet<Page>();
const expectedConflictByPage = new WeakSet<Page>();
const expectedUploadErrorByPage = new WeakSet<Page>();
const expectedMutationAbortByPage = new WeakSet<Page>();

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ playwright }) => {
  if (process.env.E2E_LIVE !== "true") {
    throw new Error("Set E2E_LIVE=true to run live acceptance tests.");
  }
  await mkdir(screenshotsDir, { recursive: true });

  const api = await playwright.request.newContext({ baseURL: apiBaseUrl });
  try {
    const health = await api.get("/health/ready");
    expect(health.ok()).toBeTruthy();
    adminAccessToken = await loginViaApi(api, accounts.admin.email, accounts.admin.password);
    await loginViaApi(api, accounts.manager.email, accounts.manager.password);
    await loginViaApi(api, accounts.staff.email, accounts.staff.password);
    knowledgeDepartment = await findDepartment(api, adminAccessToken, "UAT-KNOWLEDGE");
    managerUser = await findUser(api, adminAccessToken, accounts.manager.email);
    await findUser(api, adminAccessToken, accounts.staff.email);
  } finally {
    await api.dispose();
  }
});

test.beforeEach(async ({ page }) => {
  const browserIssues: string[] = [];
  browserIssuesByPage.set(page, browserIssues);
  page.on("console", (message) => {
    if (message.type() === "error") {
      const text = message.text();
      const locationUrl = message.location().url;
      const expectedAuth401 =
        /Failed to load resource: the server responded with a status of 401/.test(text) &&
        (expectedAuth401ByPage.has(page) || /\/api\/v1\/auth\/(me|refresh)/.test(locationUrl) || locationUrl === "");
      const expectedConflict409 =
        expectedConflictByPage.has(page) && /Failed to load resource: the server responded with a status of 409/.test(text);
      const expectedInvalidUpload =
        expectedUploadErrorByPage.has(page) &&
        /Failed to load resource: the server responded with a status of (400|413|415)/.test(text);
      if (!expectedAuth401 && !expectedConflict409 && !expectedInvalidUpload) {
        browserIssues.push(text);
      }
    }
  });
  page.on("pageerror", (error) => browserIssues.push(error.message));
  page.on("requestfailed", (request) => {
    const failure = request.failure();
    const errorText = failure?.errorText ?? "request failed";
    const url = request.url();
    const expectedStreamAbort = url.includes("/messages/stream") && /abort|ERR_ABORTED/i.test(errorText);
    const expectedLogoutAbort = url.includes("/api/v1/auth/logout") && /abort|ERR_ABORTED/i.test(errorText);
    const expectedMutationAbort =
      expectedMutationAbortByPage.has(page) &&
      (/\/api\/v1\/(departments|users)\/[0-9a-f-]+$/i.test(url) ||
        /\/api\/v1\/documents\/[0-9a-f-]+\/permissions\/[0-9a-f-]+$/i.test(url)) &&
      /abort|ERR_ABORTED/i.test(errorText);
    if (!url.includes("/api/v1/auth/me") && !expectedStreamAbort && !expectedLogoutAbort && !expectedMutationAbort) {
      browserIssues.push(`${url} ${errorText}`);
    }
  });
});

test.afterEach(async ({ page }, testInfo) => {
  const browserIssues = browserIssuesByPage.get(page) ?? [];
  if (browserIssues.length > 0) {
    testInfo.annotations.push({ type: "browserIssues", description: browserIssues.join("\n") });
  }
  expect(browserIssues).toEqual([]);
});

test("live authentication, role navigation, direct route protection, and session expiry", async ({ page, request }) => {
  await loginThroughUi(page, accounts.admin.email, accounts.admin.password);
  await expect(page.getByRole("link", { name: "Users" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Departments" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Audit logs" })).toBeVisible();
  await expect(page.getByText(/API ready|API checking/)).toBeVisible();
  await logoutThroughUi(page);

  await loginThroughUi(page, accounts.manager.email, accounts.manager.password);
  await expect(page.getByRole("link", { name: "Feedback" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Users" })).toHaveCount(0);
  await page.goto("/users");
  await expect(page.getByRole("heading", { name: "Access denied" }).first()).toBeVisible();
  const managerAccessToken = await loginViaApi(request, accounts.manager.email, accounts.manager.password);
  const forbiddenUsers = await request.get(`${apiBaseUrl}/api/v1/users`, {
    headers: authHeaders(managerAccessToken),
  });
  expect(forbiddenUsers.status()).toBe(403);
  await page.getByRole("link", { name: "Return to chat" }).click();
  await expect(page.getByRole("heading", { name: "AI Chat workspace" }).first()).toBeVisible();

  await logoutThroughUi(page);
  await loginThroughUi(page, accounts.staff.email, accounts.staff.password);
  await expect(page.getByRole("link", { name: "Chat" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Documents" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Audit logs" })).toHaveCount(0);
  await page.goto("/audit-logs");
  await expect(page.getByRole("heading", { name: "Access denied" }).first()).toBeVisible();

  expectedAuth401ByPage.add(page);
  await page.addInitScript(() => {
    sessionStorage.setItem("enterprise_ai_access_token", "invalid-token");
    sessionStorage.setItem("enterprise_ai_refresh_token", "invalid-refresh-token");
  });
  await page.goto("/chat");
  await expect(page.getByRole("heading", { name: "Sign in" }).first()).toBeVisible();
});

test("live admin user and department management", async ({ page, request }) => {
  expectedConflictByPage.add(page);
  expectedMutationAbortByPage.add(page);
  await loginThroughUi(page, accounts.admin.email, accounts.admin.password);

  await page.getByRole("link", { name: "Departments" }).click();
  await expect(page.getByRole("heading", { name: "Department management" }).first()).toBeVisible();
  const departmentCode = `UAT-LIVE-${uniqueSuffix}`;
  const editedDepartmentCode = `UAT-LIVE-EDIT-${uniqueSuffix}`;
  await page.getByLabel("Name").fill(`UAT Live Department ${uniqueSuffix}`);
  await page.getByLabel("Code").fill(departmentCode);
  await page.getByLabel("Description").fill("Created by live Playwright UAT.");
  await page.getByRole("button", { name: "Create department" }).click();
  await page.getByLabel("Search").fill(departmentCode);
  await expect(page.getByText(departmentCode)).toBeVisible();
  await page.getByLabel("Name").fill(`UAT Live Duplicate ${uniqueSuffix}`);
  await page.getByLabel("Code").fill(departmentCode);
  await page.getByLabel("Description").fill("Duplicate conflict check.");
  await page.getByRole("button", { name: "Create department" }).click();
  await expect(page.getByText("Create department failed")).toBeVisible();
  await page.getByRole("button", { name: "Edit" }).first().click();
  await page.getByLabel("Edit name").fill(`UAT Live Department Edited ${uniqueSuffix}`);
  await page.getByLabel("Edit code").fill(editedDepartmentCode);
  await page.getByLabel("Edit description").fill("Edited by live Playwright UAT.");
  await page.getByRole("button", { name: "Update department" }).click();
  await page.getByLabel("Search").fill(editedDepartmentCode);
  await expect(page.getByText(editedDepartmentCode)).toBeVisible();
  await page.getByRole("button", { name: "Delete" }).first().click();
  await page.getByRole("button", { name: "Delete" }).last().click();
  await expect(page.getByText("Department deleted")).toBeVisible();

  await page.getByRole("link", { name: "Users" }).click();
  await expect(page.getByRole("heading", { name: "User management" }).first()).toBeVisible();
  const createdEmail = `uat.live.${uniqueSuffix}@example.test`;
  const createdPassword = `LiveUat!${uniqueSuffix}`;
  await page.getByLabel("Email").fill(createdEmail);
  await page.getByLabel("Full name").fill(`UAT Live User ${uniqueSuffix}`);
  await page.getByLabel("Temporary password").fill(createdPassword);
  await page.locator("#new-role").selectOption("STAFF");
  await page.getByLabel("Department ID").fill(knowledgeDepartment.id);
  await page.getByRole("button", { name: "Create user" }).click();
  await page.getByLabel("Search").fill(createdEmail);
  await expect(page.getByText(createdEmail)).toBeVisible();
  await page.getByLabel("Email").fill(createdEmail);
  await page.getByLabel("Full name").fill(`UAT Live Duplicate ${uniqueSuffix}`);
  await page.getByLabel("Temporary password").fill(createdPassword);
  await page.locator("#new-role").selectOption("STAFF");
  await page.getByLabel("Department ID").fill(knowledgeDepartment.id);
  await page.getByRole("button", { name: "Create user" }).click();
  await expect(page.getByText("Create user failed")).toBeVisible();
  await page.getByRole("button", { name: "Edit" }).first().click();
  await page.getByLabel("Edit full name").fill(`UAT Live User Edited ${uniqueSuffix}`);
  await page.getByRole("button", { name: "Update user" }).click();
  await expect(page.getByText(`UAT Live User Edited ${uniqueSuffix}`)).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await page.getByRole("button", { name: "Deactivate" }).first().click();
  await page.getByRole("button", { name: "Deactivate" }).last().click();
  await expect(page.getByText("INACTIVE")).toBeVisible();

  const inactiveLogin = await request.post(`${apiBaseUrl}/api/v1/auth/login`, {
    data: { email: createdEmail, password: createdPassword },
  });
  expect(inactiveLogin.status()).toBe(403);

  await page.getByRole("button", { name: "Reactivate" }).first().click();
  await expect(page.getByText("ACTIVE")).toBeVisible();
  const reactivatedLogin = await request.post(`${apiBaseUrl}/api/v1/auth/login`, {
    data: { email: createdEmail, password: createdPassword },
  });
  expect(reactivatedLogin.ok()).toBeTruthy();
});

test("live document upload, processing, permissions, and authorization", async ({ page, request }, testInfo) => {
  expectedMutationAbortByPage.add(page);
  await loginThroughUi(page, accounts.admin.email, accounts.admin.password);
  await page.getByRole("link", { name: "Documents" }).click();
  await page.getByRole("link", { name: "Upload PDF" }).click();

  const invalidPath = testInfo.outputPath(`uat-live-invalid-${uniqueSuffix}.txt`);
  await writeFile(invalidPath, "This is intentionally not a PDF.");
  expectedUploadErrorByPage.add(page);
  await page.getByLabel("Title").fill(`UAT Invalid Upload ${uniqueSuffix}`);
  await page.getByLabel("Description").fill("Live UAT invalid upload check.");
  await page.getByLabel("Access scope").selectOption("PRIVATE");
  await page.locator('input[type="file"]').setInputFiles(invalidPath);
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByRole("alert")).toContainText("Only PDF files are supported.");

  const pdfPath = testInfo.outputPath(`uat-live-${uniqueSuffix}.pdf`);
  await writeFile(pdfPath, buildPdf(`UAT live upload policy ${uniqueSuffix} requires review and safe processing.`));
  const title = `UAT Live Upload ${uniqueSuffix}`;
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Description").fill("Live UAT upload through the browser.");
  await page.getByLabel("Access scope").selectOption("PRIVATE");
  await page.locator('input[type="file"]').setInputFiles(pdfPath);
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByRole("heading", { name: title }).first()).toBeVisible();

  const documentId = page.url().split("/documents/")[1]?.split("/")[0];
  expect(documentId).toBeTruthy();
  await expect.poll(
    async () => {
      const statusResponse = await request.get(`${apiBaseUrl}/api/v1/documents/${documentId}/status`, {
        headers: authHeaders(adminAccessToken),
      });
      const statusJson = (await statusResponse.json()) as DataResponse<DocumentStatus>;
      return statusJson.data.status;
    },
    { timeout: 180_000, intervals: [2_000, 5_000, 10_000] },
  ).toBe("READY");
  await page.reload();
  await expect(page.getByText("READY").first()).toBeVisible();

  await page.getByRole("link", { name: "Permissions" }).click();
  await page.getByLabel("Grantee type").selectOption("user");
  await page.getByLabel("Grantee ID").fill(managerUser.id);
  await page.getByLabel("Permission").selectOption("VIEW");
  await page.getByRole("button", { name: "Grant" }).click();
  await expect(page.getByText(`User ${managerUser.id}`)).toBeVisible();
  await page.getByLabel("Grantee ID").fill(managerUser.id);
  await page.getByLabel("Permission").selectOption("VIEW");
  await expect(page.getByText("This exact direct grant already exists.")).toBeVisible();

  await logoutThroughUi(page);
  await loginThroughUi(page, accounts.manager.email, accounts.manager.password);
  await page.goto(`/documents/${documentId}`);
  await expect(page.getByRole("heading", { name: title }).first()).toBeVisible();

  await logoutThroughUi(page);
  await loginThroughUi(page, accounts.admin.email, accounts.admin.password);
  await page.goto(`/documents/${documentId}/permissions`);
  await page.getByRole("button", { name: "Revoke" }).first().click();
  await page.getByRole("button", { name: "Revoke" }).last().click();
  await expect(page.getByText("No direct permissions")).toBeVisible();

  const managerAccessToken = await loginViaApi(request, accounts.manager.email, accounts.manager.password);
  const revokedAccess = await request.get(`${apiBaseUrl}/api/v1/documents/${documentId}`, {
    headers: authHeaders(managerAccessToken),
  });
  expect(revokedAccess.status()).toBe(404);
});

test("live staff chat SSE, citations, feedback, audit visibility, and system status", async ({ page }) => {
  let streamHeaders: Record<string, string> | null = null;
  page.on("response", async (response) => {
    if (response.url().includes("/messages/stream")) {
      streamHeaders = await response.allHeaders();
    }
  });

  await loginThroughUi(page, accounts.staff.email, accounts.staff.password);
  await expect(page.getByRole("heading", { name: "AI Chat workspace" }).first()).toBeVisible();
  await page.getByRole("button", { name: "New session" }).click();
  await page.getByLabel("Message").fill(
    "According to the UAT travel approval policy, what approval is required before booking travel?",
  );
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Generating and validating citations")).toBeVisible();
  await expect(page.getByText(/manager approval before booking travel/i).first()).toBeVisible({ timeout: 120_000 });
  await expect(page.getByText(/UAT Grounding Handbook|UAT Shared Knowledge Policy/)).toBeVisible();
  await expect(page.getByText("Page 1").first()).toBeVisible();
  expect(streamHeaders?.["content-type"]).toContain("text/event-stream");
  expect(streamHeaders?.["content-length"]).toBeUndefined();
  expect(page.url()).not.toContain("token");

  await page.getByLabel("Mark answer helpful").last().click();
  await expect(page.getByText("Feedback saved")).toBeVisible();

  await logoutThroughUi(page);
  await loginThroughUi(page, accounts.admin.email, accounts.admin.password);
  await page.getByRole("link", { name: "Feedback" }).click();
  await expect(page.getByRole("heading", { name: "Feedback management" }).first()).toBeVisible();
  await expect(page.getByText(/HELPFUL|NOT_HELPFUL/).first()).toBeVisible();
  await page.getByRole("link", { name: "Audit logs" }).click();
  await expect(page.getByRole("heading", { name: "Audit log explorer" }).first()).toBeVisible();
  await expect(page.getByText(/CHAT_|AUTH_|DOCUMENT_/).first()).toBeVisible();
  await page.getByRole("link", { name: "System status" }).click();
  await expect(page.getByText("API live")).toBeVisible();
  await expect(page.getByText("PostgreSQL")).toBeVisible();
  await expect(page.getByText("Redis")).toBeVisible();
  await expect(page.getByText("Not exposed by current backend API")).toBeVisible();
});

test("live responsive, keyboard, reduced-motion, and cancellation smoke", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await loginThroughUi(page, accounts.staff.email, accounts.staff.password);
  await page.screenshot({ path: resolve(screenshotsDir, "390x844-chat.png"), fullPage: true });
  await expectNoHorizontalOverflow(page);
  await page.getByRole("button", { name: "Open navigation" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  await page.keyboard.press("Escape");

  await page.getByLabel("Message").fill("Cancel this UAT stream after it starts.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("button", { name: "Stop" })).toBeVisible();
  await page.getByRole("button", { name: "Stop" }).click();
  await expect(page.getByText("STREAM_CANCELLED")).toBeVisible();
  await expect(page.getByRole("button", { name: "Send" })).toBeVisible();

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1366, height: 768 },
    { width: 1024, height: 768 },
    { width: 768, height: 1024 },
    { width: 360, height: 800 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "Document library" }).first()).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.screenshot({
      path: resolve(screenshotsDir, `${viewport.width}x${viewport.height}-documents.png`),
      fullPage: true,
    });
  }
});

async function loginThroughUi(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByRole("heading", { name: /AI Chat workspace|Document library|Document detail|Access denied/ }).first(),
  ).toBeVisible({ timeout: 30_000 });
  if (await page.getByRole("heading", { name: "Access denied" }).first().isVisible()) {
    await page.getByRole("link", { name: "Return to chat" }).click();
    await expect(page.getByRole("heading", { name: "AI Chat workspace" }).first()).toBeVisible();
  }
}

async function logoutThroughUi(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" }).first()).toBeVisible();
}


async function loginViaApi(
  request: APIRequestContext,
  email: string,
  password: string,
): Promise<string> {
  const response = await request.post(`${apiBaseUrl}/api/v1/auth/login`, {
    data: { email, password },
  });
  expect(response.ok()).toBeTruthy();
  const payload = (await response.json()) as LoginResponse;
  return payload.data.access_token;
}

async function findDepartment(
  request: APIRequestContext,
  token: string,
  code: string,
): Promise<Department> {
  const response = await request.get(`${apiBaseUrl}/api/v1/departments`, {
    headers: authHeaders(token),
    params: { search: code, page_size: 10 },
  });
  expect(response.ok()).toBeTruthy();
  const payload = (await response.json()) as ListResponse<Department>;
  const department = payload.data.find((item) => item.code === code);
  if (!department) {
    throw new Error(`Missing seeded department ${code}.`);
  }
  return department;
}

async function findUser(request: APIRequestContext, token: string, email: string): Promise<User> {
  const response = await request.get(`${apiBaseUrl}/api/v1/users`, {
    headers: authHeaders(token),
    params: { search: email, page_size: 10 },
  });
  expect(response.ok()).toBeTruthy();
  const payload = (await response.json()) as ListResponse<User>;
  const user = payload.data.find((item) => item.email === email);
  if (!user) {
    throw new Error(`Missing seeded user ${email}.`);
  }
  return user;
}

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required for live acceptance tests.`);
  }
  return value;
}

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 2);
}

function buildPdf(text: string): Buffer {
  const safeText = text
    .replaceAll("\\", "\\\\")
    .replaceAll("(", "\\(")
    .replaceAll(")", "\\)")
    .replaceAll("\r", " ")
    .replaceAll("\n", " ");
  const stream = `BT\n/F1 12 Tf\n72 720 Td\n(${safeText}) Tj\nET\n`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${Buffer.byteLength(stream, "utf8")} >>\nstream\n${stream}endstream`,
  ];
  let body = "%PDF-1.4\n";
  const offsets = [0];
  for (const [index, object] of objects.entries()) {
    offsets.push(Buffer.byteLength(body, "utf8"));
    body += `${index + 1} 0 obj\n${object}\nendobj\n`;
  }
  const xrefOffset = Buffer.byteLength(body, "utf8");
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1)) {
    body += `${String(offset).padStart(10, "0")} 00000 n \n`;
  }
  body += `trailer\n<< /Root 1 0 R /Size ${objects.length + 1} >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  return Buffer.from(body, "utf8");
}


