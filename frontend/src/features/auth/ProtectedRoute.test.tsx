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

function renderAt(path: string) {
  return render(
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
    </MemoryRouter>,
  );
}

describe("ProtectedRoute redirect to sign-in", () => {
  it("drops the last page after an explicit logout, so the next person starts fresh", () => {
    auth = { status: "authenticated", user: contractManager };
    const { rerender } = renderAt("/documents/doc-1");
    expect(screen.getByText("protected page")).toBeInTheDocument();

    auth = { status: "unauthenticated", user: null };
    rerender(
      <MemoryRouter initialEntries={["/documents/doc-1"]}>
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
      </MemoryRouter>,
    );
    expect(screen.getByText("login state: null")).toBeInTheDocument();
  });

  it("keeps the page for a tab opened without a token (D-7 viewer)", () => {
    auth = { status: "unauthenticated", user: null };
    renderAt("/documents/doc-1?page=4");
    expect(screen.getByText('login state: {"from":"/documents/doc-1?page=4"}')).toBeInTheDocument();
  });

  it("keeps the page when the session expired", () => {
    auth = { status: "expired", user: null };
    renderAt("/documents/doc-1");
    expect(screen.getByText('login state: {"from":"/documents/doc-1"}')).toBeInTheDocument();
  });
});
