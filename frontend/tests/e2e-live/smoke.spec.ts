import { expect, type APIRequestContext, type BrowserContext, type Page, test } from "@playwright/test";
import { appendFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

/**
 * Smoke of the redesigned UI against a real backend (owner checklist, wave 4).
 * Run: E2E_LIVE=true UAT_ADMIN_PASSWORD=… UAT_MANAGER_PASSWORD=… UAT_STAFF_PASSWORD=…
 *      PLAYWRIGHT_BASE_URL=<frontend> E2E_API_BASE_URL=<api> npx playwright test -c playwright.live.config.ts smoke
 * Passwords come only from the environment. Traces, failure screenshots and videos are off so typed
 * values never reach a file; the screenshots this spec takes show only masked password fields.
 */
// channel "chromium": the full build in new headless mode has the PDF viewer the preview needs.
test.use({ trace: "off", screenshot: "off", video: "off", channel: "chromium" });
// The three tests are independent; run with --workers=1 so they still go one after another.

const apiBaseUrl = process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:18300";
const shotsDir = process.env.SMOKE_SCREENSHOT_DIR ?? resolve(process.cwd(), "test-results", "smoke");
// Public dev item ND-001 of tests/acceptance/natural_dev_v1.yaml (never a held-out question), answered on the
// smoke stack; ND-003 (a list) and the old English UAT question came back NO_ANSWER there.
const answerableQuestion =
  process.env.SMOKE_ANSWERABLE_QUESTION ?? "Tổng thời gian nghỉ lễ là bao nhiêu ngày trong một năm?";
const refusedQuestion = process.env.SMOKE_REFUSED_QUESTION ?? "Giá cổ phiếu của công ty hôm nay là bao nhiêu?";
// The owner asks for at least 180 s per answer; a cold first answer on a small GPU can take longer.
const answerTimeout = 300_000;

type Account = { email: string; password: string };
let accounts: { admin: Account; manager: Account; staff: Account };

test.beforeAll(async () => {
  if (process.env.E2E_LIVE !== "true") {
    throw new Error("Set E2E_LIVE=true to run the live smoke.");
  }
  accounts = {
    admin: { email: process.env.UAT_ADMIN_EMAIL ?? "admin.uat@example.test", password: requiredEnv("UAT_ADMIN_PASSWORD") },
    manager: { email: process.env.UAT_MANAGER_EMAIL ?? "manager.uat@example.test", password: requiredEnv("UAT_MANAGER_PASSWORD") },
    staff: { email: process.env.UAT_STAFF_EMAIL ?? "staff.uat@example.test", password: requiredEnv("UAT_STAFF_PASSWORD") },
  };
  await mkdir(shotsDir, { recursive: true });
});

test("staff: answered and refused questions, preview from a citation, no uploader names", async ({ page, context }) => {
  test.setTimeout(900_000);
  const previewStatuses: number[] = [];
  context.on("response", (response) => {
    if (/\/api\/v1\/documents\/[^/]+\/preview$/.test(new URL(response.url()).pathname)) {
      previewStatuses.push(response.status());
    }
  });

  await login(page, accounts.staff);
  await page.getByRole("button", { name: "Cuộc trò chuyện mới", exact: true }).click();
  // Count answers only once the new, empty session is on screen (not the previously selected one).
  await expect(page.getByText("Chưa có tin nhắn")).toBeVisible();

  const answered = await ask(page, answerableQuestion, "câu 1 (có trả lời, câu đầu tiên của phiên)");
  await expect.soft(answered, "answerable question should be ANSWERED").toContainText("Đã xác minh nguồn");
  await shot(page, "staff-1-chat-answered");

  const refused = await ask(page, refusedQuestion, "câu 2 (bị từ chối)");
  await expect.soft(refused, "refused question should be NO_ANSWER").toContainText("Không có trích dẫn");
  await expect.soft(refused.getByRole("button", { name: /Mở trích dẫn/ })).toHaveCount(0);
  await shot(page, "staff-2-chat-refused");

  const chip = answered.getByRole("button", { name: /Mở trích dẫn/ }).first();
  if (await chip.count()) {
    await chip.click();
    const link = page
      .getByRole("complementary", { name: "Trích dẫn" })
      .getByRole("link", { name: /Mở tài liệu tại trang/ })
      .first();
    const [viewer] = await Promise.all([context.waitForEvent("page"), link.click()]);
    await viewer.waitForLoadState();
    await expect(viewer.locator("iframe, img").first()).toBeVisible({ timeout: 60_000 });
    await viewer.waitForTimeout(3_000); // let the PDF viewer paint the page before the screenshot
    await expect(viewer.getByText("Không mở được tài liệu")).toHaveCount(0);
    expect(previewStatuses, "the viewer should load GET /documents/{id}/preview").toContain(200);
    await shot(viewer, "staff-3-preview");
    await viewer.close();
  } else {
    test.info().annotations.push({ type: "skipped-step", description: "no citation to open a preview from" });
  }

  const listResponse = page.waitForResponse((response) => /\/api\/v1\/documents\?/.test(response.url()));
  await page.getByRole("link", { name: "Tài liệu", exact: true }).click();
  const list = (await (await listResponse).json()) as { data: Record<string, unknown>[] };
  for (const item of list.data) {
    // BR-4 option (a): the name keys are absent, not null, for a non-Admin caller.
    expect(item).not.toHaveProperty("uploaded_by_name");
    expect(item).not.toHaveProperty("department_name");
    expect(typeof item.uploaded_by_me).toBe("boolean");
  }
  await shot(page, "staff-4-documents");
  if (list.data.length) {
    await page.getByRole("link", { name: "Chi tiết" }).first().click();
    // Wait for the detail itself (its "Thông tin" section), not the list's heading still on screen.
    await expect(page.getByRole("heading", { name: "Thông tin" })).toBeVisible();
    await expect(page.getByText("Người tải lên")).toHaveCount(list.data[0].uploaded_by_me ? 1 : 0);
    await shot(page, "staff-5-document-detail");
  }
  await logout(page);
});

test("manager: upload limited to PRIVATE or the own department, others refused by the API", async ({
  page,
  context,
  playwright,
}) => {
  await login(page, accounts.manager);
  await page.goto("/documents/upload");
  await expect(page.getByRole("radio", { name: /^Toàn công ty/ })).toBeDisabled();
  await page.getByRole("radio", { name: /^Phòng ban/ }).check();
  const options = await page.getByLabel("Phòng ban", { exact: true }).locator("option").allTextContents();
  expect(options, "a Manager is offered only their own department").toHaveLength(2);
  await shot(page, "manager-1-upload-form");

  // The API itself must refuse another department and ORGANIZATION (BR-1 rule 3).
  const managerToken = await page.evaluate(() => sessionStorage.getItem("enterprise_ai_access_token"));
  const api = await playwright.request.newContext({ baseURL: apiBaseUrl });
  try {
    const adminToken = await apiLogin(api, accounts.admin);
    const me = await (await api.get("/api/v1/auth/me", { headers: bearer(managerToken) })).json();
    const departments = await (await api.get("/api/v1/departments?page_size=100", { headers: bearer(adminToken) })).json();
    const other = (departments.data as { id: string }[]).find((department) => department.id !== me.data.department_id);
    const pdf = await makePdf(context, `smoke manager refused ${Date.now()}`);
    if (other) {
      const otherDepartment = await api.post("/api/v1/documents/upload", {
        headers: bearer(managerToken),
        multipart: { file: { name: "smoke.pdf", mimeType: "application/pdf", buffer: pdf }, title: "Smoke", access_scope: "DEPARTMENT", department_id: other.id },
      });
      expect(otherDepartment.status(), "another department").toBe(403);
    }
    const organization = await api.post("/api/v1/documents/upload", {
      headers: bearer(managerToken),
      multipart: { file: { name: "smoke.pdf", mimeType: "application/pdf", buffer: pdf }, title: "Smoke", access_scope: "ORGANIZATION" },
    });
    expect(organization.status(), "ORGANIZATION").toBe(403);
  } finally {
    await api.dispose();
  }

  // A real PRIVATE upload through the form, then clean it up.
  await page.getByRole("radio", { name: /^Riêng tư/ }).check();
  await page.getByLabel("Tệp PDF", { exact: true }).setInputFiles({
    name: "smoke-private.pdf",
    mimeType: "application/pdf",
    buffer: await makePdf(context, `smoke manager private ${Date.now()}`),
  });
  await page.getByLabel("Tiêu đề").fill(`Smoke riêng tư ${Date.now()}`);
  await page.getByRole("button", { name: "Tải lên" }).click();
  await expect(page).toHaveURL(/\/documents\/[0-9a-f-]+$/, { timeout: 60_000 });
  await expect(page.getByText("Bạn đã tải lên")).toBeVisible();
  await shot(page, "manager-2-uploaded-detail");
  await page.getByRole("button", { name: "Xóa", exact: true }).click();
  await page.getByRole("dialog", { name: "Xóa tài liệu này?" }).getByRole("button", { name: "Xóa" }).click();
  await expect(page).toHaveURL(/\/documents$/);
  await logout(page);
});

test("admin: names in documents, audit filtered by event_type, system status", async ({ page }) => {
  await login(page, accounts.admin);
  await page.getByRole("link", { name: "Tài liệu", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Tài liệu" })).toBeVisible();
  await page.getByRole("link", { name: "Chi tiết" }).first().click();
  await expect(page.getByText("Người tải lên")).toBeVisible();
  await shot(page, "admin-1-document-detail");

  await page.getByRole("link", { name: "Nhật ký hệ thống" }).click();
  const filtered = page.waitForResponse((response) => response.url().includes("event_type=AUTH_LOGIN_SUCCEEDED"));
  await page.getByLabel("Loại sự kiện").selectOption("AUTH_LOGIN_SUCCEEDED");
  expect((await filtered).status()).toBe(200);
  const events = await page.locator("tbody tr td:nth-child(2)").allTextContents();
  expect(events.length).toBeGreaterThan(0);
  expect(new Set(events)).toEqual(new Set(["AUTH_LOGIN_SUCCEEDED"]));
  await shot(page, "admin-2-audit-filtered");

  await page.getByRole("link", { name: "Trạng thái hệ thống" }).click();
  await expect(page.getByText("Nhà cung cấp LLM")).toBeVisible();
  await shot(page, "admin-3-system");
  await logout(page);
});

async function login(page: Page, account: Account): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/chat$/);
}

async function logout(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Đăng xuất" }).click();
  await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
}

/**
 * Sends a question and returns the new answer card once the validated answer is shown. The answer card
 * only appears after message.completed, so the time measured is end to end: click to answer on screen.
 */
async function ask(page: Page, question: string, label: string) {
  const answers = page.locator('section[aria-label="Cuộc trò chuyện"] article');
  const before = await answers.count();
  await page.getByLabel("Câu hỏi", { exact: true }).fill(question);
  const started = Date.now();
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(answers).toHaveCount(before + 1, { timeout: answerTimeout });
  const seconds = ((Date.now() - started) / 1000).toFixed(1);
  // Pin this answer: answers.last() is lazy and would move to the next question's card.
  const card = answers.nth(before);
  const outcome = (await card.innerText()).includes("Đã xác minh nguồn") ? "ANSWERED" : "NO_ANSWER";
  test.info().annotations.push({ type: "chat-timing", description: `${label}: ${seconds} s, ${outcome}` });
  await appendFile(resolve(shotsDir, "timings.txt"), `${new Date().toISOString()} ${label}: ${seconds} s, ${outcome}\n`);
  return card;
}

async function shot(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: resolve(shotsDir, `${name}.png`), fullPage: true });
}

async function makePdf(context: BrowserContext, text: string): Promise<Buffer> {
  const pdfPage = await context.newPage();
  await pdfPage.setContent(`<h1>${text}</h1>`);
  const pdf = await pdfPage.pdf();
  await pdfPage.close();
  return pdf;
}

async function apiLogin(api: APIRequestContext, account: Account): Promise<string> {
  const response = await api.post("/api/v1/auth/login", { data: { email: account.email, password: account.password } });
  expect(response.ok(), "API login").toBeTruthy();
  return (await response.json()).data.access_token as string;
}

function bearer(token: string | null): Record<string, string> {
  return { Authorization: `Bearer ${token ?? ""}` };
}

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required for the live smoke.`);
  }
  return value;
}
