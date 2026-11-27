export const appConfig = {
  appName: import.meta.env.VITE_APP_NAME || "Enterprise AI Knowledge Assistant",
  // Unset: the dev API. "": the page's own origin (a same-origin proxy, DEMO.md). Absolute: as given.
  apiBaseUrl: trimTrailingSlash(
    import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000",
  ),
  apiPrefix: "/api/v1",
};

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}
