import { X } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useReducer } from "react";
import { clsx } from "clsx";

export type ToastTone = "success" | "info" | "warning" | "error";

export interface ToastInput {
  tone: ToastTone;
  title: string;
  message?: string;
}

interface ToastItem extends ToastInput {
  id: string;
}

interface ToastContextValue {
  pushToast: (toast: ToastInput) => void;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

type ToastAction = { type: "push"; toast: ToastItem } | { type: "dismiss"; id: string };

function reducer(state: ToastItem[], action: ToastAction): ToastItem[] {
  if (action.type === "push") {
    return [action.toast, ...state].slice(0, 4);
  }
  return state.filter((toast) => toast.id !== action.id);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, dispatch] = useReducer(reducer, []);

  const pushToast = useCallback((toast: ToastInput) => {
    dispatch({ type: "push", toast: { ...toast, id: crypto.randomUUID() } });
  }, []);

  const dismissToast = useCallback((id: string) => {
    dispatch({ type: "dismiss", id });
  }, []);

  const value = useMemo(() => ({ pushToast, dismissToast }), [dismissToast, pushToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed right-4 top-20 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-3"
        aria-live="polite"
        aria-relevant="additions"
      >
        {toasts.map((toast) => (
          <article
            key={toast.id}
            className={clsx("pointer-events-auto rounded-token border bg-surface p-4 text-sm shadow-panel", toneClasses[toast.tone])}
          >
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-ink">{toast.title}</p>
                {toast.message ? <p className="mt-1 text-muted">{toast.message}</p> : null}
              </div>
              <button className="rounded-token p-1 text-muted hover:bg-elevated" type="button" onClick={() => dismissToast(toast.id)} aria-label="Dismiss notification">
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </article>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

const toneClasses: Record<ToastTone, string> = {
  success: "border-success/25",
  info: "border-accent/25",
  warning: "border-warning/25",
  error: "border-danger/25",
};

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used inside ToastProvider.");
  }
  return context;
}