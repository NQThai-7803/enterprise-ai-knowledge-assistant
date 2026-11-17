import { describe, expect, it } from "vitest";
import { splitAnswerSegments } from "./answerSegments";

const VI = "Chưa xác minh được từ tài liệu bạn được phép truy cập";
const EN = "Could not be verified from the documents you can access";

describe("splitAnswerSegments", () => {
  it("keeps an answer without the fixed sentence as one plain segment", () => {
    expect(splitAnswerSegments("Ngân sách là 1.200.000.000 đồng [1].")).toEqual([
      { text: "Ngân sách là 1.200.000.000 đồng [1].", unverified: false },
    ]);
  });

  it("separates a Vietnamese unverified sentence from cited text", () => {
    expect(splitAnswerSegments(`Được mượn 6 cuốn [1]. ${VI}: tiền đặt cọc.`)).toEqual([
      { text: "Được mượn 6 cuốn [1]. ", unverified: false },
      { text: `${VI}: tiền đặt cọc.`, unverified: true },
    ]);
  });

  it("recognises the English sentence and stops at a line break", () => {
    expect(splitAnswerSegments(`A [1].\n${EN}: the fee\nB [2].`)).toEqual([
      { text: "A [1].\n", unverified: false },
      { text: `${EN}: the fee`, unverified: true },
      { text: "\nB [2].", unverified: false },
    ]);
  });

  it("does not end the sentence at dots inside numbers", () => {
    const sentence = `${VI}: khoản 1.200.000 đồng.`;
    expect(splitAnswerSegments(sentence)).toEqual([{ text: sentence, unverified: true }]);
  });

  it("leaves a matching sentence with a citation marker as plain text", () => {
    const cited = `${VI}: [1]`;
    expect(splitAnswerSegments(cited)).toEqual([{ text: cited, unverified: false }]);
  });

  it("does not match other wording", () => {
    const other = "Không xác minh được từ tài liệu bạn được phép truy cập: tiền cọc.";
    expect(splitAnswerSegments(other)).toEqual([{ text: other, unverified: false }]);
  });

  it("finds every unverified sentence and loses no text", () => {
    const content = `Ý một [1]. ${VI}: ý hai. ${VI}: ý ba?`;
    const segments = splitAnswerSegments(content);
    expect(segments.filter((segment) => segment.unverified)).toHaveLength(2);
    expect(segments.map((segment) => segment.text).join("")).toBe(content);
  });

  it("returns no segments for empty content", () => {
    expect(splitAnswerSegments("")).toEqual([]);
  });
});
