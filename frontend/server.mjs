import { createReadStream, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("./dist/", import.meta.url));
const port = Number.parseInt(process.env.PORT ?? "8080", 10);

const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".webp", "image/webp"],
  [".ico", "image/x-icon"],
]);

function resolvePath(url) {
  const pathname = decodeURIComponent(new URL(url, "http://localhost").pathname);
  const normalized = normalize(pathname).replace(/^([/\\])+/, "");
  const candidate = join(root, normalized);
  if (!candidate.startsWith(root)) {
    return join(root, "index.html");
  }
  try {
    const stat = statSync(candidate);
    if (stat.isFile()) {
      return candidate;
    }
  } catch {
    return join(root, "index.html");
  }
  return join(root, "index.html");
}

createServer((request, response) => {
  const filePath = resolvePath(request.url ?? "/");
  const type = contentTypes.get(extname(filePath)) ?? "application/octet-stream";
  response.setHeader("Content-Type", type);
  response.setHeader("Cache-Control", filePath.endsWith("index.html") ? "no-cache" : "public, max-age=31536000, immutable");
  createReadStream(filePath)
    .on("error", () => {
      response.writeHead(500);
      response.end("Static asset unavailable.");
    })
    .pipe(response);
}).listen(port, "0.0.0.0", () => {
  console.log(`Frontend listening on ${port}`);
});