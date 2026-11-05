import { expect, type Page, test } from "@playwright/test";

async function mockAdminUsers(page: Page) {
  let staffActive = true;
  await page.addInitScript(() => {
    sessionStorage.setItem("enterprise_ai_access_token", "test-access-token");
    sessionStorage.setItem("enterprise_ai_refresh_token", "test-refresh-token");
  });
  await page.route("**/health/ready", (route) =>
    route.fulfill({ json: { status: "ready", checks: { database: "ok", redis: "ok" } } }),
  );
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      json: {
        data: {
          id: "admin-1",
          email: "admin@example.test",
          full_name: "Admin User",
          role: "ADMIN",
          department_id: null,
          is_active: true,
        },
        meta: null,
      },
    }),
  );
  await page.route("**/api/v1/users?**", (route) =>
    route.fulfill({
      json: {
        data: [{
          id: "staff-1",
          email: "staff@example.test",
          full_name: "Staff User",
          role: "STAFF",
          department_id: null,
          is_active: staffActive,
          created_at: "2026-10-14T00:00:00Z",
          updated_at: "2026-10-14T00:00:00Z",
        }],
        meta: { page: 1, page_size: 20, total: 1, total_pages: 1 },
      },
    }),
  );
  await page.route("**/api/v1/users/staff-1", (route) => {
    if (route.request().method() === "DELETE") {
      staffActive = false;
      return route.fulfill({ status: 204, body: "" });
    }
    return route.fallback();
  });
}

test("login has labeled fields, keyboard order, visible focus, and announced validation", async ({ page }) => {
  await page.goto("/login");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("textbox", { name: "Email" })).toBeFocused();
  const focusStyle = await page.getByRole("textbox", { name: "Email" }).evaluate((element) => {
    const style = getComputedStyle(element);
    return { width: style.outlineWidth, style: style.outlineStyle };
  });
  expect(focusStyle.style).not.toBe("none");
  expect(Number.parseFloat(focusStyle.width)).toBeGreaterThan(0);
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Password")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("alert")).toHaveCount(2);
});

test("confirmation dialog receives focus when opened", async ({ page }) => {
  await mockAdminUsers(page);
  await page.goto("/users");
  await page.getByRole("button", { name: "Deactivate" }).first().click();
  const dialog = page.getByRole("dialog", { name: /deactivate/i });
  await expect(dialog).toBeVisible();
  expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
});

test("Escape dismisses confirmation dialog without acting", async ({ page }) => {
  await mockAdminUsers(page);
  await page.goto("/users");
  await page.getByRole("button", { name: "Deactivate" }).first().click();
  const dialog = page.getByRole("dialog", { name: /deactivate/i });
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(page.getByText("INACTIVE")).toHaveCount(0);
});

test("mobile reduced-motion login does not overflow or animate its signal", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  const observed = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    animation: getComputedStyle(document.querySelector(".motion-signal")!, "::before").animationName,
  }));
  expect(observed.overflow).toBe(false);
  expect(observed.animation).toBe("none");
});

test("dialog traps both Tab directions, labels its message, and restores focus on cancel/reopen", async ({ page }) => {
  await mockAdminUsers(page);
  await page.goto("/users");
  const trigger = page.getByRole("button", { name: "Deactivate" }).first();
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Deactivate user" });
  const cancel = dialog.getByRole("button", { name: "Cancel" });
  const confirm = dialog.getByRole("button", { name: "Deactivate" });
  await page.getByRole("button", { name: "Create user" }).focus();
  await expect(cancel).toBeFocused();
  const observed = await page.evaluate(() => ({
    activeTag: document.activeElement?.tagName,
    activeText: document.activeElement?.textContent?.trim().slice(0, 40),
    modal: document.querySelector('[role="dialog"]')?.getAttribute("aria-modal"),
    describedBy: document.querySelector('[role="dialog"]')?.getAttribute("aria-describedby"),
  }));
  await page.keyboard.press("Shift+Tab");
  const afterShiftTab = await page.evaluate(() => ({
    activeTag: document.activeElement?.tagName,
    activeText: document.activeElement?.textContent?.trim().slice(0, 40),
    insideDialog: Boolean(document.querySelector('[role="dialog"]')?.contains(document.activeElement)),
  }));
  await page.keyboard.press("Tab");
  const afterTab = await page.evaluate(() => ({
    activeTag: document.activeElement?.tagName,
    activeText: document.activeElement?.textContent?.trim().slice(0, 40),
    insideDialog: Boolean(document.querySelector('[role="dialog"]')?.contains(document.activeElement)),
  }));
  const descriptionId = await dialog.getAttribute("aria-describedby");
  const descriptionText = descriptionId
    ? await page.locator(`[id="${descriptionId}"]`).textContent()
    : null;
  await cancel.click();
  const afterCancel = await page.evaluate(() => ({
    activeTag: document.activeElement?.tagName,
    activeText: document.activeElement?.textContent?.trim().slice(0, 40),
  }));
  expect(observed.modal).toBe("true");
  expect(descriptionId).toBeTruthy();
  expect(descriptionText).toContain("refresh tokens");
  expect(observed.activeText).toBe("Cancel");
  expect(afterShiftTab.insideDialog).toBe(true);
  expect(afterTab.insideDialog).toBe(true);
  expect(afterCancel.activeTag).toBe("BUTTON");
  expect(afterCancel.activeText).toBe("Deactivate");
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
  await trigger.click();
  await expect(cancel).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(confirm).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(cancel).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test("successful confirmation keeps focus on a live control when its trigger is replaced", async ({ page }) => {
  await mockAdminUsers(page);
  await page.goto("/users");
  await page.getByRole("button", { name: "Deactivate" }).first().click();
  const dialog = page.getByRole("dialog", { name: "Deactivate user" });
  await dialog.getByRole("button", { name: "Deactivate" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Reactivate" })).toBeVisible();
  const focus = await page.evaluate(() => ({
    tag: document.activeElement?.tagName,
    connected: document.activeElement?.isConnected,
    inMain: Boolean(document.querySelector("main")?.contains(document.activeElement)),
  }));
  expect(focus.connected).toBe(true);
  expect(focus.inMain).toBe(true);
  expect(focus.tag).toBe("BUTTON");
});
