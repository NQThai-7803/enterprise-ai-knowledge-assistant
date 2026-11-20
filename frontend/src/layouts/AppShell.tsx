import {
  Activity,
  AlignLeft,
  Box,
  Building2,
  FileText,
  LogOut,
  Menu,
  MessageCircle,
  ThumbsUp,
  type LucideIcon,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { AuthenticatedUser, UserRole } from "../api/types";
import { initials } from "../lib/format";
import { roleLabel } from "../lib/permissions";
import { useAuth } from "../features/auth/AuthProvider";
import { safeErrorMessage } from "../api/errors";
import { useToast } from "../components/feedback/ToastProvider";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  roles?: UserRole[];
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    title: "Làm việc",
    items: [
      { to: "/chat", label: "Trò chuyện", icon: MessageCircle },
      { to: "/documents", label: "Tài liệu", icon: FileText },
    ],
  },
  {
    title: "Quản trị",
    items: [
      { to: "/users", label: "Người dùng", icon: Users, roles: ["ADMIN"] },
      { to: "/departments", label: "Phòng ban", icon: Building2, roles: ["ADMIN"] },
      { to: "/feedback", label: "Phản hồi", icon: ThumbsUp, roles: ["ADMIN", "MANAGER"] },
      { to: "/audit-logs", label: "Nhật ký hệ thống", icon: AlignLeft, roles: ["ADMIN"] },
    ],
  },
  {
    title: "Tài khoản",
    items: [
      { to: "/system", label: "Trạng thái hệ thống", icon: Activity },
      { to: "/profile", label: "Hồ sơ", icon: UserRound },
    ],
  },
];

interface ApiStatus {
  label: string;
  dotClassName: string;
}

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pushToast } = useToast();
  const [mobileOpen, setMobileOpen] = useState(false);

  const readyQuery = useQuery({
    queryKey: ["health", "ready"],
    queryFn: apiClient.health.ready,
    refetchInterval: 30_000,
    retry: 1,
  });

  // D-6: the old top-bar "API ready" badge lives on as a small status dot in the sidebar.
  const apiStatus: ApiStatus = readyQuery.isError
    ? { label: "API không phản hồi", dotClassName: "bg-danger" }
    : readyQuery.data?.status === "ready"
      ? { label: "API sẵn sàng", dotClassName: "bg-success" }
      : readyQuery.data
        ? { label: "API chưa sẵn sàng", dotClassName: "bg-warning" }
        : { label: "Đang kiểm tra API", dotClassName: "bg-warning" };

  useEffect(() => {
    if (!mobileOpen) {
      return undefined;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [mobileOpen]);

  const handleLogout = async () => {
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (error) {
      pushToast({ tone: "error", title: "Đăng xuất thất bại", message: safeErrorMessage(error) });
    }
  };

  return (
    <div className="min-h-[100dvh] bg-canvas text-ink lg:grid lg:grid-cols-[var(--sidebar-width)_minmax(0,1fr)]">
      <aside className="hidden border-r border-border bg-surface lg:sticky lg:top-0 lg:flex lg:h-[100dvh] lg:flex-col">
        <SidebarContent user={user} apiStatus={apiStatus} onNavigate={() => undefined} onLogout={handleLogout} />
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 bg-ink/40 lg:hidden" role="presentation" onClick={() => setMobileOpen(false)}>
          <aside
            className="h-full w-[min(17rem,85vw)] bg-surface shadow-panel"
            onClick={(event) => event.stopPropagation()}
          >
            <SidebarContent
              user={user}
              apiStatus={apiStatus}
              onNavigate={() => setMobileOpen(false)}
              onLogout={handleLogout}
              onClose={() => setMobileOpen(false)}
            />
          </aside>
        </div>
      ) : null}

      <div className="min-w-0">
        <div className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-surface px-4 lg:hidden">
          <button
            type="button"
            className="rounded-token p-2 text-ink transition hover:bg-canvas"
            onClick={() => setMobileOpen(true)}
            aria-label="Mở điều hướng"
          >
            <Menu className="h-5 w-5" aria-hidden={true} />
          </button>
          <Brand />
        </div>
        <main className="mx-auto max-w-[1500px] px-4 py-6 lg:px-10 lg:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-token bg-accent text-accent-contrast">
        <Box className="h-4 w-4" aria-hidden={true} />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold">EAKA</p>
        <p className="text-xs text-muted">Knowledge Assistant</p>
      </div>
    </div>
  );
}

function SidebarContent({
  user,
  apiStatus,
  onNavigate,
  onLogout,
  onClose,
}: {
  user: AuthenticatedUser | null;
  apiStatus: ApiStatus;
  onNavigate: () => void;
  onLogout: () => void;
  onClose?: () => void;
}) {
  const groups = navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.roles || (user !== null && item.roles.includes(user.role))),
    }))
    .filter((group) => group.items.length > 0);

  return (
    <div className="flex h-full flex-col overflow-y-auto px-3.5 py-5 text-sm">
      <div className="flex items-center justify-between gap-2 px-2.5 pb-[18px] pt-1">
        <Brand />
        {onClose ? (
          <button
            type="button"
            className="rounded-token p-2 text-muted transition hover:bg-canvas hover:text-ink"
            onClick={onClose}
            aria-label="Đóng điều hướng"
          >
            <X className="h-5 w-5" aria-hidden={true} />
          </button>
        ) : null}
      </div>

      <nav aria-label="Điều hướng chính" className="flex flex-col">
        {groups.map((group) => (
          <div key={group.title} className="flex flex-col gap-0.5 pb-3">
            <p className="px-2.5 pb-1 pt-1.5 text-[11px] font-medium uppercase tracking-[0.04em] text-muted">
              {group.title}
            </p>
            {group.items.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    `flex min-h-[38px] items-center gap-2.5 rounded-token px-2.5 transition ${
                      isActive ? "bg-accent/10 font-medium text-accent-strong" : "text-ink/80 hover:bg-canvas"
                    }`
                  }
                >
                  <Icon className="h-4 w-4 shrink-0" aria-hidden={true} />
                  {item.label}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="flex-1" />

      <p className="flex items-center gap-2 px-2.5 pb-3 text-xs text-muted">
        <span className={`h-2 w-2 shrink-0 rounded-full ${apiStatus.dotClassName}`} aria-hidden={true} />
        {apiStatus.label}
      </p>
      <div className="flex items-center gap-2.5 border-t border-border/70 px-2.5 pt-3">
        <div
          className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full bg-border/50 text-xs font-semibold text-ink/80"
          aria-hidden={true}
        >
          {initials(user?.full_name)}
        </div>
        <div className="min-w-0 flex-1 leading-tight">
          <p className="truncate text-[13px] font-medium">{user?.full_name}</p>
          {/* BR-4: the caller's own department name, from /auth/me. */}
          <p className="truncate text-xs text-muted">
            {user ? [roleLabel(user.role), user.department_name].filter(Boolean).join(" · ") : null}
          </p>
        </div>
        <button
          type="button"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-token text-muted transition hover:bg-canvas hover:text-ink"
          onClick={onLogout}
          aria-label="Đăng xuất"
          title="Đăng xuất"
        >
          <LogOut className="h-4 w-4" aria-hidden={true} />
        </button>
      </div>
    </div>
  );
}
