import { X } from "lucide-react";
import { type ReactNode, useEffect, useId, useRef } from "react";

/**
 * Right-side panel on the native modal <dialog>: the browser traps focus, makes the page inert,
 * closes on Escape and returns focus to the opener. Content renders only while open.
 */
export function Drawer({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) {
      return;
    }
    if (open && !dialog.open) {
      // jsdom has no showModal; real browsers do.
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      } else {
        dialog.setAttribute("open", "");
      }
    }
    if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className="drawer"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      {open ? (
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between gap-3 border-b border-border/70 px-6 py-4">
            <h2 id={titleId} className="text-[15px] font-semibold text-ink">
              {title}
            </h2>
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-token text-muted transition hover:bg-canvas hover:text-ink"
              onClick={onClose}
              aria-label="Đóng"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          <div className="app-scrollbar min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
        </div>
      ) : null}
    </dialog>
  );
}
