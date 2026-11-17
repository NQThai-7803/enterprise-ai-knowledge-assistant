import { describe, expect, it } from "vitest";
import { formatBytes, formatDateTime } from "./format";

describe("format helpers", () => {
  it("formats dates as dd/MM/yyyy HH:mm in local time", () => {
    expect(formatDateTime("2026-11-16T14:05:00")).toBe("16/11/2026 14:05");
  });

  it("uses Vietnamese for missing or invalid values", () => {
    expect(formatDateTime(null)).toBe("Không có");
    expect(formatDateTime("not-a-date")).toBe("Không có");
    expect(formatBytes(-1)).toBe("Không có");
  });
});
