import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { isApiError } from "../api/errors";
import type { ValidationDetail } from "../api/types";

// BR-10: Vietnamese text for each stable detail code; the English `message` is never shown.
const DETAIL_TEXT: Record<string, string> = {
  REQUIRED: "Trường này là bắt buộc.",
  TOO_LONG: "Nội dung quá dài.",
  TOO_SHORT: "Nội dung quá ngắn.",
  OUT_OF_RANGE: "Giá trị nằm ngoài giới hạn cho phép.",
  INVALID_CHOICE: "Giá trị không nằm trong danh sách cho phép.",
  INVALID_DATE: "Ngày không hợp lệ.",
  INVALID_FORMAT: "Sai định dạng.",
  INVALID_TYPE: "Sai kiểu dữ liệu.",
  INVALID_VALUE: "Giá trị không hợp lệ.",
  INVALID_RANGE: "Khoảng giá trị không hợp lệ.",
  NOT_ALLOWED: "Không được gửi trường này trong trường hợp này.",
  UNKNOWN_FIELD: "Trường này không được hỗ trợ.",
  INVALID_JSON: "Dữ liệu gửi lên không đúng định dạng.",
};
const FALLBACK_TEXT = "Giá trị không hợp lệ.";

function validationDetails(error: unknown): ValidationDetail[] | null {
  if (!isApiError(error) || error.status !== 422 || !Array.isArray(error.details)) {
    return null;
  }
  return error.details.filter(
    (detail): detail is ValidationDetail =>
      typeof detail === "object" && detail !== null && typeof (detail as ValidationDetail).code === "string",
  );
}

/**
 * Puts each 422 detail on its form field. `overrides` gives a field-specific text, keyed "field.CODE".
 * Returns the fields it set and the texts of details that match no field on this form (for a form-level
 * message), or null when the error carries no details, so the caller keeps its own handling.
 */
export function applyFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly Path<T>[],
  overrides: Record<string, string> = {},
): { fields: Path<T>[]; rest: string[] } | null {
  const details = validationDetails(error);
  if (!details) {
    return null;
  }
  const applied: Path<T>[] = [];
  const rest: string[] = [];
  for (const detail of details) {
    const text = overrides[`${detail.field}.${detail.code}`] ?? DETAIL_TEXT[detail.code] ?? FALLBACK_TEXT;
    const field = fields.find((name) => name === detail.field);
    if (field) {
      setError(field, { type: "server", message: text });
      applied.push(field);
    } else {
      rest.push(text);
    }
  }
  return { fields: applied, rest };
}
