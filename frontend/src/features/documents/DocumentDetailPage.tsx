import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clsx } from "clsx";
import { CheckCircle2, ChevronLeft, Circle, Download, Lock, Trash2, XCircle } from "lucide-react";
import { type ReactNode, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import type { AuthenticatedUser, DocumentItem, DocumentStatus } from "../../api/types";
import { useToast } from "../../components/feedback/ToastProvider";
import { Button } from "../../components/ui/Button";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { DocumentStatusBadge } from "../../components/ui/StatusBadge";
import { ErrorState, LoadingState } from "../../components/ui/State";
import { formatBytes, formatDateTime, formatIsoDate } from "../../lib/format";
import { lifecycleLabels } from "../../lib/labels";
import { canManageDocumentPermissions } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { ScopeBadge } from "./ScopeBadge";

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
      link.download = filename ?? detailQuery.data?.data.original_filename ?? "tai-lieu";
      link.click();
      URL.revokeObjectURL(url);
    },
    onError: (error) => pushToast({ tone: "error", title: "Tải xuống thất bại", message: safeErrorMessage(error) }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.documents.delete(documentId as string),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      pushToast({ tone: "success", title: "Đã xóa tài liệu" });
      navigate("/documents");
    },
    onError: (error) => pushToast({ tone: "error", title: "Xóa thất bại", message: safeErrorMessage(error) }),
  });

  if (detailQuery.isLoading) {
    return <LoadingState label="Đang tải tài liệu" />;
  }
  if (detailQuery.isError) {
    return (
      <ErrorState
        title="Không tải được tài liệu"
        error={detailQuery.error}
        onRetry={() => void detailQuery.refetch()}
      />
    );
  }

  const documentItem = detailQuery.data?.data;
  if (!documentItem) {
    return <ErrorState title="Không tải được tài liệu" message="Không có dữ liệu chi tiết của tài liệu." />;
  }
  const currentStatus = statusQuery.data?.data.status ?? documentItem.status;

  return (
    <div>
      <Link
        to="/documents"
        className="mb-5 inline-flex items-center gap-1 text-sm text-muted transition hover:text-ink"
      >
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        Tài liệu
      </Link>

      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="mb-1.5 flex flex-wrap items-center gap-2.5">
            {documentItem.document_code ? (
              <span className="font-mono text-xs text-muted">{documentItem.document_code}</span>
            ) : null}
            <DocumentStatusBadge status={currentStatus} />
          </div>
          <h1 className="text-2xl font-semibold tracking-normal text-ink">{documentItem.title}</h1>
          {documentItem.description ? (
            <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">{documentItem.description}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            loading={downloadMutation.isPending}
            onClick={() => downloadMutation.mutate()}
            icon={<Download className="h-4 w-4" aria-hidden="true" />}
          >
            Tải xuống
          </Button>
          {canManageDocumentPermissions(user) ? (
            <Link
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-token border border-border bg-surface px-3 text-sm font-semibold text-ink transition hover:bg-elevated"
              to={`/documents/${documentItem.id}/permissions`}
            >
              <Lock className="h-4 w-4" aria-hidden="true" />
              Phân quyền
            </Link>
          ) : null}
          {/* D-8: shown to every role as before; the backend answers 403 when the caller may not delete. */}
          <Button
            type="button"
            variant="danger"
            onClick={() => setConfirmDelete(true)}
            icon={<Trash2 className="h-4 w-4" aria-hidden="true" />}
          >
            Xóa
          </Button>
        </div>
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <section className="rounded-xl border border-border/70 bg-surface p-6" aria-labelledby="document-info">
          <h2 id="document-info" className="mb-4 text-[15px] font-semibold">
            Thông tin
          </h2>
          <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
            <Detail label="Tên tệp gốc" value={<span className="break-all">{documentItem.original_filename}</span>} />
            <Detail label="Phạm vi truy cập" value={<ScopeBadge document={documentItem} user={user} />} />
            <Detail label="Phòng ban" value={departmentText(documentItem, user)} />
            <Detail label="Kích thước" value={formatBytes(documentItem.file_size)} />
            <Detail label="Mã tài liệu" value={documentItem.document_code ?? "Không có"} />
            <Detail label="Phiên bản" value={documentItem.document_version ?? "Không có"} />
            <Detail label="Hiệu lực" value={effectiveText(documentItem)} />
            <Detail label="Vòng đời" value={lifecycleLabels[documentItem.lifecycle_status]} />
            {documentItem.supersedes_document_id ? (
              <Detail
                label="Thay thế tài liệu"
                value={
                  <Link
                    className="text-accent transition hover:text-accent-strong"
                    to={`/documents/${documentItem.supersedes_document_id}`}
                  >
                    Xem tài liệu cũ
                  </Link>
                }
              />
            ) : null}
            {/* TODO(BR-4 followup): uploader name only when the response carries it; uploaded_by_me for others. */}
            <Detail label="Ngày tạo" value={formatDateTime(documentItem.created_at)} />
            <Detail label="Cập nhật" value={formatDateTime(documentItem.updated_at)} />
            <Detail label="Mã tài liệu (ID)" value={<span className="break-all font-mono text-xs">{documentItem.id}</span>} />
          </dl>
        </section>

        <section className="rounded-xl border border-border/70 bg-surface p-6" aria-labelledby="document-processing">
          <h2 id="document-processing" className="mb-4 text-[15px] font-semibold">
            Trạng thái xử lý
          </h2>
          <ProcessingTimeline status={currentStatus} errorMessage={statusQuery.data?.data.error_message ?? null} />
          <p className="mt-4 text-xs text-muted">
            Kiểm tra lần cuối:{" "}
            {statusQuery.data?.data.updated_at ? formatDateTime(statusQuery.data.data.updated_at) : "Không có"}
          </p>
        </section>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Xóa tài liệu này?"
        message="Tài liệu sẽ không còn trong danh sách và không được dùng để trả lời. Bản ghi vẫn được giữ cho nhật ký hệ thống."
        confirmLabel="Xóa"
        loading={deleteMutation.isPending}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => deleteMutation.mutate()}
      />
    </div>
  );
}

