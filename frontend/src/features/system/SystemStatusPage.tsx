import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { apiClient } from "../../api/client";
import type { AdminCheckStatus, AdminProviderStatus, AdminSystemResponse, DocumentStatus } from "../../api/types";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/State";
import { formatDateTime } from "../../lib/format";
import { documentStatusLabels } from "../../lib/labels";
import { useAuth } from "../auth/AuthProvider";

// Handoff (8): this screen shows Vietnamese labels; the raw enum or code is only in the tooltip (title).

type Tone = "success" | "warning" | "danger" | "neutral";

const providerStatus: Record<AdminProviderStatus["status"], { label: string; tone: Tone }> = {
  healthy: { label: "Hoạt động", tone: "success" },
  disabled: { label: "Tắt", tone: "neutral" },
  misconfigured: { label: "Cấu hình sai", tone: "danger" },
  unhealthy: { label: "Lỗi", tone: "danger" },
};

const checkStatus: Record<AdminCheckStatus, { label: string; tone: Tone }> = {
  ok: { label: "Bình thường", tone: "success" },
  degraded: { label: "Suy giảm", tone: "warning" },
  unavailable: { label: "Không phản hồi", tone: "danger" },
  disabled: { label: "Tắt", tone: "neutral" },
  misconfigured: { label: "Cấu hình sai", tone: "danger" },
  not_configured: { label: "Chưa cấu hình", tone: "neutral" },
};

const checkNames: Record<string, string> = {
  api: "API",
  postgres: "PostgreSQL",
  redis: "Redis",
  worker: "Xử lý nền (worker)",
  ocr: "Nhận dạng chữ (OCR)",
  embedding: "Tạo embedding",
  llm: "Mô hình ngôn ngữ",
  web_search: "Tìm kiếm web",
  streaming: "Truyền câu trả lời",
  conversation: "Bộ nhớ hội thoại",
};

const rerankerLabels = {
  cross_encoder: "Mô hình xếp hạng lại",
  lexical_fallback: "Theo từ khóa (dự phòng)",
  disabled: "Tắt",
} as const;

const environmentLabels: Record<string, string> = {
  production: "Vận hành",
  staging: "Thử nghiệm",
  development: "Phát triển",
  test: "Kiểm thử",
};

