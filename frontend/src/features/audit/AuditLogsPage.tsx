import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Fragment, useState } from "react";
import { apiClient } from "../../api/client";
import { isApiError, safeErrorMessage } from "../../api/errors";
import type { AuditLogItem } from "../../api/types";
import { DataTable } from "../../components/data/DataTable";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { FieldWrapper, SelectInput, TextInput } from "../../components/ui/Field";
import { Pagination } from "../../components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatDateTime, truncateMiddle } from "../../lib/format";
import { auditOutcomeLabels } from "../../lib/labels";
import { AUDIT_EVENT_GROUPS, RESERVED_AUDIT_EVENTS, auditTargetLabels } from "./auditEventTypes";

type Outcome = AuditLogItem["outcome"];

export function AuditLogsPage() {
  const [page, setPage] = useState(1);
  const [outcome, setOutcome] = useState<Outcome | "">("");
  const [eventType, setEventType] = useState("");
  const [requestId, setRequestId] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const auditQuery = useQuery({
    queryKey: ["audit", page, outcome, eventType, requestId],
    queryFn: () =>
      apiClient.audit.list({
        page,
        page_size: 25,
        outcome: outcome || undefined,
        event_type: eventType || undefined,
        request_id: requestId.trim() || undefined,
      }),
    retry: (failureCount, error) => !isApiError(error) && failureCount < 2,
  });

  const rows = auditQuery.data?.items ?? [];
  const filterInvalid = isApiError(auditQuery.error) && auditQuery.error.code === "AUDIT_FILTER_INVALID";
  const resetFilters = () => {
    setPage(1);
    setOutcome("");
    setEventType("");
    setRequestId("");
  };

  // No decorative motion on this screen (motion rules): rows expand instantly.
  return (
    <div>
      <PageHeader
        title="Nhật ký hệ thống"
        description="Ghi nhận đăng nhập, tài liệu, phân quyền và hỏi đáp. Không lưu nội dung câu hỏi hay mật khẩu."
      />
      <section className="mb-5 grid gap-3 md:grid-cols-[18rem_12rem_minmax(0,1fr)]" aria-label="Bộ lọc nhật ký">
        <FieldWrapper id="audit-event" label="Loại sự kiện">
          <SelectInput
            id="audit-event"
            value={eventType}
            onChange={(event) => {
              setPage(1);
              setEventType(event.target.value);
            }}
          >
            <option value="">Tất cả sự kiện</option>
            {AUDIT_EVENT_GROUPS.map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.types.map((type) => (
                  <option key={type} value={type}>
                    {RESERVED_AUDIT_EVENTS.has(type) ? `${type} (không còn ghi)` : type}
                  </option>
                ))}
              </optgroup>
            ))}
          </SelectInput>
        </FieldWrapper>
        <FieldWrapper id="audit-outcome" label="Kết quả">
          <SelectInput
            id="audit-outcome"
            value={outcome}
            onChange={(event) => {
              setPage(1);
              setOutcome(event.target.value as Outcome | "");
            }}
          >
            <option value="">Tất cả</option>
            {(Object.keys(auditOutcomeLabels) as Outcome[]).map((value) => (
              <option key={value} value={value}>
                {auditOutcomeLabels[value]}
              </option>
            ))}
          </SelectInput>
        </FieldWrapper>
        <FieldWrapper id="audit-request" label="Request ID">
          <TextInput
            id="audit-request"
            className="font-mono"
            placeholder="Dán request ID để tra cứu"
            value={requestId}
            onChange={(event) => {
              setPage(1);
              setRequestId(event.target.value);
            }}
          />
        </FieldWrapper>
      </section>

      {auditQuery.isLoading ? <LoadingState label="Đang tải nhật ký" /> : null}
      {filterInvalid ? (
        <div className="space-y-3">
          <ErrorState
            title="Bộ lọc không hợp lệ"
            message={`Kiểm tra lại loại sự kiện hoặc request ID. ${safeErrorMessage(auditQuery.error)}`}
          />
          <Button type="button" variant="secondary" onClick={resetFilters}>
            Xóa bộ lọc
          </Button>
        </div>
      ) : null}
      {auditQuery.isError && !filterInvalid ? (
        <ErrorState
          title="Không tải được nhật ký"
          error={auditQuery.error}
          onRetry={() => void auditQuery.refetch()}
        />
      ) : null}
      {!auditQuery.isLoading && !auditQuery.isError && rows.length === 0 ? (
        <EmptyState title="Không có bản ghi phù hợp" />
      ) : null}
      {rows.length ? (
        <>
          <DataTable columns={["Thời gian", "Sự kiện", "Người thực hiện", "Đối tượng", "Kết quả", ""]}>
            {rows.map((row) => {
              const expanded = expandedId === row.id;
              return (
                <Fragment key={row.id}>
                  <tr>
                    <td className="whitespace-nowrap px-5 py-3 font-mono text-xs text-ink/80">
                      {formatDateTime(row.created_at, "dd/MM/yyyy HH:mm:ss")}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-ink">{row.event_type}</td>
                    <td className="px-5 py-3 text-ink/80">
                      {/* TODO(BR-4 followup): actor name when the response carries it. */}
                      {row.actor_user_id ? truncateMiddle(row.actor_user_id, 14) : "Hệ thống"}
                    </td>
                    <td className="px-5 py-3 text-ink/80">
                      {row.target_type ? (auditTargetLabels[row.target_type] ?? row.target_type) : "—"}
                    </td>
                    <td className="px-5 py-3">
                      <Badge tone={row.outcome === "SUCCESS" ? "success" : "danger"}>
                        {auditOutcomeLabels[row.outcome]}
                      </Badge>
                    </td>
                    <td className="px-3 py-3 text-right">
                      <button
                        type="button"
                        className="flex h-8 w-8 items-center justify-center rounded-token text-muted hover:bg-canvas hover:text-ink"
                        aria-expanded={expanded}
                        aria-label={expanded ? "Ẩn chi tiết" : "Xem chi tiết"}
                        onClick={() => setExpandedId(expanded ? null : row.id)}
                      >
                        {expanded ? (
                          <ChevronDown className="h-4 w-4" aria-hidden="true" />
                        ) : (
                          <ChevronRight className="h-4 w-4" aria-hidden="true" />
                        )}
                      </button>
                    </td>
                  </tr>
                  {expanded ? (
                    <tr>
                      <td colSpan={6} className="px-5 pb-4">
                        <dl className="grid gap-4 rounded-token border border-border/70 bg-elevated p-4 sm:grid-cols-3">
                          <AuditDetail label="Request ID" value={row.request_id ?? "Không có"} mono />
                          <AuditDetail label="Mã lỗi" value={row.error_code ?? "Không có"} mono />
                          <AuditDetail
                            label="Loại đối tượng"
                            value={row.target_type ? `${row.target_type} ${row.target_id ?? ""}`.trim() : "Không có"}
                            mono
                          />
                          <div className="sm:col-span-3">
                            <dt className="text-xs text-muted">Metadata</dt>
                            <dd>
                              <pre className="mt-1 whitespace-pre-wrap break-all font-mono text-xs text-ink/80">
                                {JSON.stringify(row.metadata, null, 2)}
                              </pre>
                            </dd>
                          </div>
                        </dl>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </DataTable>
          {auditQuery.data ? (
            <Pagination
              meta={{
                page: auditQuery.data.page,
                page_size: auditQuery.data.page_size,
                total: auditQuery.data.total,
                total_pages: auditQuery.data.total_pages,
              }}
              onPageChange={setPage}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function AuditDetail({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className={mono ? "mt-1 break-all font-mono text-xs text-ink" : "mt-1 text-sm text-ink"}>{value}</dd>
    </div>
  );
}
