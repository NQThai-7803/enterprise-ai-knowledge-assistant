import { AlertTriangle } from "lucide-react";
import { useId, useLayoutEffect, useRef, type KeyboardEvent } from "react";
import { Button } from "./Button";

const focusableSelector =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusableIn(element: ParentNode): HTMLElement[] {
  return Array.from(element.querySelectorAll<HTMLElement>(focusableSelector)).filter(
    (candidate) => {
      const style = getComputedStyle(candidate);
      return !candidate.hidden && style.display !== "none" && style.visibility !== "hidden";
    },
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
  loading = false,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}) {
  const dialogRef = useRef<HTMLElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useLayoutEffect(() => {
    if (!open) {
      return undefined;
    }
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousContainer = previousFocus?.parentElement;
    const dialog = dialogRef.current;
    if (!dialog) {
      return undefined;
    }
    const focusInside = () => (focusableIn(dialog)[0] ?? dialog).focus();
    focusInside();
    const containFocus = (event: FocusEvent) => {
      if (!dialog.contains(event.target as Node)) {
        focusInside();
      }
    };
    document.addEventListener("focusin", containFocus);
    return () => {
      document.removeEventListener("focusin", containFocus);
      queueMicrotask(() => {
        if (dialog.isConnected) {
          return;
        }
        const restoreTarget = previousFocus?.isConnected && !previousFocus.matches(":disabled")
          ? previousFocus
          : (previousContainer?.isConnected ? focusableIn(previousContainer)[0] : null)
            ?? focusableIn(document.querySelector("main") ?? document)[0];
        restoreTarget?.focus();
      });
    };
  }, [open]);

  useLayoutEffect(() => {
    if (!open) {
      return;
    }
    const dialog = dialogRef.current;
    if (loading) {
      dialog?.focus();
    } else if (dialog && document.activeElement === dialog) {
      focusableIn(dialog)[0]?.focus();
    }
  }, [loading, open]);

  const onDialogKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      if (!loading) {
        onCancel();
      }
      return;
    }
    if (event.key !== "Tab") {
      return;
    }
    const dialog = dialogRef.current;
    if (!dialog) {
      return;
    }
    const focusable = focusableIn(dialog);
    const first = focusable[0];
    const last = focusable.at(-1);
    if (!first || !last) {
      event.preventDefault();
      dialog.focus();
    } else if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialog)) {
      event.preventDefault();
      first.focus();
    }
  };

  if (!open) {
    return null;
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="presentation">
      <section ref={dialogRef} className="w-full max-w-md rounded-token border border-border bg-surface p-5 shadow-panel" role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId} aria-busy={loading || undefined} tabIndex={-1} onKeyDown={onDialogKeyDown}>
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-1 h-5 w-5 shrink-0 text-warning" aria-hidden="true" />
          <div className="min-w-0">
            <h2 id={titleId} className="text-lg font-semibold text-ink">
              {title}
            </h2>
            <p id={descriptionId} className="mt-2 text-sm leading-6 text-muted">{message}</p>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
          <Button type="button" variant="danger" onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </div>
      </section>
    </div>
  );
}
