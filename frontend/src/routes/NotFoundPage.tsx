import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center bg-canvas p-6 text-ink">
      <section className="max-w-md rounded-token border border-border bg-surface p-6 text-center shadow-panel">
        <p className="text-sm font-semibold text-accent">404</p>
        <h1 className="mt-2 text-xl font-semibold">Page not found</h1>
        <p className="mt-2 text-sm text-muted">The requested console route is unavailable.</p>
        <Link className="mt-4 inline-flex min-h-10 items-center justify-center rounded-token border border-border bg-surface px-3 text-sm font-semibold text-ink hover:bg-elevated" to="/chat">
          Return to chat
        </Link>
      </section>
    </main>
  );
}