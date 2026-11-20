import { clsx } from "clsx";
import type { ReactNode } from "react";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "accent" | "strong";

const toneClasses: Record<BadgeTone, string> = {
  neutral: "bg-border/40 text-ink/80",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  danger: "bg-danger/10 text-danger",
  accent: "bg-accent/10 text-accent-strong",
  strong: "bg-ink text-surface",
};

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
