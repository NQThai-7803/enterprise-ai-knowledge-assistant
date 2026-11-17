// Fixed sentence the backend writes for a part of the question it could not verify
// (grounded_answer_service `_UNVERIFIED_PART_SENTENCE`, simple-mode prompt), in Vietnamese or English.
// TODO(BR-3): switch to a structured field once API_SPEC defines one; until then match the prefixes.
const UNVERIFIED_PREFIXES = [
  "Chưa xác minh được từ tài liệu bạn được phép truy cập",
  "Could not be verified from the documents you can access",
];

const PREFIX_PATTERN = new RegExp(
  UNVERIFIED_PREFIXES.map((prefix) => prefix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"),
  "giu",
);
// A sentence ends at . ! ? followed by whitespace or the end, or at a line break ("1.200.000" does not end it).
const SENTENCE_END = /[.!?](?=\s|$)|\n/gu;
const CITATION_MARKER = /\[\d+\]/;

export interface AnswerSegment {
  text: string;
  unverified: boolean;
}

/**
 * Splits an assistant answer into plain text and "could not be verified" sentences.
 * A matching sentence that carries a citation marker is a validated claim, so it stays plain.
 * Joining every segment's text gives back the (NFC-normalised) input.
 */
export function splitAnswerSegments(content: string): AnswerSegment[] {
  const text = content.normalize("NFC");
  const segments: AnswerSegment[] = [];
  let cursor = 0;

  for (const match of text.matchAll(PREFIX_PATTERN)) {
    const start = match.index;
    if (start < cursor) {
      continue;
    }
    SENTENCE_END.lastIndex = start + match[0].length;
    const endMatch = SENTENCE_END.exec(text);
    const end = !endMatch ? text.length : endMatch[0] === "\n" ? endMatch.index : endMatch.index + 1;
    const sentence = text.slice(start, end);
    if (CITATION_MARKER.test(sentence)) {
      continue;
    }
    if (start > cursor) {
      segments.push({ text: text.slice(cursor, start), unverified: false });
    }
    segments.push({ text: sentence, unverified: true });
    cursor = end;
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), unverified: false });
  }
  return segments;
}
