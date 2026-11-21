import { useQuery } from "@tanstack/react-query";
import { Download, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { apiClient } from "../../api/client";
import { ApiError } from "../../api/errors";
import { ErrorState, LoadingState } from "../../components/ui/State";

type FileState =
  | { status: "loading" }
  | { status: "ready"; url: string; mimeType: string; filename: string | null }
  | { status: "error"; error: unknown };

/**
 * D-7: opens a document at a page in its own tab. Fetches GET /documents/{id}/preview (BR-2) with the
 * Bearer token (a plain link cannot send it), shows it through a blob: URL and revokes the URL on leave.
 */
export function DocumentViewerPage() {
  const { documentId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const requestedPage = Number(searchParams.get("page"));
  const page = Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : null;
  const [file, setFile] = useState<FileState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  const detailQuery = useQuery({
    queryKey: ["documents", documentId],
    queryFn: () => apiClient.documents.detail(documentId),
    enabled: Boolean(documentId),
    retry: false,
  });
  const title = detailQuery.data?.data.title ?? "Tài liệu";

  useEffect(() => {
    let cancelled = false;
    let url: string | null = null;
    apiClient.documents
      .preview(documentId)
      .then(({ blob, filename }) => {
        if (cancelled) {
          return;
        }
        url = URL.createObjectURL(blob);
        setFile({ status: "ready", url, mimeType: blob.type, filename });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setFile({ status: "error", error });
        }
      });
    return () => {
      cancelled = true;
      if (url) {
        URL.revokeObjectURL(url);
      }
    };
  }, [documentId, attempt]);

  const mimeType = file.status === "ready" ? file.mimeType || (detailQuery.data?.data.mime_type ?? "") : "";
  const isImage = mimeType === "image/png" || mimeType === "image/jpeg";

  const close = () => {
    window.close();
    // Only reached when the browser refuses to close a tab it did not open from script.
    navigate(`/documents/${documentId}`);
  };

  return (
    <div className="flex h-[100dvh] flex-col bg-canvas text-ink">
      <header className="flex min-h-14 shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border bg-surface px-4 py-2 sm:px-6">
        <div className="flex min-w-0 items-baseline gap-3">
          <h1 className="truncate text-[15px] font-semibold">{title}</h1>
          {page && !isImage ? <span className="shrink-0 text-sm text-muted">Trang {page}</span> : null}
        </div>
        <div className="flex items-center gap-2">
          {file.status === "ready" ? (
            <a
              href={file.url}
              download={file.filename ?? detailQuery.data?.data.original_filename ?? "tai-lieu"}
              className="inline-flex min-h-9 items-center gap-2 rounded-token border border-border bg-surface px-3 text-sm transition hover:bg-canvas"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              Tải xuống
            </a>
          ) : null}
          <button
            type="button"
            className="inline-flex min-h-9 items-center gap-2 rounded-token border border-border bg-surface px-3 text-sm transition hover:bg-canvas"
            onClick={close}
          >
            <X className="h-4 w-4" aria-hidden="true" />
            Đóng
          </button>
        </div>
      </header>

      <main className="min-h-0 flex-1">
        {file.status === "loading" ? (
          <div className="p-6">
            <LoadingState label="Đang tải tài liệu" />
          </div>
        ) : null}
        {file.status === "error" ? (
          <div className="mx-auto max-w-xl p-6">
            <ErrorState
              title="Không mở được tài liệu"
              message={viewerErrorMessage(file.error)}
              error={file.error}
              onRetry={() => {
                setFile({ status: "loading" });
                setAttempt((current) => current + 1);
              }}
            />
          </div>
        ) : null}
        {file.status === "ready" && isImage ? (
          <div className="flex h-full items-center justify-center overflow-auto p-4">
            <img src={file.url} alt={title} className="max-h-full max-w-full object-contain" />
          </div>
        ) : null}
        {file.status === "ready" && !isImage ? (
          <iframe
            title={page ? `${title}, trang ${page}` : title}
            src={page ? `${file.url}#page=${page}` : file.url}
            className="h-full w-full border-0 bg-surface"
          />
        ) : null}
      </main>
    </div>
  );
}

function viewerErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 404) {
    return "Không tìm thấy tài liệu, hoặc bạn không có quyền xem tài liệu này.";
  }
  if (error instanceof ApiError && error.status === 410) {
    return "Tệp gốc của tài liệu này không còn trên máy chủ.";
  }
  if (error instanceof ApiError) {
    return "Máy chủ không trả được tệp. Thử lại sau ít phút.";
  }
  return "Không tải được tệp. Kiểm tra kết nối mạng rồi thử lại.";
}
