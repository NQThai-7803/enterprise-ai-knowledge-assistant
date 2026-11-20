import { useQuery } from "@tanstack/react-query";
import { Search, Upload } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import type { DocumentAccessScope, DocumentItem, DocumentStatus } from "../../api/types";
import { DataTable } from "../../components/data/DataTable";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { FieldWrapper, SelectInput, TextInput } from "../../components/ui/Field";
import { Pagination } from "../../components/ui/Pagination";
import { DocumentStatusBadge } from "../../components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatBytes, formatDateTime } from "../../lib/format";
import { accessScopeLabels, documentStatusLabels, lifecycleLabels } from "../../lib/labels";
import { canUploadDocuments } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { ScopeBadge } from "./ScopeBadge";

const IN_PROGRESS: DocumentStatus[] = ["UPLOADED", "PROCESSING"];

export function DocumentsPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<DocumentStatus | "">("");
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
    // Keep refreshing while a row is still being processed in the background.
    refetchInterval: (query) =>
      query.state.data?.data.some((document) => IN_PROGRESS.includes(document.status)) ? 5_000 : false,
  });

  const documents = documentsQuery.data?.data ?? [];
  const filtered = Boolean(search.trim() || status || scope);

  return (
    <div>
      <PageHeader
        title="Tài liệu"
        description="Danh sách đã lọc theo quyền của bạn. Tài liệu mới được xử lý nền trước khi dùng để hỏi đáp."
        actions={
          canUploadDocuments(user) ? (
            <Link
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-token bg-accent px-4 text-sm font-semibold text-accent-contrast transition hover:bg-accent-strong"
              to="/documents/upload"
            >
              <Upload className="h-4 w-4" aria-hidden="true" />
              Tải tài liệu lên
            </Link>
          ) : null
        }
      />

      <section className="mb-5 grid gap-3 md:grid-cols-[minmax(0,1fr)_13rem_13rem]" aria-label="Bộ lọc tài liệu">
        <FieldWrapper id="document-search" label="Tìm kiếm">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" aria-hidden="true" />
            <TextInput
              id="document-search"
              className="pl-9"
              // TODO(BR-1 mục 4): add "mã tài liệu" once search covers document_code.
              placeholder="Tên hoặc tên tệp"
              maxLength={200}
              value={search}
              onChange={(event) => {
                setPage(1);
                setSearch(event.target.value);
              }}
            />
          </div>
        </FieldWrapper>
        <FieldWrapper id="document-scope" label="Phạm vi">
          <SelectInput
            id="document-scope"
            value={scope}
            onChange={(event) => {
              setPage(1);
              setScope(event.target.value as DocumentAccessScope | "");
            }}
          >
            <option value="">Tất cả phạm vi</option>
            {(Object.keys(accessScopeLabels) as DocumentAccessScope[]).map((value) => (
              <option key={value} value={value}>
                {accessScopeLabels[value]}
              </option>
            ))}
          </SelectInput>
        </FieldWrapper>
        <FieldWrapper id="document-status" label="Trạng thái">
          <SelectInput
            id="document-status"
            value={status}
            onChange={(event) => {
              setPage(1);
              setStatus(event.target.value as DocumentStatus | "");
            }}
          >
            <option value="">Tất cả trạng thái</option>
            {(Object.keys(documentStatusLabels) as DocumentStatus[]).map((value) => (
              <option key={value} value={value}>
                {documentStatusLabels[value]}
              </option>
            ))}
          </SelectInput>
        </FieldWrapper>
      </section>

      {documentsQuery.isLoading ? <LoadingState label="Đang tải tài liệu" /> : null}
      {documentsQuery.isError ? (
        <ErrorState
          title="Không tải được danh sách tài liệu"
          message={safeErrorMessage(documentsQuery.error)}
          onRetry={() => void documentsQuery.refetch()}
        />
      ) : null}
      {!documentsQuery.isLoading && !documentsQuery.isError && documents.length === 0 ? (
        <EmptyState
          title={filtered ? "Không có tài liệu phù hợp" : "Chưa có tài liệu nào"}
          description={
            filtered
              ? "Thử đổi từ khóa hoặc bộ lọc."
              : "Khi tài liệu được tải lên và xử lý xong, chúng sẽ xuất hiện ở đây."
          }
        />
      ) : null}

      {documents.length ? (
        <>
          <DataTable columns={["Tài liệu", "Phạm vi", "Trạng thái", "Cập nhật", "Thao tác"]}>
            {documents.map((document) => (
              <tr key={document.id} className="align-middle">
                <td className="px-5 py-3.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-ink">{document.title}</span>
                    {document.lifecycle_status !== "ACTIVE" ? (
                      <Badge tone="neutral">{lifecycleLabels[document.lifecycle_status]}</Badge>
                    ) : null}
                  </div>
                  <p className="mt-0.5 font-mono text-xs text-muted">{documentSubline(document)}</p>
                </td>
                <td className="px-5 py-3.5">
                  <ScopeBadge document={document} user={user} />
                </td>
                <td className="px-5 py-3.5">
                  <DocumentStatusBadge status={document.status} />
                </td>
                <td className="whitespace-nowrap px-5 py-3.5 text-muted">{formatDateTime(document.updated_at)}</td>
                <td className="px-5 py-3.5">
                  <div className="flex justify-end gap-4 whitespace-nowrap text-sm">
                    <Link className="text-ink transition hover:text-accent" to={`/documents/${document.id}`}>
                      Chi tiết
                    </Link>
                    {user?.role === "ADMIN" ? (
                      <Link
                        className="text-ink transition hover:text-accent"
                        to={`/documents/${document.id}/permissions`}
                      >
                        Phân quyền
                      </Link>
                    ) : null}
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

function documentSubline(document: DocumentItem): string {
  return [
    document.document_code ?? document.original_filename,
    document.document_version ? `v${document.document_version}` : null,
    formatBytes(document.file_size),
  ]
    .filter(Boolean)
    .join(" · ");
}
