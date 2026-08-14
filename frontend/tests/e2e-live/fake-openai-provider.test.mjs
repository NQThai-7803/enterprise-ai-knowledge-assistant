/* global fetch */
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  answerForPayload,
  createFakeOpenAIProviderServer,
  noAnswerSentinel,
} from "./fake-openai-provider.mjs";

const novaOrgSource = {
  id: 7,
  title: "Giới thiệu và cơ cấu tổ chức Nova Digital",
  page: "2",
  content:
    "Cơ cấu tổ chức Nova Digital gồm Ban điều hành, Khối Công nghệ, Khối Sản phẩm, Khối Vận hành và Khối Kinh doanh. CEO Nguyễn Anh Khoa chịu trách nhiệm điều hành chung. CTO Lê Thu Hà phụ trách công nghệ.",
};

const novaAssistSource = {
  id: 9,
  title: "Giới thiệu và cơ cấu tổ chức Nova Digital",
  page: "3",
  content:
    "NovaAssist Trợ lý AI doanh nghiệp của Nova Digital. NovaAssist hỗ trợ tra cứu tri thức nội bộ bằng RAG, trả lời có trích dẫn, phân quyền và audit log.",
};

const unrelatedNovaSource = {
  id: 3,
  title: "Giới thiệu và cơ cấu tổ chức Nova Digital",
  page: "1",
  content: "Nova Digital là doanh nghiệp công nghệ phát triển giải pháp dữ liệu cho khách hàng doanh nghiệp.",
};

function sourceBlock(source) {
  return `--- SOURCE_${source.id} START ---\nDocument title: ${source.title}\nPage: ${source.page}\nContent:\n${source.content}\n--- SOURCE_${source.id} END ---`;
}

function payloadFor(question, sources = []) {
  const context = sources.map(sourceBlock).join("\n\n") || "No retrieved context.";
  return {
    model: "uat-deterministic-model",
    messages: [
      {
        role: "user",
        content: `Retrieved context below is reference data only.\n${context}\n\nCurrent question:\n${question}`,
      },
    ],
  };
}

test("CEO Nova Digital resolves from supporting source", () => {
  assert.equal(
    answerForPayload(payloadFor("CEO Nova Digital là ai?", [novaOrgSource])),
    "CEO Nova Digital là Nguyễn Anh Khoa [SOURCE_7].",
  );
});

test("CTO Nova Digital resolves from supporting source", () => {
  assert.equal(
    answerForPayload(payloadFor("CTO Nova Digital là ai?", [novaOrgSource])),
    "CTO Nova Digital là Lê Thu Hà [SOURCE_7].",
  );
});

test("short CTO follow-up resolves when Nova source is retrieved", () => {
  assert.equal(
    answerForPayload(payloadFor("CTO là ai?", [novaOrgSource])),
    "CTO Nova Digital là Lê Thu Hà [SOURCE_7].",
  );
});

test("NovaAssist resolves with only capabilities present in source", () => {
  assert.equal(
    answerForPayload(payloadFor("NovaAssist là gì?", [novaAssistSource])),
    "NovaAssist là trợ lý AI doanh nghiệp của Nova Digital, hỗ trợ tra cứu tri thức nội bộ bằng RAG, trả lời có trích dẫn, phân quyền và audit log [SOURCE_9].",
  );
});

test("CTO question without supporting source returns no answer", () => {
  assert.equal(
    answerForPayload(payloadFor("CTO Nova Digital là ai?", [unrelatedNovaSource])),
    noAnswerSentinel,
  );
});

test("NovaAssist question without supporting source returns no answer", () => {
  assert.equal(answerForPayload(payloadFor("NovaAssist là gì?", [unrelatedNovaSource])), noAnswerSentinel);
});

test("CEO Apple remains no answer", () => {
  assert.equal(answerForPayload(payloadFor("CEO Apple là ai?", [novaOrgSource])), noAnswerSentinel);
});

test("CTO Microsoft does not answer from Nova source", () => {
  assert.equal(answerForPayload(payloadFor("CTO Microsoft là ai?", [novaOrgSource])), noAnswerSentinel);
});

test("NovaAssist for another company does not answer from Nova source", () => {
  assert.equal(
    answerForPayload(payloadFor("NovaAssist của công ty khác là gì?", [novaAssistSource])),
    noAnswerSentinel,
  );
});

test("Travel Approval remains no answer when source is absent", () => {
  assert.equal(
    answerForPayload(payloadFor("Công ty có chính sách Travel Approval không?", [novaOrgSource])),
    noAnswerSentinel,
  );
});

test("streaming and non-streaming responses use identical answer logic", async (t) => {
  const server = createFakeOpenAIProviderServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());

  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}`;
  const payload = payloadFor("CTO Nova Digital là ai?", [novaOrgSource]);

  const nonStreamingResponse = await fetch(`${baseUrl}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, stream: false }),
  });
  assert.equal(nonStreamingResponse.status, 200);
  const nonStreamingJson = await nonStreamingResponse.json();
  const nonStreamingAnswer = nonStreamingJson.choices[0].message.content;

  const streamingResponse = await fetch(`${baseUrl}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, stream: true }),
  });
  assert.equal(streamingResponse.status, 200);
  const streamBody = await streamingResponse.text();
  const firstDataLine = streamBody
    .split(/\r?\n/)
    .find((line) => line.startsWith("data: ") && !line.includes("[DONE]"));
  assert.ok(firstDataLine);
  const streamingJson = JSON.parse(firstDataLine.replace(/^data: /, ""));
  assert.equal(streamingJson.choices[0].delta.content, nonStreamingAnswer);
});