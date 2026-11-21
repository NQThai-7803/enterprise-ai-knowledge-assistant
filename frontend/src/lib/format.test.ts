import { describe, expect, it } from "vitest";
import { formatBytes, formatDateTime, formatIsoDate, initials } from "./format";

describe("format helpers", () => {
  it("formats dates as dd/MM/yyyy HH:mm in local time", () => {
    expect(formatDateTime("2026-11-16T14:05:00")).toBe("16/11/2026 14:05");
  });

  it("uses Vietnamese for missing or invalid values", () => {
    expect(formatDateTime(null)).toBe("Không có");
    expect(formatDateTime("not-a-date")).toBe("Không có");
    expect(formatBytes(-1)).toBe("Không có");
  });

  it("formats calendar dates without a timezone shift", () => {
    expect(formatIsoDate("2026-09-01")).toBe("01/09/2026");
    expect(formatIsoDate(null)).toBe("Không có");
    expect(formatIsoDate("2026-09-01T00:00:00Z")).toBe("Không có");
  });

  it("builds avatar initials from the first and last word", () => {
    expect(initials("Staff Nhân sự")).toBe("SS");
    expect(initials("  đỗ   minh ")).toBe("ĐM");
    expect(initials("Admin")).toBe("A");
    expect(initials("")).toBe("?");
    expect(initials(undefined)).toBe("?");
  });
});
