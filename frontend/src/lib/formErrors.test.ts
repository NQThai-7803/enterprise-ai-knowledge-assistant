import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/errors";
import { applyFieldErrors } from "./formErrors";

// BR-10 contract example: upload with effective_to before effective_from.
const rangeError = new ApiError({
  code: "VALIDATION_ERROR",
  message: "effective_to must not precede effective_from.",
  status: 422,
  details: [
    { field: "effective_to", code: "INVALID_RANGE", message: "effective_to must not precede effective_from." },
    { field: null, code: "INVALID_JSON", message: "Body is not valid JSON." },
    { field: "unknown_on_this_form", code: "TOO_LONG", message: "Too long." },
  ],
});

describe("applyFieldErrors", () => {
  it("puts details on their fields in Vietnamese and returns the rest", () => {
    const setError = vi.fn();
    const result = applyFieldErrors(rangeError, setError, ["title", "effective_to"], {
      "effective_to.INVALID_RANGE": "Ngày hết hiệu lực không được trước ngày bắt đầu hiệu lực.",
    });

    expect(setError).toHaveBeenCalledWith("effective_to", {
      type: "server",
      message: "Ngày hết hiệu lực không được trước ngày bắt đầu hiệu lực.",
    });
    expect(result).toEqual({
      fields: ["effective_to"],
      rest: ["Dữ liệu gửi lên không đúng định dạng.", "Nội dung quá dài."],
    });
  });

  it("returns null for errors without details, so pages keep their own handling", () => {
    const setError = vi.fn();
    expect(applyFieldErrors(new ApiError({ code: "FORBIDDEN", message: "x", status: 403 }), setError, ["title"])).toBeNull();
    expect(applyFieldErrors(new Error("network"), setError, ["title"])).toBeNull();
    expect(setError).not.toHaveBeenCalled();
  });
});
