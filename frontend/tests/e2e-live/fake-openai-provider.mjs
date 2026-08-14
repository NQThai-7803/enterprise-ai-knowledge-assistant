import { createServer } from "node:http";
import { fileURLToPath } from "node:url";

const port = Number.parseInt(process.env.PORT ?? "18080", 10);
const delayMs = Number.parseInt(process.env.FAKE_LLM_DELAY_MS ?? "250", 10);
const model = "uat-deterministic-model";
export const noAnswerSentinel = "__NO_ANSWER__";

export function normalizeText(value) {
  return String(value ?? "")
    .normalize("NFC")
    .toLocaleLowerCase("vi")
    .replace(/\s+/g, " ")
    .trim();
}

function latestUserPrompt(payload) {
  const messages = Array.isArray(payload.messages) ? payload.messages : [];
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.role === "user" && typeof message.content === "string") {
      return message.content;
    }
  }
  return "";
}

function currentQuestion(prompt) {
  const match = /Current question:\s*([\s\S]*)$/i.exec(prompt);
  return (match?.[1] ?? prompt).trim();
}

function sourceBlocks(prompt) {
  const sources = [];
  const pattern =
    /--- SOURCE_(\d+) START ---\s*Document title:\s*([^\n]*)\nPage:\s*([^\n]*)\nContent:\n([\s\S]*?)\n--- SOURCE_\1 END ---/g;
  for (const match of prompt.matchAll(pattern)) {
    sources.push({
      marker: `[SOURCE_${match[1]}]`,
      title: match[2].trim(),
      page: match[3].trim(),
      content: match[4].trim(),
      normalized: normalizeText(match[4]),
    });
  }
  return sources;
}

function findSource(sources, predicates) {
  return sources.find((source) => predicates.every((predicate) => predicate(source.normalized)));
}

function includesAny(...needles) {
  const normalizedNeedles = needles.map((needle) => normalizeText(needle));
  return (text) => normalizedNeedles.some((needle) => text.includes(needle));
}

function includesAll(...needles) {
  const normalizedNeedles = needles.map((needle) => normalizeText(needle));
  return (text) => normalizedNeedles.every((needle) => text.includes(needle));
}

function mentionsUnsupportedOrganization(question) {
  return !includesAny("nova digital")(question) && includesAny("apple", "microsoft", "c\u00f4ng ty kh\u00e1c")(question);
}

function isCtoQuestion(question) {
  return includesAny("cto", "gi\u00e1m \u0111\u1ed1c c\u00f4ng ngh\u1ec7")(question);
}

function findNovaCtoSource(sources) {
  return findSource(sources, [
    includesAny("nova digital"),
    includesAny("cto", "gi\u00e1m \u0111\u1ed1c c\u00f4ng ngh\u1ec7"),
    includesAny("l\u00ea thu h\u00e0"),
  ]);
}

function isNovaAssistQuestion(question) {
  return includesAny("novaassist")(question);
}

function findNovaAssistSource(sources) {
  return findSource(sources, [
    includesAny("novaassist"),
    includesAny(
      "nova digital",
      "tr\u1ee3 l\u00fd ai doanh nghi\u1ec7p",
      "s\u1ea3n ph\u1ea9m tr\u1ee3 l\u00fd tri th\u1ee9c",
    ),
  ]);
}

function formatVietnameseList(items) {
  if (items.length === 0) {
    return "";
  }
  if (items.length === 1) {
    return items[0];
  }
  return `${items.slice(0, -1).join(", ")} v\u00e0 ${items.at(-1)}`;
}

