import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

// Tests under tests/ run with real accounts, and a failing assertion prints both its received and its
// expected value (terminal, CI log, Playwright's error-context.md). So no expect() may take a token,
// password, secret or cookie as either; compare key names, a length or presence instead
// (docs/ui/FRONTEND_TESTING.md, "Secrets in tests"). The check goes by names.
const SECRET_NAME = "/token|password|passwd|secret|cookie/i";
const EXPECT_CALL = "CallExpression:matches([callee.name='expect'], [callee.object.name='expect'])";
// A variable, a property, a call (tokens(), getToken()) or a storage key ("..._token"), awaited or not.
const SECRET_PATHS = ["name", "property.name", "callee.name", "callee.property.name", "arguments.0.value"];
const secretAssertionMessage =
  "Assertion on a token, password, secret or cookie value: a failure prints it. Compare key names, a length or presence, e.g. expect(Boolean(token)).toBe(true).";
const secretAssertions = [
  ...["", "argument."].flatMap((awaited) =>
    SECRET_PATHS.map((path) => `${EXPECT_CALL}[arguments.0.${awaited}${path}=${SECRET_NAME}]`),
  ),
  ...SECRET_PATHS.slice(0, 4).map((path) => `CallExpression[callee.property.name=/^to[A-Z]/][arguments.0.${path}=${SECRET_NAME}]`),
].map((selector) => ({ selector, message: secretAssertionMessage }));

export default tseslint.config(
  { ignores: ["dist/**", "coverage/**", "node_modules/**", "*.js", "*.d.ts", "*.tsbuildinfo", "postcss.config.cjs"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["server.mjs", "tests/e2e-live/**/*.mjs"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        console: "readonly",
        process: "readonly",
        URL: "readonly",
        setTimeout: "readonly",
      },
    },
  },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: {
        document: "readonly",
        window: "readonly",
        navigator: "readonly",
        sessionStorage: "readonly",
        AbortController: "readonly",
        ReadableStream: "readonly",
        TextDecoder: "readonly",
        TextEncoder: "readonly",
        FormData: "readonly",
        File: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        Response: "readonly",
        RequestInit: "readonly",
        Headers: "readonly",
        fetch: "readonly",
        crypto: "readonly",
        DOMException: "readonly",
        FileList: "readonly",
      },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": "off",
      "react-hooks/set-state-in-effect": "off",
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
  {
    files: ["tests/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": ["error", ...secretAssertions],
    },
  },
);

