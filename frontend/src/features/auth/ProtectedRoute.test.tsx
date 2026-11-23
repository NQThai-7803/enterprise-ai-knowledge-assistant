import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { AuthStatus } from "./AuthProvider";
import { ProtectedRoute } from "./ProtectedRoute";
import { contractManager } from "../../test/fixtures/contract";

let auth: { status: AuthStatus; user: typeof contractManager | null } = { status: "authenticated", user: contractManager };
vi.mock("./AuthProvider", () => ({ useAuth: () => auth }));

function LoginProbe() {
  const location = useLocation();
  return <p>login state: {JSON.stringify(location.state)}</p>;
}

function tree(path: string) {
  return (
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginProbe />} />
        <Route
          path="/documents/:id"
          element={
            <ProtectedRoute>
              <p>protected page</p>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

/** Signs in on the page, then moves to `next` (logout or expiry) on the same mounted route. */
function signedInThen(next: AuthStatus, path = "/documents/doc-1") {
  auth = { status: "authenticated", user: contractManager };
  const { rerender } = render(tree(path));
  expect(screen.getByText("protected page")).toBeInTheDocument();
  auth = { status: next, user: null };
  rerender(tree(path));
}

describe("ProtectedRoute redirect to sign-in", () => {
  it("drops the last page after an explicit logout, so the next person starts fresh", () => {
    signedInThen("unauthenticated");
    expect(screen.getByText("login state: null")).toBeInTheDocument();
  });

  it("keeps the page for a tab opened without a token (D-7 viewer)", () => {
    auth = { status: "unauthenticated", user: null };
    render(tree("/documents/doc-1?page=4"));
    expect(screen.getByText('login state: {"from":"/documents/doc-1?page=4"}')).toBeInTheDocument();
  });

  it("keeps the page for the same user only when the session expired", () => {
    signedInThen("expired");
    expect(screen.getByText(`login state: {"from":"/documents/doc-1","userId":"${contractManager.id}"}`)).toBeInTheDocument();
  });

  it("keeps no page when a session expired before this tab knew whose it was (a reload with a dead token)", () => {
    auth = { status: "expired", user: null };
    render(tree("/documents/doc-1"));
    expect(screen.getByText("login state: null")).toBeInTheDocument();
  });
});
