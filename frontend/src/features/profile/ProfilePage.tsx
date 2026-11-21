import type { ReactNode } from "react";
import type { AuthenticatedUser } from "../../api/types";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { initials } from "../../lib/format";
import { roleLabel } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";

export function ProfilePage() {
  const { user } = useAuth();
  if (!user) {
    return null;
  }

  return (
    <div>
      <PageHeader title="Hồ sơ" />
      <section className="max-w-2xl rounded-xl border border-border/70 bg-surface p-6" aria-label="Thông tin tài khoản">
        <div className="flex flex-wrap items-center gap-4 border-b border-border/70 pb-5">
          <span
            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-accent/10 text-lg font-semibold text-accent-strong"
            aria-hidden="true"
          >
            {initials(user.full_name)}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-lg font-semibold text-ink">{user.full_name}</p>
            <p className="truncate text-sm text-muted">{user.email}</p>
          </div>
          <Badge tone={user.is_active ? "success" : "neutral"}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
            {user.is_active ? "Hoạt động" : "Vô hiệu hóa"}
          </Badge>
        </div>
        <dl className="grid gap-4 py-5 sm:grid-cols-2">
          <Detail label="Vai trò" value={roleLabel(user.role)} />
          {/* BR-4: department_name of the caller's own department, null without one. */}
          <Detail label="Phòng ban" value={user.department_name ?? "Chưa thuộc phòng ban"} />
        </dl>
        <p className="rounded-token bg-elevated px-4 py-3 text-sm leading-6 text-ink/80">
          {accessSummary(user)} Muốn đổi mật khẩu hoặc phòng ban, hãy liên hệ quản trị viên.
        </p>
      </section>
    </div>
  );
}

function accessSummary(user: AuthenticatedUser): string {
  if (user.role === "ADMIN") {
    return "Bạn xem được mọi tài liệu và quản lý người dùng, phòng ban, phân quyền.";
  }
  const department = user.department_name ? `, tài liệu của phòng ${user.department_name}` : "";
  const base = `Bạn xem được tài liệu toàn công ty${department} và tài liệu được cấp quyền trực tiếp.`;
  if (user.role === "MANAGER" && user.department_name) {
    return `${base} Bạn tải lên được tài liệu riêng tư hoặc cho phòng ${user.department_name}.`;
  }
  return base;
}

function Detail({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-1 text-sm text-ink">{value}</dd>
    </div>
  );
}
