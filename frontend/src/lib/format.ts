import { format, formatDistanceToNowStrict } from "date-fns";
import { vi } from "date-fns/locale";

const UNAVAILABLE = "Không có";

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return UNAVAILABLE;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return UNAVAILABLE;
  }
  return format(date, "dd/MM/yyyy HH:mm");
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) {
    return UNAVAILABLE;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return UNAVAILABLE;
  }
  return `${formatDistanceToNowStrict(date, { locale: vi })} trước`;
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return UNAVAILABLE;
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

export function truncateMiddle(value: string, maxLength = 36): string {
  if (value.length <= maxLength) {
    return value;
  }
  const half = Math.floor((maxLength - 3) / 2);
  return `${value.slice(0, half)}...${value.slice(-half)}`;
}

export function initials(name: string | null | undefined): string {
  const parts = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }
  // Array.from keeps a surrogate pair together; first word + last word, like "Staff Nhân sự" -> "SS".
  const first = Array.from(parts[0])[0];
  const last = parts.length > 1 ? Array.from(parts[parts.length - 1])[0] : "";
  return `${first}${last}`.toUpperCase();
}
