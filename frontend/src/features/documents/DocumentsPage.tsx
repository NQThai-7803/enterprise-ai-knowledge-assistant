import { useQuery } from "@tanstack/react-query";
import { FileUp, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import type { DocumentAccessScope } from "../../api/types";
import { DataTable } from "../../components/data/DataTable";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { FieldWrapper, SelectInput, TextInput } from "../../components/ui/Field";
import { Pagination } from "../../components/ui/Pagination";
import { DocumentStatusBadge } from "../../components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatBytes, formatDateTime, truncateMiddle } from "../../lib/format";
import { canUploadDocuments } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";

export function DocumentsPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [scope, setScope] = useState<DocumentAccessScope | "">("");

  const documentsQuery = useQuery({
    queryKey: ["documents", page, search, status, scope],
    queryFn: () =>
      apiClient.documents.list({
        page,
        page_size: 20,
        search: search.trim() || undefined,
        status: status || undefined,
        access_scope: scope || undefined,
      }),
  });

  const documents = documentsQuery.data?.data ?? [];

  return (
    <div>
      <PageHeader
        title="Document library"
        description="Accessible documents are returned by backend permission filters before they reach this table."
        actions={
          canUploadDocuments(user) ? (
            <Link className="inline-flex min-h-10 items-center justify-center gap-2 rounded-token border border-accent bg-accent px-3 text-sm font-semibold text-accent-contrast hover:bg-accent/90" to="/documents/upload">
              <FileUp className="h-4 w-4" aria-hidden="true" />
              Upload PDF
            </Link>
          ) : null
        }
      />

      <section className="mb-4 grid gap-3 rounded-token border border-border bg-surface p-4 md:grid-cols-[1fr_12rem_12rem]">
        <FieldWrapper id="document-search" label="Search">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" aria-hidden="true" />
            <TextInput id="document-search" className="pl-9" value={search} onChange={(event) => { setPage(1); setSearch(event.target.value); }} />
          </div>
        </FieldWrapper>
        <FieldWrapper id="document-status" label="Status">
          <SelectInput id="document-status" value={status} onChange={(event) => { setPage(1); setStatus(event.target.value); }}>
            <option value="">All statuses</option>
            <option value="UPLOADED">Uploaded</option>
            <option value="PROCESSING">Processing</option>
            <option value="READY">Ready</option>
            <option value="FAILED">Failed</option>
            <option value="ARCHIVED">Archived</option>
          </SelectInput>
        </FieldWrapper>
        <FieldWrapper id="document-scope" label="Access scope">
          <SelectInput id="document-scope" value={scope} onChange={(event) => { setPage(1); setScope(event.target.value as DocumentAccessScope | ""); }}>
            <option value="">All scopes</option>
            <option value="PRIVATE">Private</option>
            <option value="DEPARTMENT">Department</option>
            <option value="ORGANIZATION">Organization</option>
          </SelectInput>
        </FieldWrapper>
      </section>

      {documentsQuery.isLoading ? <LoadingState label="Loading documents" /> : null}
      {documentsQuery.isError ? <ErrorState message={safeErrorMessage(documentsQuery.error)} onRetry={() => void documentsQuery.refetch()} /> : null}
      {!documentsQuery.isLoading && !documentsQuery.isError && documents.length === 0 ? <EmptyState title="No documents found" /> : null}

      {documents.length ? (
        <>
          <DataTable columns={["Title", "Status", "Scope", "File", "Updated", "Actions"]}>
            {documents.map((document) => (
              <tr key={document.id} className="align-top hover:bg-elevated/60">
                <td className="px-4 py-3">
                  <Link className="font-semibold text-accent hover:underline" to={`/documents/${document.id}`}>{document.title}</Link>
                  <p className="mt-1 text-xs text-muted">{truncateMiddle(document.id)}</p>
                </td>
                <td className="px-4 py-3"><DocumentStatusBadge status={document.status} /></td>
                <td className="px-4 py-3"><Badge tone="neutral">{document.access_scope}</Badge></td>
                <td className="px-4 py-3 text-muted">
                  <span className="block">{document.original_filename}</span>
                  <span className="text-xs">{formatBytes(document.file_size)}</span>
                </td>
                <td className="px-4 py-3 text-muted">{formatDateTime(document.updated_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <Link className="rounded-token border border-border px-2 py-1 text-xs font-semibold hover:bg-elevated" to={`/documents/${document.id}`}>Detail</Link>
                    {user?.role === "ADMIN" ? <Link className="rounded-token border border-border px-2 py-1 text-xs font-semibold hover:bg-elevated" to={`/documents/${document.id}/permissions`}>Permissions</Link> : null}
                  </div>
                </td>
              </tr>
            ))}
          </DataTable>
          {documentsQuery.data?.meta ? <Pagination meta={documentsQuery.data.meta} onPageChange={setPage} /> : null}
        </>
      ) : null}
    </div>
  );
}