function novaAssistAnswer(source) {
  const text = source.normalized;
  const intro = includesAny("tr\u1ee3 l\u00fd ai doanh nghi\u1ec7p")(text)
    ? "NovaAssist l\u00e0 tr\u1ee3 l\u00fd AI doanh nghi\u1ec7p c\u1ee7a Nova Digital"
    : "NovaAssist l\u00e0 s\u1ea3n ph\u1ea9m tr\u1ee3 l\u00fd tri th\u1ee9c c\u1ee7a Nova Digital";
  const capabilities = [];
  if (includesAll("tri th\u1ee9c n\u1ed9i b\u1ed9", "rag")(text)) {
    capabilities.push("h\u1ed7 tr\u1ee3 tra c\u1ee9u tri th\u1ee9c n\u1ed9i b\u1ed9 b\u1eb1ng RAG");
  } else if (includesAny("tra c\u1ee9u tri th\u1ee9c n\u1ed9i b\u1ed9")(text)) {
    capabilities.push("h\u1ed7 tr\u1ee3 tra c\u1ee9u tri th\u1ee9c n\u1ed9i b\u1ed9");
  } else if (includesAny("t\u00ecm ki\u1ebfm t\u00e0i li\u1ec7u n\u1ed9i b\u1ed9")(text)) {
    capabilities.push("h\u1ed7 tr\u1ee3 t\u00ecm ki\u1ebfm t\u00e0i li\u1ec7u n\u1ed9i b\u1ed9");
  }
  if (includesAny("tr\u1ea3 l\u1eddi c\u00f3 tr\u00edch d\u1eabn", "h\u1ecfi \u0111\u00e1p c\u00f3 tr\u00edch d\u1eabn")(text)) {
    capabilities.push("tr\u1ea3 l\u1eddi c\u00f3 tr\u00edch d\u1eabn");
  }
  if (includesAny("ph\u00e2n quy\u1ec1n")(text)) {
    capabilities.push("ph\u00e2n quy\u1ec1n");
  }
  if (includesAny("audit log")(text)) {
    capabilities.push("audit log");
  }

  const suffix = capabilities.length > 0 ? `, ${formatVietnameseList(capabilities)}` : "";
  return `${intro}${suffix} ${source.marker}.`;
}

