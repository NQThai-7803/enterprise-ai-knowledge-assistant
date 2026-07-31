import {
  Activity,
  Building2,
  ClipboardList,
  FileText,
  Library,
  LogOut,
  Menu,
  MessageSquareText,
  ShieldAlert,
  type LucideIcon,
  UserCircle,
  Users,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { UserRole } from "../api/types";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
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

const navItems: NavItem[] = [
  { to: "/chat", label: "Chat", icon: MessageSquareText },
  { to: "/documents", label: "Documents", icon: Library },
  { to: "/users", label: "Users", icon: Users, roles: ["ADMIN"] },
  { to: "/departments", label: "Departments", icon: Building2, roles: ["ADMIN"] },
  { to: "/feedback", label: "Feedback", icon: ClipboardList, roles: ["ADMIN", "MANAGER"] },
  { to: "/audit-logs", label: "Audit logs", icon: ShieldAlert, roles: ["ADMIN"] },
  { to: "/system", label: "System status", icon: Activity },
  { to: "/profile", label: "Profile", icon: UserCircle },
];

const titles: Record<string, string> = {
  "/chat": "AI Chat workspace",
  "/documents": "Document library",
  "/documents/upload": "Document upload",
  "/users": "User management",
  "/departments": "Department management",
  "/feedback": "Feedback management",
  "/audit-logs": "Audit log explorer",
  "/system": "System and LLM status",
  "/profile": "Profile and account",
};

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { pushToast } = useToast();
  const [mobileOpen, setMobileOpen] = useState(false);
  const visibleNav = navItems.filter((item) => !item.roles || (user && item.roles.includes(user.role)));
  const title = pageTitle(location.pathname);

  const readyQuery = useQuery({
    queryKey: ["health", "ready"],
    queryFn: apiClient.health.ready,
    refetchInterval: 30_000,
    retry: 1,
  });

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
      pushToast({ tone: "error", title: "Logout failed", message: safeErrorMessage(error) });
    }
  };

  return (
    <div className="min-h-[100dvh] bg-canvas text-ink lg:grid lg:grid-cols-[var(--sidebar-width)_1fr]">
      <aside className="hidden border-r border-border bg-[rgb(19_27_35)] text-white lg:flex lg:min-h-[100dvh] lg:flex-col">
        <SidebarContent items={visibleNav} userRole={user?.role ?? "STAFF"} onNavigate={() => undefined} />
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" role="presentation" onClick={() => setMobileOpen(false)}>
          <aside className="h-full w-[min(18rem,85vw)] bg-[rgb(19_27_35)] text-white shadow-panel" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-white/10 p-4">
              <span className="font-semibold">Enterprise AI</span>
              <button type="button" className="rounded-token p-2 hover:bg-white/10" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
                <X className="h-5 w-5" aria-hidden={true} />
              </button>
            </div>
            <SidebarContent items={visibleNav} userRole={user?.role ?? "STAFF"} onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      ) : null}

      <div className="min-w-0">
        <header className="sticky top-0 z-30 border-b border-border bg-surface/95 backdrop-blur">
          <div className="flex min-h-16 items-center justify-between gap-3 px-4 lg:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <button type="button" className="rounded-token border border-border p-2 text-ink lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
                <Menu className="h-5 w-5" aria-hidden={true} />
              </button>
              <div className="min-w-0">
                <p className="text-xs font-medium text-muted">Enterprise AI</p>
                <h1 className="truncate text-lg font-semibold text-ink">{title}</h1>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge tone={readyQuery.data?.status === "ready" ? "success" : readyQuery.isError ? "danger" : "warning"}>
                API {readyQuery.data?.status ?? (readyQuery.isError ? "unavailable" : "checking")}
              </Badge>
              <div className="hidden text-right text-sm md:block">
                <p className="font-semibold text-ink">{user?.full_name}</p>
                <p className="text-xs text-muted">{user ? roleLabel(user.role) : "Unknown"}</p>
              </div>
              <Button type="button" variant="ghost" onClick={handleLogout} icon={<LogOut className="h-4 w-4" aria-hidden={true} />}>
                Logout
              </Button>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-4 py-5 lg:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function SidebarContent({
  items,
  userRole,
  onNavigate,
}: {
  items: NavItem[];
  userRole: UserRole;
  onNavigate: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-white/10 p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-token bg-accent text-accent-contrast">
            <FileText className="h-5 w-5" aria-hidden={true} />
          </div>
          <div>
            <p className="font-semibold">Enterprise AI</p>
            <p className="text-xs text-white/60">Knowledge Assistant</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-3" aria-label="Primary navigation">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex min-h-11 items-center gap-3 rounded-token px-3 text-sm font-medium transition ${
                  isActive ? "bg-white text-[rgb(19_27_35)]" : "text-white/78 hover:bg-white/10 hover:text-white"
                }`
              }
            >
              <Icon className="h-4 w-4" aria-hidden={true} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
      <div className="border-t border-white/10 p-4 text-xs text-white/64">
        <p>Role: {roleLabel(userRole)}</p>
      </div>
    </div>
  );
}

function pageTitle(pathname: string): string {
  if (titles[pathname]) {
    return titles[pathname];
  }
  if (pathname.startsWith("/documents/") && pathname.endsWith("/permissions")) {
    return "Document permissions";
  }
  if (pathname.startsWith("/documents/")) {
    return "Document detail";
  }
  return "Enterprise AI Console";
}