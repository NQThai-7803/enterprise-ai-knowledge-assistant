import { createServer } from "node:http";

const port = Number.parseInt(process.env.PORT ?? "18080", 10);
const delayMs = Number.parseInt(process.env.FAKE_LLM_DELAY_MS ?? "250", 10);
const model = "uat-deterministic-model";
const noAnswerSentinel = "__NO_ANSWER__";

function normalizeText(value) {
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
  return (text) => needles.some((needle) => text.includes(normalizeText(needle)));
}

function includesAll(...needles) {
  return (text) => needles.every((needle) => text.includes(normalizeText(needle)));
}

function answerForPayload(payload) {
  const prompt = latestUserPrompt(payload);
  const question = normalizeText(currentQuestion(prompt));
  const sources = sourceBlocks(prompt);

  if (includesAny("travel approval", "công tác", "du lịch", "đi công tác")(question)) {
    const source = findSource(sources, [
      includesAny("uat travel approval policy", "travel approval"),
      includesAny("manager approval", "booking travel"),
    ]);
    return source
      ? `The UAT travel approval policy requires manager approval before booking travel and expense evidence after the trip ${source.marker}.`
      : noAnswerSentinel;
  }

  if (includesAll("thời gian", "làm việc")(question) || includesAll("lịch", "làm việc", "tiêu chuẩn")(question)) {
    const scheduleSource = findSource(sources, [
      includesAny("08:00 - 12:00", "08:00–12:00"),
      includesAny("13:00 - 17:00", "13:00–17:00"),
      includesAny("40 giờ"),
    ]);
    const legalLimitSource = findSource(sources, [includesAny("08 giờ/ngày", "48 giờ/tuần")]);
    const source = scheduleSource ?? legalLimitSource;
    return source
      ? `Thời gian làm việc tiêu chuẩn là Thứ Hai đến Thứ Sáu, buổi sáng 08:00 - 12:00, buổi chiều 13:00 - 17:00, tổng 08 giờ/ngày. Doanh nghiệp áp dụng tuần làm việc tiêu chuẩn 40 giờ ${source.marker}.`
      : noAnswerSentinel;
  }

  if (includesAll("nghỉ phép", "bao nhiêu ngày")(question) || includesAll("một năm", "nghỉ phép")(question)) {
    const source = findSource(sources, [
      includesAny("nghỉ hằng năm", "nghỉ phép năm"),
      includesAny("12 ngày"),
    ]);
    return source
      ? `Người lao động làm việc trong điều kiện bình thường được nghỉ hằng năm 12 ngày hưởng nguyên lương ${source.marker}.`
      : noAnswerSentinel;
  }

  if (includesAll("làm thêm giờ", "nghỉ phép")(question)) {
    const overtimeSource = findSource(sources, [
      includesAny("làm thêm giờ"),
      includesAny("40 giờ/tháng", "200 giờ/năm", "300 giờ/năm"),
    ]);
    const leaveSource = findSource(sources, [
      includesAny("nghỉ hằng năm", "nghỉ phép năm"),
      includesAny("12 ngày"),
    ]);
    if (overtimeSource && leaveSource) {
      return `Làm thêm giờ phải có nhu cầu công việc thực tế, được phê duyệt trước và có sự đồng ý của người lao động; giờ làm thêm không quá 40 giờ/tháng và thông thường không quá 200 giờ/năm, trừ trường hợp được áp dụng 300 giờ/năm theo pháp luật ${overtimeSource.marker}. Về nghỉ phép, người lao động làm việc trong điều kiện bình thường được nghỉ hằng năm 12 ngày hưởng nguyên lương ${leaveSource.marker}.`;
    }
    return noAnswerSentinel;
  }

  return noAnswerSentinel;
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

  if (payload.stream) {
    response.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    });
    response.write(`data: ${JSON.stringify({ choices: [{ delta: { content: answer }, finish_reason: null }] })}\n\n`);
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
        message: { role: "assistant", content: answer },
        finish_reason: "stop",
      },
    ],
    usage: { prompt_tokens: 12, completion_tokens: 18, total_tokens: 30 },
  });
}

createServer((request, response) => {
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
}).listen(port, "0.0.0.0", () => {
  console.log(`UAT fake OpenAI-compatible provider listening on ${port}`);
});