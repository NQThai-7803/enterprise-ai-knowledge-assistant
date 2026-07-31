import { Link } from "react-router-dom";
import { AccessDeniedState } from "../components/ui/State";

export function AccessDeniedPage() {
  return (
    <main className="min-h-[100dvh] bg-canvas p-6 text-ink">
      <AccessDeniedState />
      <div className="mt-4 text-center">
        <Link className="inline-flex min-h-10 items-center justify-center rounded-token border border-border bg-surface px-3 text-sm font-semibold text-ink hover:bg-elevated" to="/chat">
          Return to chat
        </Link>
      </div>
    </main>
  );
}