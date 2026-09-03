import {
  CheckCircle2,
  CircleAlert,
  Info,
  TriangleAlert,
  X,
} from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
} from "react";
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

const TOAST_DURATION_MS = 5000;

type ToastAction =
  | { type: "push"; toast: ToastItem }
  | { type: "dismiss"; id: string };

function reducer(state: ToastItem[], action: ToastAction): ToastItem[] {
  if (action.type === "push") {
    return [action.toast, ...state].slice(0, 4);
  }

  return state.filter((toast) => toast.id !== action.id);
}

export function ToastProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [toasts, dispatch] = useReducer(reducer, []);

  const dismissToast = useCallback((id: string) => {
    dispatch({ type: "dismiss", id });
  }, []);

  const pushToast = useCallback(
    (toast: ToastInput) => {
      const id = crypto.randomUUID();

      dispatch({
        type: "push",
        toast: {
          ...toast,
          id,
        },
      });

      window.setTimeout(() => {
        dismissToast(id);
      }, TOAST_DURATION_MS);
    },
    [dismissToast],
  );

  const value = useMemo(
    () => ({
      pushToast,
      dismissToast,
    }),
    [dismissToast, pushToast],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}

      <div
        className="pointer-events-none fixed right-4 top-20 z-50 flex w-[min(26rem,calc(100vw-2rem))] flex-col gap-3"
        aria-live="polite"
        aria-relevant="additions"
      >
        {toasts.map((toast) => {
          const config = toneConfig[toast.tone];
          const Icon = config.icon;

          return (
            <article
              key={toast.id}
              className={clsx(
                "pointer-events-auto relative overflow-hidden rounded-token border p-4 text-sm shadow-panel",
                config.container,
              )}
            >
              <div
                className={clsx(
                  "absolute inset-y-0 left-0 w-1",
                  config.accent,
                )}
                aria-hidden="true"
              />

              <div className="flex items-start gap-3 pl-1">
                <div
                  className={clsx(
                    "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-token",
                    config.iconContainer,
                  )}
                >
                  <Icon
                    className={clsx("h-4 w-4", config.iconColor)}
                    aria-hidden="true"
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <p
                    className={clsx(
                      "font-semibold",
                      config.titleColor,
                    )}
                  >
                    {toast.title}
                  </p>

                  {toast.message ? (
                    <p className="mt-1 leading-5 text-muted">
                      {toast.message}
                    </p>
                  ) : null}
                </div>

                <button
                  className="rounded-token p-1 text-muted transition hover:bg-elevated hover:text-ink"
                  type="button"
                  onClick={() => dismissToast(toast.id)}
                  aria-label="Dismiss notification"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

const toneConfig = {
  success: {
    icon: CheckCircle2,
    container: "border-success/35 bg-success/10",
    accent: "bg-success",
    iconContainer: "bg-success/15",
    iconColor: "text-success",
    titleColor: "text-success",
  },
  info: {
    icon: Info,
    container: "border-accent/35 bg-accent/10",
    accent: "bg-accent",
    iconContainer: "bg-accent/15",
    iconColor: "text-accent",
    titleColor: "text-accent",
  },
  warning: {
    icon: TriangleAlert,
    container: "border-warning/35 bg-warning/10",
    accent: "bg-warning",
    iconContainer: "bg-warning/15",
    iconColor: "text-warning",
    titleColor: "text-warning",
  },
  error: {
    icon: CircleAlert,
    container: "border-danger/35 bg-danger/10",
    accent: "bg-danger",
    iconContainer: "bg-danger/15",
    iconColor: "text-danger",
    titleColor: "text-danger",
  },
} satisfies Record<
  ToastTone,
  {
    icon: typeof CheckCircle2;
    container: string;
    accent: string;
    iconContainer: string;
    iconColor: string;
    titleColor: string;
  }
>;

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used inside ToastProvider.");
  }

  return context;
}