function departmentText(documentItem: DocumentItem, user: AuthenticatedUser | null): string {
  if (!documentItem.department_id) {
    return "Không gắn phòng ban";
  }
  if (user?.department_id === documentItem.department_id && user.department_name) {
    return user.department_name;
  }
  // TODO(BR-4 followup): show department_name when the document response carries it.
  return "Phòng ban của tài liệu";
}

function effectiveText(documentItem: DocumentItem): string {
  if (!documentItem.effective_from && !documentItem.effective_to) {
    return "Không ghi";
  }
  const from = documentItem.effective_from ? formatIsoDate(documentItem.effective_from) : "…";
  const to = documentItem.effective_to ? formatIsoDate(documentItem.effective_to) : "nay";
  return `${from} – ${to}`;
}

type StepState = "done" | "active" | "pending" | "failed";

/** Three steps derived from status only; finer stages wait for BR-7. */
function ProcessingTimeline({ status, errorMessage }: { status: DocumentStatus; errorMessage: string | null }) {
  const steps: { label: string; note: string; state: StepState }[] = [
    { label: "Đã tải lên", note: "Đã nhận tệp", state: "done" },
    {
      label: "Xử lý",
      note: "Trích xuất văn bản, chia đoạn, tạo embedding",
      state: status === "UPLOADED" ? "pending" : status === "PROCESSING" ? "active" : "done",
    },
    status === "FAILED"
      ? { label: "Lỗi", note: errorMessage ?? "Xử lý không thành công.", state: "failed" }
      : {
          label: status === "ARCHIVED" ? "Lưu trữ" : "Sẵn sàng",
          note: status === "ARCHIVED" ? "Không còn dùng để hỏi đáp" : "Có thể dùng để hỏi đáp",
          state: status === "READY" || status === "ARCHIVED" ? "done" : "pending",
        },
  ];

  return (
    <ol className="flex flex-col gap-4">
      {steps.map((step) => (
        <li key={step.label} className="flex gap-3">
          <StepIcon state={step.state} />
          <div className="min-w-0">
            <p className={clsx("text-sm font-medium", step.state === "pending" ? "text-muted" : "text-ink")}>
              {step.label}
            </p>
            <p className={clsx("text-xs", step.state === "failed" ? "text-danger" : "text-muted")}>{step.note}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function StepIcon({ state }: { state: StepState }) {
  if (state === "done") {
    return <CheckCircle2 className="mt-0.5 h-[18px] w-[18px] shrink-0 text-accent" aria-label="Xong" />;
  }
  if (state === "failed") {
    return <XCircle className="mt-0.5 h-[18px] w-[18px] shrink-0 text-danger" aria-label="Lỗi" />;
  }
  if (state === "active") {
    return (
      <span
        className="mt-0.5 h-[18px] w-[18px] shrink-0 animate-spin rounded-full border-2 border-border border-t-accent"
        role="img"
        aria-label="Đang chạy"
      />
    );
  }
  return <Circle className="mt-0.5 h-[18px] w-[18px] shrink-0 text-border" aria-label="Chưa tới" />;
}

function Detail({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-1 text-sm text-ink">{value}</dd>
    </div>
  );
}
