import { Component, type ReactNode } from "react";
import { Button } from "../ui/Button";

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(): void {
    // Deliberately do not print stack traces or component props in production UI.
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }
    return (
      <main className="flex min-h-[100dvh] items-center justify-center bg-canvas p-6 text-ink">
        <section className="max-w-md rounded-token border border-border bg-surface p-6 shadow-panel">
          <h1 className="text-lg font-semibold">Application error</h1>
          <p className="mt-2 text-sm text-muted">The interface failed to render safely.</p>
          <Button className="mt-4" type="button" onClick={() => window.location.reload()}>
            Reload
          </Button>
        </section>
      </main>
    );
  }
}