export function SystemStatusPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";
  const liveQuery = useQuery({ queryKey: ["health", "live"], queryFn: apiClient.health.live, refetchInterval: 30_000 });
  const readyQuery = useQuery({
    queryKey: ["health", "ready"],
    queryFn: apiClient.health.ready,
    refetchInterval: 30_000,
    retry: 1,
  });
  const systemQuery = useQuery({
    queryKey: ["admin", "system"],
    queryFn: apiClient.admin.system,
    enabled: isAdmin,
    retry: false,
  });

  const checkedAt = Math.max(liveQuery.dataUpdatedAt, readyQuery.dataUpdatedAt, systemQuery.dataUpdatedAt);
  const recheck = () => {
    void liveQuery.refetch();
    void readyQuery.refetch();
    if (isAdmin) {
      void systemQuery.refetch();
    }
  };
  const live = liveQuery.data;
  const ready = readyQuery.data;
  const system = systemQuery.data?.data;

  return (
    <div>
      <PageHeader
        title="Trạng thái hệ thống"
        description={`Kiểm tra lần cuối: ${checkedAt ? formatDateTime(new Date(checkedAt).toISOString(), "dd/MM/yyyy HH:mm:ss") : "đang kiểm tra"}`}
        actions={
          <Button
            type="button"
            variant="secondary"
            onClick={recheck}
            loading={liveQuery.isFetching || readyQuery.isFetching || systemQuery.isFetching}
            icon={<RefreshCw className="h-4 w-4" aria-hidden="true" />}
          >
            Kiểm tra lại
          </Button>
        }
      />

      <h2 className="mb-3 text-sm font-medium text-muted">Hạ tầng</h2>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <InfraCard
          label="API live"
          source="GET /health/live"
          state={live ? [live.status === "ok" ? "Hoạt động" : "Bất thường", live.status === "ok" ? "success" : "warning", live.status] : failed(liveQuery.isError)}
        />
        <InfraCard
          label="API ready"
          source="GET /health/ready"
          state={ready ? [ready.status === "ready" ? "Sẵn sàng" : "Chưa sẵn sàng", ready.status === "ready" ? "success" : "warning", ready.status] : failed(readyQuery.isError)}
        />
        <InfraCard label="PostgreSQL" source="checks.database" state={checkState(ready?.checks.database, readyQuery.isError)} />
        <InfraCard label="Redis" source="checks.redis" state={checkState(ready?.checks.redis, readyQuery.isError)} />
      </div>
      {readyQuery.isError ? (
        <div className="mt-3">
          <ErrorState title="API chưa sẵn sàng" error={readyQuery.error} onRetry={() => void readyQuery.refetch()} />
        </div>
      ) : null}

      <h2 className="mb-3 mt-7 text-sm font-medium text-muted">Mô hình ngôn ngữ và truy xuất</h2>
      <dl className="divide-y divide-border/70 rounded-xl border border-border/70 bg-surface">
        {isAdmin && system ? <ProviderRows system={system} /> : null}
        {ready?.reranker_mode ? (
          <Row label="Chế độ xếp hạng" value={<span title={ready.reranker_mode}>{rerankerLabels[ready.reranker_mode]}</span>} />
        ) : null}
        <Row label="Chiến lược trả lời" value="Chỉ dùng nguồn đã truy xuất, kiểm tra trích dẫn" />
        <Row label="Truyền câu trả lời (SSE)" value="Gửi sau khi kiểm tra xong" />
      </dl>
      {isAdmin && systemQuery.isLoading ? <LoadingState label="Đang tải trạng thái quản trị" rows={2} /> : null}
      {isAdmin && systemQuery.isError ? (
        <div className="mt-3">
          <ErrorState
            title="Không tải được trạng thái quản trị"
            error={systemQuery.error}
            onRetry={() => void systemQuery.refetch()}
          />
        </div>
      ) : null}
      {!isAdmin ? (
        <p className="mt-3 text-xs text-muted">Nhà cung cấp, mô hình và phiên bản chỉ hiện cho quản trị viên.</p>
      ) : null}

      {isAdmin && system ? (
        <>
          <h2 className="mb-3 mt-7 text-sm font-medium text-muted">Kiểm tra chi tiết</h2>
          <ul className="divide-y divide-border/70 rounded-xl border border-border/70 bg-surface">
            {system.health.checks.map((check) => (
              // The server's English message stays in the tooltip with the check's code.
              <li
                key={check.name}
                className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"
                title={[check.name, check.message].filter(Boolean).join(": ")}
              >
                <span className="text-sm text-ink">{checkNames[check.name] ?? check.name}</span>
                <Badge tone={checkStatus[check.status]?.tone ?? "neutral"} title={check.status}>
                  {checkStatus[check.status]?.label ?? check.status}
                </Badge>
              </li>
            ))}
          </ul>

          <h2 className="mb-3 mt-7 text-sm font-medium text-muted">Tài liệu theo trạng thái</h2>
          <div className="flex flex-wrap gap-2 rounded-xl border border-border/70 bg-surface px-5 py-4">
            <span className="mr-2 text-sm text-ink/80">{system.statistics.documents.total} tài liệu</span>
            {(Object.entries(system.statistics.documents.by_status) as [DocumentStatus, number][]).map(([status, count]) => (
              <Badge key={status} tone="neutral" title={status}>
                {documentStatusLabels[status] ?? status} · {count}
              </Badge>
            ))}
          </div>

          <h2 className="mb-3 mt-7 text-sm font-medium text-muted">Phiên bản</h2>
          <dl className="divide-y divide-border/70 rounded-xl border border-border/70 bg-surface">
            <Row label="Ứng dụng" value={`${system.version.app_name} ${system.version.version}`} />
            <Row
              label="Môi trường"
              value={<span title={system.version.environment}>{environmentLabels[system.version.environment] ?? system.version.environment}</span>}
            />
            <Row
              label="Migration"
              value={`${system.version.database_revision ?? "chưa rõ"} / ${system.version.migration_head}`}
              mono
            />
            <Row label="Khởi động lúc" value={formatDateTime(system.version.started_at)} />
          </dl>
        </>
      ) : null}

      <p className="mt-4 text-xs text-muted">
        Chỉ hiển thị thông tin backend thật sự cung cấp. Khóa API và URL nội bộ không bao giờ hiện ở đây.
      </p>
    </div>
  );
}

function ProviderRows({ system }: { system: AdminSystemResponse }) {
  const { llm, web_search: webSearch } = system.providers;
  return (
    <>
      <Row label="Nhà cung cấp LLM" value={<ProviderValue provider={llm} />} />
      <Row label="Mô hình" value={llm.model ?? "Chưa cấu hình"} mono={Boolean(llm.model)} />
      <Row label="Tìm kiếm web" value={<ProviderValue provider={webSearch} />} />
    </>
  );
}

function ProviderValue({ provider }: { provider: AdminProviderStatus }) {
  const status = providerStatus[provider.status];
  return (
    <span className="inline-flex items-center gap-2" title={provider.provider}>
      {provider.display_name ?? provider.provider}
      <Badge tone={status?.tone ?? "neutral"} title={provider.status}>
        {status?.label ?? provider.status}
      </Badge>
    </span>
  );
}

type InfraState = [label: string, tone: Tone, code: string];

function failed(isError: boolean): InfraState | null {
  return isError ? ["Không phản hồi", "danger", "unavailable"] : null;
}

function checkState(value: string | undefined, isError: boolean): InfraState | null {
  if (value) {
    return value === "ok" ? ["Bình thường", "success", value] : ["Lỗi", "danger", value];
  }
  return failed(isError);
}

function InfraCard({ label, source, state }: { label: string; source: string; state: InfraState | null }) {
  return (
    <section className="rounded-xl border border-border/70 bg-surface p-4" aria-label={label}>
      <p className="text-sm font-medium text-ink">{label}</p>
      <div className="my-2.5">
        {state ? (
          <Badge tone={state[1]} title={state[2]}>
            <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
            {state[0]}
          </Badge>
        ) : (
          <Badge tone="neutral">Đang kiểm tra</Badge>
        )}
      </div>
      <p className="font-mono text-xs text-muted">{source}</p>
    </section>
  );
}

function Row({ label, value, mono = false }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
      <dt className="text-sm text-ink/80">{label}</dt>
      <dd className={mono ? "font-mono text-sm font-medium text-ink" : "text-sm font-medium text-ink"}>{value}</dd>
    </div>
  );
}
