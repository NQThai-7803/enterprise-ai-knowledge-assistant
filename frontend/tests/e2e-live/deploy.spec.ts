import { expect, type Page, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

/**
 * Checks that only show behind a production build and its reverse proxy (DEMO.md: nginx serves the SPA
 * and proxies /api/ and /health/ on the same origin): sign-in from either loopback host name (BR-13),
 * SSE passed on event by event, token refresh through the proxy, citation excerpts free of Symbol-font
 * code points (BR-14), the cited PDF opened at its page, and a reload on deep routes.
 * Run: E2E_LIVE=true UAT_*_PASSWORD=… PLAYWRIGHT_BASE_URL=<proxy origin>
 *      npx playwright test -c playwright.live.config.ts deploy --workers=1
 * Secrets in Tests: tokens stay inside the page or are only decoded for their exp, never asserted on.
 */
test.use({ trace: "off", screenshot: "off", video: "off", channel: "chromium" });

const shotsDir = process.env.SMOKE_SCREENSHOT_DIR ?? resolve(process.cwd(), "test-results", "smoke");
const answerableQuestion =
  process.env.SMOKE_ANSWERABLE_QUESTION ?? "Tổng thời gian nghỉ lễ là bao nhiêu ngày trong một năm?";
// An answer the model has just given (DEMO.md: warmup asks a few dev questions) comes back too fast to
// tell a buffering proxy from a streaming one, so the SSE check can take a question nobody asked yet.
const sseQuestion = process.env.SMOKE_SSE_QUESTION ?? answerableQuestion;
const answerTimeout = 300_000;

type Account = { email: string; password: string };
let accounts: { admin: Account; manager: Account; staff: Account };

test.beforeAll(async () => {
  if (process.env.E2E_LIVE !== "true") {
    throw new Error("Set E2E_LIVE=true to run the live deploy checks.");
  }
  accounts = {
    admin: { email: process.env.UAT_ADMIN_EMAIL ?? "admin.uat@example.test", password: requiredEnv("UAT_ADMIN_PASSWORD") },
    manager: { email: process.env.UAT_MANAGER_EMAIL ?? "manager.uat@example.test", password: requiredEnv("UAT_MANAGER_PASSWORD") },
    staff: { email: process.env.UAT_STAFF_EMAIL ?? "staff.uat@example.test", password: requiredEnv("UAT_STAFF_PASSWORD") },
  };
  await mkdir(shotsDir, { recursive: true });
});

test("sign-in works from the other loopback host name of the proxy (same-origin build)", async ({ page, baseURL }) => {
  const base = new URL(baseURL!);
  const otherHost = base.hostname === "localhost" ? "127.0.0.1" : base.hostname === "127.0.0.1" ? "localhost" : null;
  test.skip(!otherHost, "the base URL is not a loopback host");
  const origin = `${base.protocol}//${otherHost}:${base.port}`;
  // A build with a fixed API origin calls it from this page cross-origin, and CORS refuses the sign-in.
  const elsewhere: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (/^\/(api|health)\//.test(url.pathname) && url.origin !== origin) elsewhere.push(`${url.origin}${url.pathname}`);
  });
  await login(page, accounts.staff, origin);
  await expect(page.getByText("API sẵn sàng"), "/health/ready from this origin").toBeVisible();
  await page.screenshot({ path: resolve(shotsDir, `deploy-0-signed-in-${otherHost}.png`) });
  expect(elsewhere, "API requests sent to another origin").toEqual([]);
  await logout(page);
});

