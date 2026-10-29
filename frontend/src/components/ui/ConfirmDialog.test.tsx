import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog } from "./ConfirmDialog";

function Harness({
  initialLoading = false,
  pendingOnConfirm = false,
  onConfirm = vi.fn(),
}: {
  initialLoading?: boolean;
  pendingOnConfirm?: boolean;
  onConfirm?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(initialLoading);
  return (
    <main>
      <button type="button" onClick={() => setOpen(true)}>Open confirmation</button>
      <button type="button" onClick={() => setLoading(true)}>Start pending</button>
      <ConfirmDialog
        open={open}
        title="Delete item"
        message="This action removes the item."
        confirmLabel="Delete"
        loading={loading}
        onCancel={() => setOpen(false)}
        onConfirm={() => {
          onConfirm();
          if (pendingOnConfirm) {
            setLoading(true);
          }
        }}
      />
    </main>
  );
}

describe("ConfirmDialog keyboard contract", () => {
  it("focuses Cancel on open, associates its description, and restores the trigger on Escape", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const trigger = screen.getByRole("button", { name: "Open confirmation" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Delete item" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    const descriptionId = dialog.getAttribute("aria-describedby");
    expect(descriptionId).toBeTruthy();
    expect(document.getElementById(descriptionId!)).toHaveTextContent("removes the item");
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("locks Escape and actions while a confirmation is pending", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<Harness onConfirm={onConfirm} pendingOnConfirm />);
    await user.click(screen.getByRole("button", { name: "Open confirmation" }));
    const dialog = screen.getByRole("dialog", { name: "Delete item" });
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(dialog).toHaveFocus();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
    await user.keyboard("{Escape}{Tab}");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveFocus();
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("starts locked when opened during an existing pending action", async () => {
    const user = userEvent.setup();
    render(<Harness initialLoading />);
    await user.click(screen.getByRole("button", { name: "Open confirmation" }));
    const dialog = screen.getByRole("dialog", { name: "Delete item" });
    expect(dialog).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(dialog).toBeInTheDocument();
  });

  it("invokes confirmation once without auto-closing before the caller succeeds", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<Harness onConfirm={onConfirm} />);
    await user.click(screen.getByRole("button", { name: "Open confirmation" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("dialog", { name: "Delete item" })).toBeInTheDocument();
  });
});
