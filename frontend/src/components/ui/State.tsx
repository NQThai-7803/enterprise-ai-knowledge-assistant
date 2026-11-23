import { AlertCircle, FileText, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { isApiError, safeErrorMessage } from "../../api/errors";
import { Button } from "./Button";

/** Loading as a skeleton that keeps the content's shape; the label is for screen readers. */
export function LoadingState({ label = "Đang tải", rows = 4 }: { label?: string; rows?: number }) {
  return (
    <div className="space-y-4 py-2" role="status">
      <span className="sr-only">{label}</span>
      <SkeletonRows rows={rows} />
    </div>
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-4" aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex animate-pulse items-center gap-3">
          <div className="h-8 w-8 shrink-0 rounded-token bg-border/50" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-2/3 rounded bg-border/50" />
            <div className="h-2.5 w-1/3 rounded bg-border/40" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-xl border border-border/70 bg-surface p-8 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-elevated text-muted">
        <FileText className="h-5 w-5" aria-hidden="true" />
      </span>
      <div>
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {description ? <p className="mx-auto mt-1 max-w-sm text-sm text-muted">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

/** Pass `error` to show its safe message and the real request_id; `message` overrides the text. */
export function ErrorState({
  title = "Không tải được dữ liệu",
  message,
  error,
  onRetry,
}: {
  title?: string;
  message?: string;
  error?: unknown;
  onRetry?: () => void;
}) {
  const requestId = isApiError(error) ? error.requestId : null;
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-border/70 bg-surface p-6 text-center" role="alert">
      <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-danger/10 text-danger">
        <AlertCircle className="h-5 w-5" aria-hidden="true" />
      </span>
      <div>
        <p className="text-sm font-semibold text-ink">{title}</p>
        <p className="mx-auto mt-1 max-w-md text-sm text-muted">{message ?? safeErrorMessage(error)}</p>
      </div>
      {requestId ? (
        <code className="rounded-[6px] bg-elevated px-2 py-1 font-mono text-xs text-ink/80">request_id: {requestId}</code>
      ) : null}
      {onRetry ? (
        <Button variant="secondary" type="button" onClick={onRetry} icon={<RefreshCw className="h-4 w-4" aria-hidden="true" />}>
          Thử lại
        </Button>
      ) : null}
    </div>
  );
}

export function StatusPage({
  code,
  title,
  description,
  action,
}: {
  code: string;
  title: string;
  description: string;
  action: ReactNode;
}) {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center bg-canvas p-6 text-ink">
      <section className="flex max-w-2xl flex-col gap-6 sm:flex-row sm:items-center sm:gap-10">
        <p className="text-7xl font-semibold leading-none tracking-tight text-border" aria-hidden="true">
          {code}
        </p>
        <div>
          <h1 className="text-xl font-semibold text-ink">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
          <div className="mt-5">{action}</div>
        </div>
      </section>
    </main>
  );
}

export function StatusLink({ to, children, primary = false }: { to: string; children: ReactNode; primary?: boolean }) {
  return primary ? (
    <Link
      className="inline-flex min-h-10 items-center justify-center rounded-token bg-accent px-4 text-sm font-semibold text-accent-contrast transition hover:bg-accent-strong"
      to={to}
    >
      {children}
    </Link>
  ) : (
    <Link className="text-sm font-medium text-accent underline underline-offset-4 transition hover:text-accent-strong" to={to}>
      {children}
    </Link>
  );
}
