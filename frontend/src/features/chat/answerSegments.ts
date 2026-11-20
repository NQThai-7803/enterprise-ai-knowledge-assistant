// BR-3 contract (API_SPEC §8): a sentence naming an unverified part contains "chưa xác minh được",
// "không xác minh được" or "could not be verified", matched case- and accent-insensitively; the
// server strips its source markers. The model writes these sentences, so match the phrase, not a prefix.
// TODO(BR-3 segments): switch to segments[].kind once that field is on main.
const UNVERIFIED_PHRASES = ["chua xac minh duoc", "khong xac minh duoc", "could not be verified"];

// A sentence ends at . ! ? followed by whitespace or the end, or at a line break ("1.200.000" does not end it).
const SENTENCE_END = /[.!?](?=\s|$)|\n/gu;
const CITATION_MARKER = /\[\d+\]/;

export interface AnswerSegment {
  text: string;
  unverified: boolean;
}

function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase();
}

function isUnverified(sentence: string): boolean {
  const folded = fold(sentence);
  // A sentence that kept a citation marker is a validated claim (the contract's number exception).
  return UNVERIFIED_PHRASES.some((phrase) => folded.includes(phrase)) && !CITATION_MARKER.test(sentence);
}

/**
 * Splits an assistant answer into plain text and "could not be verified" sentences.
 * Joining every segment's text gives back the (NFC-normalised) input.
 */
export function splitAnswerSegments(content: string): AnswerSegment[] {
  const text = content.normalize("NFC");
  const segments: AnswerSegment[] = [];
  const push = (part: string, unverified: boolean) => {
    if (!part) {
      return;
    }
    const last = segments[segments.length - 1];
    if (last && last.unverified === unverified) {
      last.text += part;
    } else {
      segments.push({ text: part, unverified });
    }
  };
  const pushSentence = (sentence: string) => {
    const leading = /^\s*/u.exec(sentence)?.[0] ?? "";
    push(leading, false);
    const body = sentence.slice(leading.length);
    push(body, isUnverified(body));
  };

  let start = 0;
  for (const match of text.matchAll(SENTENCE_END)) {
    const end = match[0] === "\n" ? match.index : match.index + 1;
    pushSentence(text.slice(start, end));
    start = end;
  }
  pushSentence(text.slice(start));
  return segments;
}
