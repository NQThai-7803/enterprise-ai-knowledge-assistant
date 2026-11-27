// @vitest-environment node
import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

// Guards the no-restricted-syntax rule of eslint.config.js for tests/** (docs/ui/FRONTEND_TESTING.md,
// "Secrets in tests"): an ESLint upgrade or a selector edit must not silently switch it off.
const eslint = new ESLint();

const lines = [
  'expect(accessToken).toBe("x");', // 1: a variable
  "expect(data.refresh_token).toEqual(expected);", // 2: a property
  "expect(await tokens()).toEqual([]);", // 3: an awaited call
  'expect(sessionStorage.getItem("enterprise_ai_access_token")).toBeNull();', // 4: a storage key
  "expect(field).toHaveValue(account.password);", // 5: the expected value
  "expect.soft(clientSecret).toBeTruthy();", // 6: a soft assertion
  'expect(page.context().cookies()).not.toEqual("");', // 7: a cookie call
  "expect(Boolean(accessToken)).toBe(true);", // allowed: presence
  "expect(accessToken.length).toBeGreaterThan(20);", // allowed: a length
  "expect(await storedAuthKeys()).toEqual([]);", // allowed: key names
  "expect(response.status()).toBe(200);", // allowed: unrelated
];

async function flaggedLines(filePath: string): Promise<number[]> {
  const [result] = await eslint.lintText(lines.join("\n"), { filePath });
  return result.messages.filter((message) => message.ruleId === "no-restricted-syntax").map((message) => message.line);
}

// The first lintText loads the ESLint config and the TypeScript parser: slow when files run in parallel.
describe("secret assertion lint rule", { timeout: 30_000 }, () => {
  it("flags assertions on token, password, secret or cookie values in tests/**", async () => {
    expect(await flaggedLines("tests/e2e-live/example.spec.ts")).toEqual([1, 2, 3, 4, 5, 6, 7]);
  });

  it("leaves unit tests under src/ alone (fixed fake values are not secrets)", async () => {
    expect(await flaggedLines("src/api/example.test.ts")).toEqual([]);
  });
});
