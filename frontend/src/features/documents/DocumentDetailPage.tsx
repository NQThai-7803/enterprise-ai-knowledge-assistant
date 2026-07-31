import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, KeyRound, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import { useToast } from "../../components/feedback/ToastProvider";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { Panel } from "../../components/ui/Panel";
import { DocumentStatusBadge } from "../../components/ui/StatusBadge";
import { ErrorState, LoadingState } from "../../components/ui/State";
import { formatBytes, formatDateTime, truncateMiddle } from "../../lib/format";
import { canManageDocumentPermissions } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";

export function DocumentDetailPage() {
  const { documentId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const detailQuery = useQuery({
    queryKey: ["documents", "detail", documentId],
    queryFn: () => apiClient.documents.detail(documentId as string),
    enabled: Boolean(documentId),
  });

  const statusQuery = useQuery({
    queryKey: ["documents", "status", documentId],
    queryFn: () => apiClient.documents.status(documentId as string),
    enabled: Boolean(documentId),
    refetchInterval: (query) => {
      const status = query.state.data?.data.status;
      return status === "UPLOADED" || status === "PROCESSING" ? 5000 : false;
    },
  });

  const downloadMutation = useMutation({
    mutationFn: () => apiClient.documents.download(documentId as string),
    onSuccess: ({ blob, filename }) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename ?? "document.pdf";
      link.click();
      URL.revokeObjectURL(url);
    },
    onError: (error) => pushToast({ tone: "error", title: "Download failed", message: safeErrorMessage(error) }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.documents.delete(documentId as string),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      pushToast({ tone: "success", title: "Document deleted" });
      navigate("/documents");
    },
    onError: (error) => pushToast({ tone: "error", title: "Delete failed", message: safeErrorMessage(error) }),
  });

  if (detailQuery.isLoading) {
    return <LoadingState label="Loading document" />;
  }
  if (detailQuery.isError) {
    return <ErrorState message={safeErrorMessage(detailQuery.error)} onRetry={() => void detailQuery.refetch()} />;
  }

  const documentItem = detailQuery.data?.data;
  if (!documentItem) {
    return <ErrorState message="Document detail is unavailable." />;
  }
  const currentStatus = statusQuery.data?.data.status ?? documentItem.status;

  return (
    <div>
      <PageHeader
        title={documentItem.title}
        description={documentItem.description ?? "No description."}
        actions={
          <>
            {canManageDocumentPermissions(user) ? (
              <Link className="inline-flex min-h-10 items-center justify-center gap-2 rounded-token border border-border bg-surface px-3 text-sm font-semibold text-ink hover:bg-elevated" to={`/documents/${documentItem.id}/permissions`}>
                <KeyRound className="h-4 w-4" aria-hidden="true" />
                Permissions
              </Link>
            ) : null}
            <Button type="button" variant="secondary" loading={downloadMutation.isPending} onClick={() => downloadMutation.mutate()} icon={<Download className="h-4 w-4" aria-hidden="true" />}>
              Download
            </Button>
            <Button type="button" variant="danger" onClick={() => setConfirmDelete(true)} icon={<Trash2 className="h-4 w-4" aria-hidden="true" />}>
              Delete
            </Button>
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
        <Panel className="p-5">
          <dl className="grid gap-4 sm:grid-cols-2">
            <Detail label="Document ID" value={truncateMiddle(documentItem.id, 42)} />
            <Detail label="Status" value={<DocumentStatusBadge status={currentStatus} />} />
            <Detail label="Access scope" value={<Badge tone="neutral">{documentItem.access_scope}</Badge>} />
            <Detail label="Department" value={documentItem.department_id ? truncateMiddle(documentItem.department_id) : "Unscoped"} />
            <Detail label="Original filename" value={documentItem.original_filename} />
            <Detail label="File size" value={formatBytes(documentItem.file_size)} />
            <Detail label="Uploaded by" value={truncateMiddle(documentItem.uploaded_by)} />
            <Detail label="Created" value={formatDateTime(documentItem.created_at)} />
            <Detail label="Updated" value={formatDateTime(documentItem.updated_at)} />
          </dl>
        </Panel>

        <Panel className="p-5">
          <h3 className="text-sm font-semibold">Processing status</h3>
          <div className="mt-3 space-y-3 text-sm text-muted">
            <DocumentStatusBadge status={currentStatus} />
            <p>{statusQuery.data?.data.error_message ?? "No processing error reported."}</p>
            <p>Last checked: {statusQuery.data?.data.updated_at ? formatDateTime(statusQuery.data.data.updated_at) : "Unavailable"}</p>
          </div>
        </Panel>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete document"
        message="This sends the backend soft-delete request. The UI will not remove source files directly."
        confirmLabel="Delete"
        loading={deleteMutation.isPending}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => deleteMutation.mutate()}
      />
    </div>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-muted">{label}</dt>
      <dd className="mt-1 break-words text-sm text-ink">{value}</dd>
    </div>
  );
}