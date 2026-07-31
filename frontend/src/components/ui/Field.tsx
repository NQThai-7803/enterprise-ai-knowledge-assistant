import { clsx } from "clsx";
import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

interface FieldWrapperProps {
  id: string;
  label: string;
  error?: string;
  help?: string;
  children: ReactNode;
}

export function FieldWrapper({ id, label, error, help, children }: FieldWrapperProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      {children}
      {help && !error ? <p className="text-xs text-muted">{help}</p> : null}
      {error ? (
        <p className="text-xs font-medium text-danger" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export const TextInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function TextInput(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={clsx(
        "min-h-10 w-full rounded-token border border-border bg-surface px-3 text-sm text-ink shadow-sm transition placeholder:text-muted focus:border-accent focus:shadow-focus disabled:cursor-not-allowed disabled:bg-elevated disabled:text-muted",
        className,
      )}
      {...props}
    />
  );
});

export const SelectInput = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function SelectInput(
  { className, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      className={clsx(
        "min-h-10 w-full rounded-token border border-border bg-surface px-3 text-sm text-ink shadow-sm transition focus:border-accent focus:shadow-focus disabled:cursor-not-allowed disabled:bg-elevated disabled:text-muted",
        className,
      )}
      {...props}
    />
  );
});

export const TextArea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function TextArea(
  { className, ...props },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={clsx(
        "min-h-28 w-full rounded-token border border-border bg-surface px-3 py-2 text-sm text-ink shadow-sm transition placeholder:text-muted focus:border-accent focus:shadow-focus disabled:cursor-not-allowed disabled:bg-elevated disabled:text-muted",
        className,
      )}
      {...props}
    />
  );
});