import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

/**
 * Live acceptance of the flows smoke.spec.ts does not cover, ported to the redesigned Vietnamese UI:
 * role navigation and route protection, session expiry, admin user and department management,
 * document processing and direct permissions, SSE headers and feedback, mobile, keyboard,
 * reduced motion, cancellation and responsive layouts. Chat answers, citations, preview, the upload
 * form, names, audit filtering and system status live in smoke.spec.ts.
 * Run: E2E_LIVE=true UAT_*_PASSWORD=… PLAYWRIGHT_BASE_URL=… E2E_API_BASE_URL=…
 *      npx playwright test -c playwright.live.config.ts live-acceptance --workers=1
 */
test.use({ trace: "off", screenshot: "off", video: "off" });

type Role = "ADMIN" | "MANAGER" | "STAFF";
type Account = { email: string; password: string };

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
}

const apiBaseUrl = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000";
const screenshotsDir = resolve(process.cwd(), "..", "artifacts", "uat", "screenshots");
const uniqueSuffix = `${Date.now()}`;
// Public dev item ND-001 of tests/acceptance/natural_dev_v1.yaml (never a held-out question).
const question = process.env.SMOKE_ANSWERABLE_QUESTION ?? "Tổng thời gian nghỉ lễ là bao nhiêu ngày trong một năm?";

let accounts: { admin: Account; manager: Account; staff: Account };
let knowledgeDepartment: Department;
let managerUser: User;
let adminAccessToken = "";
const browserIssuesByPage = new WeakMap<Page, string[]>();
const expectedAuth401ByPage = new WeakSet<Page>();
const expectedConflictByPage = new WeakSet<Page>();

test.beforeAll(async ({ playwright }) => {
  if (process.env.E2E_LIVE !== "true") {
    throw new Error("Set E2E_LIVE=true to run live acceptance tests.");
  }
  accounts = {
    admin: { email: process.env.UAT_ADMIN_EMAIL ?? "admin.uat@example.test", password: requiredEnv("UAT_ADMIN_PASSWORD") },
    manager: { email: process.env.UAT_MANAGER_EMAIL ?? "manager.uat@example.test", password: requiredEnv("UAT_MANAGER_PASSWORD") },
    staff: { email: process.env.UAT_STAFF_EMAIL ?? "staff.uat@example.test", password: requiredEnv("UAT_STAFF_PASSWORD") },
  };
  await mkdir(screenshotsDir, { recursive: true });

  const api = await playwright.request.newContext({ baseURL: apiBaseUrl });
  try {
    expect((await api.get("/health/ready")).ok()).toBeTruthy();
    adminAccessToken = await loginViaApi(api, accounts.admin);
    knowledgeDepartment = await findDepartment(api, adminAccessToken, "UAT-KNOWLEDGE");
    managerUser = await findUser(api, adminAccessToken, accounts.manager.email);
  } finally {
    await api.dispose();
  }
});

