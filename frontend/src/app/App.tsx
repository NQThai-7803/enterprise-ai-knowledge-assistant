import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { LoginPage } from "../features/auth/LoginPage";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { ChatPage } from "../features/chat/ChatPage";
import { DocumentsPage } from "../features/documents/DocumentsPage";
import { DocumentUploadPage } from "../features/documents/DocumentUploadPage";
import { DocumentDetailPage } from "../features/documents/DocumentDetailPage";
import { DocumentPermissionsPage } from "../features/documents/DocumentPermissionsPage";
import { UsersPage } from "../features/admin/UsersPage";
import { DepartmentsPage } from "../features/admin/DepartmentsPage";
import { FeedbackPage } from "../features/feedback/FeedbackPage";
import { AuditLogsPage } from "../features/audit/AuditLogsPage";
import { SystemStatusPage } from "../features/system/SystemStatusPage";
import { ProfilePage } from "../features/profile/ProfilePage";
import { AccessDeniedPage } from "../routes/AccessDeniedPage";
import { NotFoundPage } from "../routes/NotFoundPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/access-denied" element={<AccessDeniedPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route
          path="documents/upload"
          element={
            <ProtectedRoute roles={["ADMIN", "MANAGER"]}>
              <DocumentUploadPage />
            </ProtectedRoute>
          }
        />
        <Route path="documents/:documentId" element={<DocumentDetailPage />} />
        <Route
          path="documents/:documentId/permissions"
          element={
            <ProtectedRoute roles={["ADMIN"]}>
              <DocumentPermissionsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="users"
          element={
            <ProtectedRoute roles={["ADMIN"]}>
              <UsersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="departments"
          element={
            <ProtectedRoute roles={["ADMIN"]}>
              <DepartmentsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="feedback"
          element={
            <ProtectedRoute roles={["ADMIN", "MANAGER"]}>
              <FeedbackPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="audit-logs"
          element={
            <ProtectedRoute roles={["ADMIN"]}>
              <AuditLogsPage />
            </ProtectedRoute>
          }
        />
        <Route path="system" element={<SystemStatusPage />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}