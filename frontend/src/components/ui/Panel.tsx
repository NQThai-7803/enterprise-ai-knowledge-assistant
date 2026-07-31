import { clsx } from "clsx";
import type { HTMLAttributes } from "react";

export function Panel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <section
      className={clsx("rounded-token border border-border bg-surface shadow-sm", className)}
      {...props}
    />
  );
}