test.beforeEach(async ({ page }) => {
  const browserIssues: string[] = [];
  browserIssuesByPage.set(page, browserIssues);
  page.on("console", (message) => {
    if (message.type() !== "error") {
      return;
    }
    const text = message.text();
    const locationUrl = message.location().url;
    const expectedAuth401 =
      /status of 401/.test(text) &&
      (expectedAuth401ByPage.has(page) || /\/api\/v1\/auth\/(me|refresh)/.test(locationUrl) || locationUrl === "");
    const expectedConflict409 = expectedConflictByPage.has(page) && /status of 409/.test(text);
    if (!expectedAuth401 && !expectedConflict409) {
      browserIssues.push(text);
    }
  });
  page.on("pageerror", (error) => browserIssues.push(error.message));
  page.on("requestfailed", (request) => {
    const errorText = request.failure()?.errorText ?? "request failed";
    const url = request.url();
    const expectedAbort =
      /abort|ERR_ABORTED/i.test(errorText) &&
      (url.includes("/messages/stream") ||
        url.includes("/api/v1/auth/logout") ||
        /\/api\/v1\/(departments|users)\/[0-9a-f-]+$/i.test(url) ||
        /\/api\/v1\/documents\/[0-9a-f-]+\/permissions\/[0-9a-f-]+$/i.test(url));
    if (!url.includes("/api/v1/auth/me") && !expectedAbort) {
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

test("role navigation, direct route protection and session expiry", async ({ page, request }) => {
  await loginThroughUi(page, accounts.admin);
  await expect(page.getByRole("link", { name: "Người dùng", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Phòng ban", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Nhật ký hệ thống", exact: true })).toBeVisible();
  await expect(page.getByText(/API sẵn sàng|Đang kiểm tra API/)).toBeVisible();
  await logoutThroughUi(page);

  await loginThroughUi(page, accounts.manager);
  await expect(page.getByRole("link", { name: "Phản hồi", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Người dùng", exact: true })).toHaveCount(0);
  await page.goto("/users");
  await expect(page.getByRole("heading", { name: "Bạn không có quyền xem trang này" })).toBeVisible();
  const managerAccessToken = await loginViaApi(request, accounts.manager);
  expect((await request.get(`${apiBaseUrl}/api/v1/users`, { headers: authHeaders(managerAccessToken) })).status()).toBe(403);
  await page.getByRole("link", { name: "Về trang Trò chuyện" }).click();
  await expect(page).toHaveURL(/\/chat$/);
  await logoutThroughUi(page);

  await loginThroughUi(page, accounts.staff);
  await expect(page.getByRole("link", { name: "Trò chuyện", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Tài liệu", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Nhật ký hệ thống", exact: true })).toHaveCount(0);
  await page.goto("/audit-logs");
  await expect(page.getByRole("heading", { name: "Bạn không có quyền xem trang này" })).toBeVisible();

  // An expired or forged session falls back to the sign-in page.
  expectedAuth401ByPage.add(page);
  await page.addInitScript(() => {
    sessionStorage.setItem("enterprise_ai_access_token", "invalid-token");
    sessionStorage.setItem("enterprise_ai_refresh_token", "invalid-refresh-token");
  });
  await page.goto("/chat");
  await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
});

test("admin department and user management", async ({ page, request }) => {
  expectedConflictByPage.add(page);
  await loginThroughUi(page, accounts.admin);

  await page.getByRole("link", { name: "Phòng ban", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Phòng ban" })).toBeVisible();
  const departmentCode = `UAT-LIVE-${uniqueSuffix}`;
  const editedDepartmentCode = `UAT-LIVE-EDIT-${uniqueSuffix}`;
  await fillDepartment(page, `UAT Live Department ${uniqueSuffix}`, departmentCode, "Created by live Playwright UAT.");
  await page.getByRole("button", { name: "Tạo phòng ban" }).click();
  await page.getByLabel("Tìm kiếm").fill(departmentCode);
  await expect(page.getByText(departmentCode, { exact: true })).toBeVisible();
  await fillDepartment(page, `UAT Live Duplicate ${uniqueSuffix}`, departmentCode, "Duplicate conflict check.");
  await page.getByRole("button", { name: "Tạo phòng ban" }).click();
  await expect(page.getByText("Tạo phòng ban thất bại")).toBeVisible();
  // Act only on the row this test created: list search may return other rows too.
  const departmentRow = (code: string) => page.getByRole("row").filter({ hasText: code });
  await departmentRow(departmentCode).getByRole("button", { name: "Sửa", exact: true }).click();
  await fillDepartment(page, `UAT Live Department Edited ${uniqueSuffix}`, editedDepartmentCode, "Edited by live Playwright UAT.");
  await page.getByRole("button", { name: "Lưu thay đổi" }).click();
  await page.getByLabel("Tìm kiếm").fill(editedDepartmentCode);
  await expect(page.getByText(editedDepartmentCode, { exact: true })).toBeVisible();
  await departmentRow(editedDepartmentCode).getByRole("button", { name: "Xóa", exact: true }).click();
  await page.getByRole("dialog", { name: "Xóa phòng ban?" }).getByRole("button", { name: "Xóa" }).click();
  await expect(page.getByText("Đã xóa phòng ban")).toBeVisible();

  await page.getByRole("link", { name: "Người dùng", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Người dùng" })).toBeVisible();
  const createdEmail = `uat.live.${uniqueSuffix}@example.test`;
  const createdPassword = `LiveUat!${uniqueSuffix}`;
  await createUserThroughDrawer(page, createdEmail, `UAT Live User ${uniqueSuffix}`, createdPassword);
  await page.getByLabel("Tìm kiếm").fill(createdEmail);
  await expect(page.getByText(createdEmail, { exact: true })).toBeVisible();

  await createUserThroughDrawer(page, createdEmail, `UAT Live Duplicate ${uniqueSuffix}`, createdPassword);
  const createDrawer = page.getByRole("dialog", { name: "Tạo người dùng" });
  await expect(createDrawer.getByRole("alert")).toContainText("Email này đã được dùng.");
  await createDrawer.getByRole("button", { name: "Đóng" }).click();

  const userRow = () => page.getByRole("row").filter({ hasText: createdEmail });
  await userRow().getByRole("button", { name: "Sửa", exact: true }).click();
  const editDrawer = page.getByRole("dialog", { name: "Sửa người dùng" });
  await editDrawer.getByLabel("Họ tên").fill(`UAT Live User Edited ${uniqueSuffix}`);
  await editDrawer.getByRole("button", { name: "Lưu thay đổi" }).click();
  await expect(userRow()).toContainText(`UAT Live User Edited ${uniqueSuffix}`);

  await userRow().getByRole("button", { name: "Vô hiệu hóa", exact: true }).click();
  await page.getByRole("dialog", { name: "Vô hiệu hóa người dùng?" }).getByRole("button", { name: "Vô hiệu hóa" }).click();
  await expect(userRow()).toContainText("Đã vô hiệu hóa");
  const inactiveLogin = await request.post(`${apiBaseUrl}/api/v1/auth/login`, {
    data: { email: createdEmail, password: createdPassword },
  });
  expect(inactiveLogin.status()).toBe(403);

  await userRow().getByRole("button", { name: "Kích hoạt lại" }).click();
  await expect(userRow()).toContainText("Đang hoạt động");
  const reactivatedLogin = await request.post(`${apiBaseUrl}/api/v1/auth/login`, {
    data: { email: createdEmail, password: createdPassword },
  });
  expect(reactivatedLogin.ok()).toBeTruthy();
});

test("document processing, direct permissions and authorization", async ({ page, request }, testInfo) => {
  test.setTimeout(300_000);
  await loginThroughUi(page, accounts.admin);

  // The form refuses a non-PDF before any request (the valid form upload is covered by smoke.spec.ts).
  await page.goto("/documents/upload");
  const invalidPath = testInfo.outputPath(`uat-live-invalid-${uniqueSuffix}.txt`);
  await writeFile(invalidPath, "This is intentionally not a PDF.");
  await page.getByLabel("Tệp PDF", { exact: true }).setInputFiles(invalidPath);
  await page.getByLabel("Tiêu đề").fill(`UAT Invalid Upload ${uniqueSuffix}`);
  await page.getByRole("button", { name: "Tải lên" }).click();
  await expect(page.getByText("Chỉ nhận tệp PDF.")).toBeVisible();

  // The document under test is created through the API, then processed by the real worker.
  const title = `UAT Live Upload ${uniqueSuffix}`;
  const created = await request.post(`${apiBaseUrl}/api/v1/documents/upload`, {
    headers: authHeaders(adminAccessToken),
    multipart: {
      file: { name: `uat-live-${uniqueSuffix}.pdf`, mimeType: "application/pdf", buffer: buildPdf(`UAT live upload ${uniqueSuffix} for permissions.`) },
      title,
      access_scope: "PRIVATE",
    },
  });
  expect(created.status()).toBe(202);
  const documentId = ((await created.json()) as { data: { id: string } }).data.id;
  try {
    await expect
      .poll(
        async () => {
          const status = await request.get(`${apiBaseUrl}/api/v1/documents/${documentId}/status`, {
            headers: authHeaders(adminAccessToken),
          });
          return ((await status.json()) as { data: { status: string } }).data.status;
        },
        { timeout: 180_000, intervals: [2_000, 5_000, 10_000] },
      )
      .toBe("READY");
    await page.goto(`/documents/${documentId}`);
    await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
    await expect(page.getByText("Sẵn sàng", { exact: true }).first()).toBeVisible();

    await page.getByRole("link", { name: "Phân quyền" }).click();
    await page.getByLabel("Chọn người dùng").selectOption(managerUser.id);
    await page.getByLabel("Quyền", { exact: true }).selectOption("VIEW");
    await page.getByRole("button", { name: "Cấp quyền" }).click();
    await expect(page.getByRole("cell", { name: managerUser.full_name })).toBeVisible();
    await page.getByLabel("Chọn người dùng").selectOption(managerUser.id);
    await expect(page.getByText("Quyền này đã tồn tại.")).toBeVisible();

    await logoutThroughUi(page);
    await loginThroughUi(page, accounts.manager);
    await page.goto(`/documents/${documentId}`);
    await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();

    await logoutThroughUi(page);
    await loginThroughUi(page, accounts.admin);
    await page.goto(`/documents/${documentId}/permissions`);
    await page.getByRole("row").filter({ hasText: managerUser.full_name }).getByRole("button", { name: "Thu hồi" }).click();
    await page.getByRole("dialog", { name: "Thu hồi quyền này?" }).getByRole("button", { name: "Thu hồi" }).click();
    await expect(page.getByText("Chưa có quyền cấp trực tiếp nào.")).toBeVisible();

    const managerAccessToken = await loginViaApi(request, accounts.manager);
    const revoked = await request.get(`${apiBaseUrl}/api/v1/documents/${documentId}`, {
      headers: authHeaders(managerAccessToken),
    });
    expect(revoked.status()).toBe(404);
  } finally {
    await request.delete(`${apiBaseUrl}/api/v1/documents/${documentId}`, { headers: authHeaders(adminAccessToken) });
  }
});

test("chat streams as text/event-stream, feedback reaches the admin report", async ({ page }) => {
  test.setTimeout(420_000);
  let streamHeaders: Record<string, string> | null = null;
  page.on("response", async (response) => {
    if (response.url().includes("/messages/stream")) {
      streamHeaders = await response.allHeaders();
    }
  });

  await loginThroughUi(page, accounts.staff);
  await page.getByRole("button", { name: "Cuộc trò chuyện mới", exact: true }).click();
  await expect(page.getByText("Chưa có tin nhắn")).toBeVisible();
  await page.getByLabel("Câu hỏi", { exact: true }).fill(question);
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  const answer = page.locator('section[aria-label="Cuộc trò chuyện"] article').first();
  await expect(answer).toBeVisible({ timeout: 300_000 });
  expect(streamHeaders?.["content-type"]).toContain("text/event-stream");
  expect(streamHeaders?.["content-length"]).toBeUndefined();
  expect(page.url()).not.toContain("token");

  await answer.getByRole("button", { name: "Câu trả lời hữu ích" }).click();
  await expect(page.getByText("Đã lưu đánh giá")).toBeVisible();

  await logoutThroughUi(page);
  await loginThroughUi(page, accounts.admin);
  await page.getByRole("link", { name: "Phản hồi", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Phản hồi câu trả lời" })).toBeVisible();
  await expect(page.locator("li").filter({ hasText: "Hữu ích" }).first()).toBeVisible();
});

test("mobile, keyboard, reduced motion, cancellation and responsive layouts", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await loginThroughUi(page, accounts.staff);
  await page.screenshot({ path: resolve(screenshotsDir, "390x844-chat.png"), fullPage: true });
  await expectNoHorizontalOverflow(page);
  await page.getByRole("button", { name: "Mở điều hướng" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("navigation", { name: "Điều hướng chính" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("navigation", { name: "Điều hướng chính" })).toHaveCount(0);

  await page.getByLabel("Câu hỏi", { exact: true }).fill("Hủy câu hỏi UAT này ngay sau khi gửi.");
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await page.getByRole("button", { name: "Dừng" }).click();
  await expect(page.getByText("Đã dừng câu trả lời trước khi hoàn tất.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Gửi câu hỏi" })).toBeVisible();

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1366, height: 768 },
    { width: 1024, height: 768 },
    { width: 768, height: 1024 },
    { width: 360, height: 800 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/documents");
    await expect(page.getByRole("heading", { level: 1, name: "Tài liệu" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.screenshot({
      path: resolve(screenshotsDir, `${viewport.width}x${viewport.height}-documents.png`),
      fullPage: true,
    });
  }
});

async function loginThroughUi(page: Page, account: Account): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/chat$/, { timeout: 30_000 });
}

async function logoutThroughUi(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Đăng xuất" }).click();
  await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
}

async function fillDepartment(page: Page, name: string, code: string, description: string): Promise<void> {
  await page.getByLabel("Tên", { exact: true }).fill(name);
  await page.getByLabel("Mã", { exact: true }).fill(code);
  await page.getByLabel("Mô tả (tùy chọn)").fill(description);
}

async function createUserThroughDrawer(page: Page, email: string, fullName: string, password: string): Promise<void> {
  await page.getByRole("button", { name: "Tạo người dùng" }).click();
  const drawer = page.getByRole("dialog", { name: "Tạo người dùng" });
  await drawer.getByLabel("Email").fill(email);
  await drawer.getByLabel("Họ tên").fill(fullName);
  await drawer.getByLabel("Mật khẩu tạm").fill(password);
  await drawer.getByLabel("Vai trò").selectOption("STAFF");
  await drawer.getByLabel("Phòng ban").selectOption(knowledgeDepartment.id);
  await drawer.getByRole("button", { name: "Tạo người dùng" }).click();
}

async function loginViaApi(request: APIRequestContext, account: Account): Promise<string> {
  const response = await request.post(`${apiBaseUrl}/api/v1/auth/login`, {
    data: { email: account.email, password: account.password },
  });
  expect(response.ok()).toBeTruthy();
  return ((await response.json()) as { data: { access_token: string } }).data.access_token;
}

async function findDepartment(request: APIRequestContext, token: string, code: string): Promise<Department> {
  const response = await request.get(`${apiBaseUrl}/api/v1/departments`, {
    headers: authHeaders(token),
    params: { search: code, page_size: 10 },
  });
  expect(response.ok()).toBeTruthy();
  const department = ((await response.json()) as { data: Department[] }).data.find((item) => item.code === code);
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
  const user = ((await response.json()) as { data: User[] }).data.find((item) => item.email === email);
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
