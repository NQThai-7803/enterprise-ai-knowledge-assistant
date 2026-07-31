import { AlertTriangle, Ban, FileSearch, Loader2, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./Button";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex min-h-40 items-center justify-center gap-3 text-sm text-muted" role="status">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="h-12 animate-pulse rounded-token bg-elevated" />
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
    <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-token border border-dashed border-border bg-elevated/60 p-6 text-center">
      <FileSearch className="h-8 w-8 text-accent" aria-hidden="true" />
      <div>
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {description ? <p className="mt-1 max-w-md text-sm text-muted">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Request failed",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-token border border-danger/20 bg-danger/5 p-4 text-sm text-danger">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{title}</p>
          <p className="mt-1 text-danger/90">{message}</p>
        </div>
        {onRetry ? (
          <Button variant="secondary" type="button" onClick={onRetry} icon={<RefreshCw className="h-4 w-4" />}>
            Retry
          </Button>
        ) : null}
      </div>
    </div>
  );
}

export function AccessDeniedState() {
  return (
    <div className="flex min-h-72 flex-col items-center justify-center gap-3 text-center">
      <Ban className="h-9 w-9 text-warning" aria-hidden="true" />
      <div>
        <h1 className="text-xl font-semibold text-ink">Access denied</h1>
        <p className="mt-1 text-sm text-muted">This workspace area is not available for your role.</p>
      </div>
    </div>
  );
}