export function answerForPayload(payload) {
  const prompt = latestUserPrompt(payload);
  const question = normalizeText(currentQuestion(prompt));
  const sources = sourceBlocks(prompt);

  if (includesAny("travel approval", "c\u00f4ng t\u00e1c", "du l\u1ecbch", "\u0111i c\u00f4ng t\u00e1c")(question)) {
    const source = findSource(sources, [
      includesAny("uat travel approval policy", "travel approval"),
      includesAny("manager approval", "booking travel"),
    ]);
    return source
      ? `The UAT travel approval policy requires manager approval before booking travel and expense evidence after the trip ${source.marker}.`
      : noAnswerSentinel;
  }

  if (
    includesAll("th\u1eddi gian", "l\u00e0m vi\u1ec7c")(question) ||
    includesAll("l\u1ecbch", "l\u00e0m vi\u1ec7c", "ti\u00eau chu\u1ea9n")(question)
  ) {
    const scheduleSource = findSource(sources, [
      includesAny("08:00 - 12:00", "08:00\u201312:00"),
      includesAny("13:00 - 17:00", "13:00\u201317:00"),
      includesAny("40 gi\u1edd"),
    ]);
    const legalLimitSource = findSource(sources, [includesAny("08 gi\u1edd/ng\u00e0y", "48 gi\u1edd/tu\u1ea7n")]);
    const source = scheduleSource ?? legalLimitSource;
    return source
      ? `Th\u1eddi gian l\u00e0m vi\u1ec7c ti\u00eau chu\u1ea9n l\u00e0 Th\u1ee9 Hai \u0111\u1ebfn Th\u1ee9 S\u00e1u, bu\u1ed5i s\u00e1ng 08:00 - 12:00, bu\u1ed5i chi\u1ec1u 13:00 - 17:00, t\u1ed5ng 08 gi\u1edd/ng\u00e0y. Doanh nghi\u1ec7p \u00e1p d\u1ee5ng tu\u1ea7n l\u00e0m vi\u1ec7c ti\u00eau chu\u1ea9n 40 gi\u1edd ${source.marker}.`
      : noAnswerSentinel;
  }

  if (
    includesAll("ngh\u1ec9 ph\u00e9p", "bao nhi\u00eau ng\u00e0y")(question) ||
    includesAll("m\u1ed9t n\u0103m", "ngh\u1ec9 ph\u00e9p")(question) ||
    includesAll("ngh\u1ec9 h\u1eb1ng n\u0103m", "bao nhi\u00eau ng\u00e0y")(question) ||
    includesAll("nguy\u00ean l\u01b0\u01a1ng", "bao nhi\u00eau ng\u00e0y")(question)
  ) {
    const source = findSource(sources, [
      includesAny("ngh\u1ec9 h\u1eb1ng n\u0103m", "ngh\u1ec9 ph\u00e9p n\u0103m"),
      includesAny("12 ng\u00e0y"),
    ]);
    return source
      ? `Ng\u01b0\u1eddi lao \u0111\u1ed9ng l\u00e0m vi\u1ec7c trong \u0111i\u1ec1u ki\u1ec7n b\u00ecnh th\u01b0\u1eddng \u0111\u01b0\u1ee3c ngh\u1ec9 h\u1eb1ng n\u0103m 12 ng\u00e0y h\u01b0\u1edfng nguy\u00ean l\u01b0\u01a1ng ${source.marker}.`
      : noAnswerSentinel;
  }

  if (includesAny("5 n\u0103m", "05 n\u0103m", "\u0111\u1ee7 n\u0103m n\u0103m")(question)) {
    const source = findSource(sources, [
      includesAny("ngh\u1ec9 h\u1eb1ng n\u0103m", "ngh\u1ec9 ph\u00e9p n\u0103m"),
      includesAny("05 n\u0103m", "5 n\u0103m", "t\u0103ng th\u00eam 01 ng\u00e0y", "t\u0103ng th\u00eam m\u1ed9t ng\u00e0y"),
    ]);
    return source
      ? `N\u1ebfu l\u00e0m \u0111\u1ee7 05 n\u0103m cho c\u00f9ng m\u1ed9t ng\u01b0\u1eddi s\u1eed d\u1ee5ng lao \u0111\u1ed9ng, ng\u01b0\u1eddi lao \u0111\u1ed9ng \u0111\u01b0\u1ee3c t\u0103ng th\u00eam 01 ng\u00e0y ngh\u1ec9 h\u1eb1ng n\u0103m ${source.marker}.`
      : noAnswerSentinel;
  }

  if (
    includesAll("ceo", "nova")(question) ||
    includesAll("gi\u00e1m \u0111\u1ed1c \u0111i\u1ec1u h\u00e0nh", "nova")(question)
  ) {
    const source = findSource(sources, [
      includesAny("ceo", "gi\u00e1m \u0111\u1ed1c \u0111i\u1ec1u h\u00e0nh"),
      includesAny("nguy\u1ec5n anh khoa"),
    ]);
    return source ? `CEO Nova Digital l\u00e0 Nguy\u1ec5n Anh Khoa ${source.marker}.` : noAnswerSentinel;
  }

  if (isCtoQuestion(question)) {
    if (mentionsUnsupportedOrganization(question)) {
      return noAnswerSentinel;
    }
    const source = findNovaCtoSource(sources);
    return source ? `CTO Nova Digital l\u00e0 L\u00ea Thu H\u00e0 ${source.marker}.` : noAnswerSentinel;
  }

  if (isNovaAssistQuestion(question)) {
    if (mentionsUnsupportedOrganization(question)) {
      return noAnswerSentinel;
    }
    const source = findNovaAssistSource(sources);
    return source ? novaAssistAnswer(source) : noAnswerSentinel;
  }

  if (includesAll("l\u00e0m th\u00eam gi\u1edd", "ngh\u1ec9 ph\u00e9p")(question)) {
    const overtimeSource = findSource(sources, [
      includesAny("l\u00e0m th\u00eam gi\u1edd"),
      includesAny("40 gi\u1edd/th\u00e1ng", "200 gi\u1edd/n\u0103m", "300 gi\u1edd/n\u0103m"),
    ]);
    const leaveSource = findSource(sources, [
      includesAny("ngh\u1ec9 h\u1eb1ng n\u0103m", "ngh\u1ec9 ph\u00e9p n\u0103m"),
      includesAny("12 ng\u00e0y"),
    ]);
    if (overtimeSource && leaveSource) {
      return `L\u00e0m th\u00eam gi\u1edd ph\u1ea3i c\u00f3 nhu c\u1ea7u c\u00f4ng vi\u1ec7c th\u1ef1c t\u1ebf, \u0111\u01b0\u1ee3c ph\u00ea duy\u1ec7t tr\u01b0\u1edbc v\u00e0 c\u00f3 s\u1ef1 \u0111\u1ed3ng \u00fd c\u1ee7a ng\u01b0\u1eddi lao \u0111\u1ed9ng; gi\u1edd l\u00e0m th\u00eam kh\u00f4ng qu\u00e1 40 gi\u1edd/th\u00e1ng v\u00e0 th\u00f4ng th\u01b0\u1eddng kh\u00f4ng qu\u00e1 200 gi\u1edd/n\u0103m, tr\u1eeb tr\u01b0\u1eddng h\u1ee3p \u0111\u01b0\u1ee3c \u00e1p d\u1ee5ng 300 gi\u1edd/n\u0103m theo ph\u00e1p lu\u1eadt ${overtimeSource.marker}. V\u1ec1 ngh\u1ec9 ph\u00e9p, ng\u01b0\u1eddi lao \u0111\u1ed9ng l\u00e0m vi\u1ec7c trong \u0111i\u1ec1u ki\u1ec7n b\u00ecnh th\u01b0\u1eddng \u0111\u01b0\u1ee3c ngh\u1ec9 h\u1eb1ng n\u0103m 12 ng\u00e0y h\u01b0\u1edfng nguy\u00ean l\u01b0\u01a1ng ${leaveSource.marker}.`;
    }
    return noAnswerSentinel;
  }

  return noAnswerSentinel;
}