test("SSE through the proxy: events arrive one by one and the stream closes", async ({ page }) => {
  test.setTimeout(answerTimeout + 60_000);
  await login(page, accounts.staff);
  // A raw stream read in the page, which holds the token; only event names and times come back.
  const stream = await page.evaluate(
    async ({ question, title }) => {
      const auth = { Authorization: `Bearer ${sessionStorage.getItem("enterprise_ai_access_token")}` };
      const json = { ...auth, "Content-Type": "application/json" };
      const created = await (await fetch("/api/v1/chat/sessions", { method: "POST", headers: json, body: JSON.stringify({ title }) })).json();
      const sessionId = created.data.id as string;
      const begin = performance.now();
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/messages/stream`, {
        method: "POST",
        headers: { ...json, Accept: "text/event-stream" },
        body: JSON.stringify({ content: question }),
      });
      const arrivals: { event: string; ms: number }[] = [];
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let pending = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        pending += decoder.decode(value, { stream: true });
        const frames = pending.split(/\r?\n\r?\n/);
        pending = frames.pop() ?? "";
        for (const frame of frames) {
          const name = /^event: *(.+)$/m.exec(frame)?.[1]?.trim();
          if (name) arrivals.push({ event: name, ms: Math.round(performance.now() - begin) });
        }
      }
      const closedMs = Math.round(performance.now() - begin);
      await fetch(`/api/v1/chat/sessions/${sessionId}`, { method: "DELETE", headers: auth });
      return {
        status: response.status,
        contentType: response.headers.get("content-type"),
        accelBuffering: response.headers.get("x-accel-buffering"),
        arrivals,
        closedMs,
      };
    },
    { question: sseQuestion, title: `Kiểm SSE ${Date.now()}` },
  );

  const startedMs = stream.arrivals.find((arrival) => arrival.event === "stream.started")?.ms;
  const completedMs = stream.arrivals.find((arrival) => arrival.event === "message.completed")?.ms;
  const heartbeats = stream.arrivals.filter((arrival) => arrival.event === "heartbeat").length;
  test.info().annotations.push({
    type: "sse-timing",
    description: `started ${startedMs} ms, ${heartbeats} heartbeat(s), completed ${completedMs} ms, closed ${stream.closedMs} ms, X-Accel-Buffering ${stream.accelBuffering}`,
  });
  expect(stream.status).toBe(200);
  expect(stream.contentType).toMatch(/^text\/event-stream/);
  expect(stream.arrivals[0]?.event, "first event").toBe("stream.started");
  expect(completedMs, "message.completed arrived").toBeDefined();
  // A buffering proxy holds every event until the upstream closes; unbuffered, stream.started comes
  // at once and the answer seconds later.
  expect(startedMs!, "stream.started should not wait for the answer").toBeLessThan(Math.min(3_000, completedMs!));
  if (completedMs! - startedMs! < 2_000) {
    const note = "answer under 2 s (already answered once?): buffering cannot be told apart, SSE check inconclusive";
    test.info().annotations.push({ type: "sse-inconclusive", description: note });
    console.log(`SSE INCONCLUSIVE: ${note}`);
  }
  expect(stream.closedMs - completedMs!, "the stream closes after message.completed").toBeLessThan(2_000);
});

test("staff: refresh through the proxy keeps the session, the cited PDF opens at its page", async ({ page, context }) => {
  test.setTimeout(answerTimeout + 120_000);
  await login(page, accounts.staff);
  await page.getByRole("button", { name: "Cuộc trò chuyện mới", exact: true }).click();
  await expect(page.getByText("Chưa có tin nhắn")).toBeVisible();

  // Access token about to expire (the client refreshes before a stream when fewer than 30 s are
  // left): the next question goes through POST /auth/refresh on the proxy first.
  const accessToken = await page.evaluate(() => sessionStorage.getItem("enterprise_ai_access_token"));
  const { exp } = JSON.parse(Buffer.from(accessToken!.split(".")[1], "base64url").toString()) as { exp: number };
  await page.clock.setFixedTime(new Date((exp - 10) * 1000));
  const refreshed = page.waitForResponse((response) => response.url().endsWith("/api/v1/auth/refresh"));
  const answers = page.locator('section[aria-label="Cuộc trò chuyện"] article');
  await page.getByLabel("Câu hỏi", { exact: true }).fill(answerableQuestion);
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  expect((await refreshed).status(), "refresh through the proxy").toBe(200);
  await expect(answers).toHaveCount(1, { timeout: answerTimeout });
  const answer = answers.first();
  await expect(answer, "the answer after the refresh").toContainText("Đã xác minh nguồn");
  const storedAuthKeys = await page.evaluate(() =>
    ["enterprise_ai_access_token", "enterprise_ai_refresh_token"].filter((key) => sessionStorage.getItem(key) !== null),
  );
  expect(storedAuthKeys, "still signed in after the refresh").toHaveLength(2);

  await answer.getByRole("button", { name: /Mở trích dẫn/ }).first().click();
  const citations = page.getByRole("complementary", { name: "Trích dẫn" });
  // BR-14: Symbol-font bullets (Private Use Area, e.g. U+F0B7) render as empty boxes.
  const excerpts = await citations.locator("article > p:nth-of-type(2)").allTextContents();
  expect(excerpts.length, "excerpts in the citation panel").toBeGreaterThan(0);
  test.info().annotations.push({ type: "excerpt-start", description: excerpts.map((text) => text.slice(0, 60)).join(" | ") });
  expect(excerpts.filter((text) => /[-]/.test(text)), "excerpts with a Private Use Area code point").toEqual([]);
  await citations.screenshot({ path: resolve(shotsDir, "deploy-1-citation-excerpt.png") });
  const link = citations.getByRole("link", { name: /Mở tài liệu tại trang/ }).first();
  const pageNumber = Number(/trang (\d+)/.exec((await link.innerText()) ?? "")?.[1]);
  expect(pageNumber, "the citation names a page").toBeGreaterThan(0);
  const previewResponse = context.waitForEvent("response", (response) => /\/api\/v1\/documents\/[^/]+\/preview$/.test(new URL(response.url()).pathname));
  const [viewer] = await Promise.all([context.waitForEvent("page"), link.click()]);
  const preview = await previewResponse;
  expect(preview.status()).toBe(200);
  expect(preview.headers()["content-type"], "preview content type through the proxy").toMatch(/^application\/pdf/);
  await expect(viewer).toHaveURL(new RegExp(`/documents/[0-9a-f-]+/view\\?page=${pageNumber}$`));
  const frame = viewer.locator("iframe");
  await expect(frame).toBeVisible({ timeout: 60_000 });
  expect(await frame.getAttribute("src"), "the PDF is opened at the cited page").toMatch(new RegExp(`^blob:.+#page=${pageNumber}$`));
  await viewer.waitForTimeout(3_000); // let the PDF viewer paint the page before the screenshot
  await viewer.screenshot({ path: resolve(shotsDir, `deploy-1-preview-page-${pageNumber}.png`) });

  // A reload on the viewer's deep route: nginx must serve the app, which opens the same page again.
  const reload = await viewer.reload();
  expect(reload?.status(), "reload of the viewer route").toBe(200);
  await expect(viewer.locator("iframe")).toBeVisible({ timeout: 60_000 });
  expect(await viewer.locator("iframe").getAttribute("src")).toMatch(new RegExp(`#page=${pageNumber}$`));
  await viewer.close();
  await logout(page);
});

test("reload on deep routes serves the app for each role", async ({ page }) => {
  // staff: a document's detail page, reached through the app.
  await login(page, accounts.staff);
  await page.getByRole("link", { name: "Tài liệu", exact: true }).click();
  await page.getByRole("link", { name: "Chi tiết" }).first().click();
  await expect(page).toHaveURL(/\/documents\/[0-9a-f-]+$/);
  await expectReloadServesApp(page, "Thông tin");
  await logout(page);

  // manager: the upload form, opened by its URL.
  await login(page, accounts.manager);
  await page.goto("/documents/upload");
  await expectReloadServesApp(page, "Tải tài liệu lên");
  await logout(page);

  // admin: the audit log.
  await login(page, accounts.admin);
  await page.getByRole("link", { name: "Nhật ký hệ thống", exact: true }).click();
  await expectReloadServesApp(page, "Nhật ký hệ thống");
  await logout(page);
});

async function expectReloadServesApp(page: Page, heading: string): Promise<void> {
  const response = await page.reload();
  expect(response?.status(), `reload of ${new URL(page.url()).pathname}`).toBe(200);
  await expect(page.getByRole("heading", { name: heading }).first()).toBeVisible();
}

async function login(page: Page, account: Account, origin = ""): Promise<void> {
  await page.goto(`${origin}/login`);
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/chat$/);
}

async function logout(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Đăng xuất" }).click();
  await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
}

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required for the live deploy checks.`);
  }
  return value;
}