function groundedContentForAnswer(answer) {
  if (answer === noAnswerSentinel) {
    return answer;
  }
  const citations = [];
  const answerText = answer
    .replace(/\s*\[SOURCE_([1-9][0-9]*)\]/g, (_match, index) => {
      const identifier = `SOURCE_${index}`;
      if (!citations.includes(identifier)) {
        citations.push(identifier);
      }
      return "";
    })
    .replace(/\s+\./g, ".")
    .replace(/\s+/g, " ")
    .trim();
  return JSON.stringify({ answer: answerText, citations });
}

function sendJson(response, status, payload) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  response.end(JSON.stringify(payload));
}

function readBody(request) {
  return new Promise((resolve, reject) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      body += chunk;
      if (body.length > 128_000) {
        reject(new Error("request too large"));
        request.destroy();
      }
    });
    request.on("end", () => resolve(body));
    request.on("error", reject);
  });
}

async function handleChatCompletions(request, response) {
  let payload;
  try {
    const body = await readBody(request);
    payload = body ? JSON.parse(body) : {};
  } catch {
    sendJson(response, 400, { error: { message: "Malformed request." } });
    return;
  }

  const answer = answerForPayload(payload);
  const content = groundedContentForAnswer(answer);

  if (payload.stream) {
    response.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    });
    response.write(`data: ${JSON.stringify({ choices: [{ delta: { content }, finish_reason: null }] })}\n\n`);
    response.write(
      `data: ${JSON.stringify({
        choices: [{ delta: {}, finish_reason: "stop" }],
        model,
        usage: { prompt_tokens: 12, completion_tokens: 18, total_tokens: 30 },
      })}\n\n`,
    );
    response.end("data: [DONE]\n\n");
    return;
  }

  await new Promise((resolve) => setTimeout(resolve, Number.isFinite(delayMs) ? delayMs : 0));
  sendJson(response, 200, {
    id: "uat-chat-completion",
    object: "chat.completion",
    model,
    choices: [
      {
        index: 0,
        message: { role: "assistant", content },
        finish_reason: "stop",
      },
    ],
    usage: { prompt_tokens: 12, completion_tokens: 18, total_tokens: 30 },
  });
}

export function createFakeOpenAIProviderServer() {
  return createServer((request, response) => {
    const url = new URL(request.url ?? "/", "http://localhost");
    if (request.method === "GET" && url.pathname === "/health") {
      sendJson(response, 200, { status: "ok" });
      return;
    }
    if (request.method === "POST" && url.pathname === "/v1/chat/completions") {
      void handleChatCompletions(request, response);
      return;
    }
    sendJson(response, 404, { error: { message: "Not found." } });
  });
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  createFakeOpenAIProviderServer().listen(port, "0.0.0.0", () => {
    console.log(`UAT fake OpenAI-compatible provider listening on ${port}`);
  });
}
