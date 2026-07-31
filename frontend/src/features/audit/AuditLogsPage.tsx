import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import { DataTable } from "../../components/data/DataTable";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { FieldWrapper, SelectInput, TextInput } from "../../components/ui/Field";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatDateTime, truncateMiddle } from "../../lib/format";

export function AuditLogsPage() {
  const [page, setPage] = useState(1);
  const [outcome, setOutcome] = useState<"SUCCESS" | "FAILURE" | "">("");
  const [eventType, setEventType] = useState("");
  const [requestId, setRequestId] = useState("");

  const auditQuery = useQuery({
    queryKey: ["audit", page, outcome, eventType, requestId],
    queryFn: () => apiClient.audit.list({ page, page_size: 25, outcome: outcome || undefined, event_type: eventType.trim() || undefined, request_id: requestId.trim() || undefined }),
  });

  const rows = auditQuery.data?.items ?? [];
  const totalPages = auditQuery.data?.total_pages ?? 0;

  return (
    <div>
      <PageHeader title="Audit log explorer" description="Admin-only operational log view. Sensitive bodies, prompts, tokens, and raw exceptions are not returned by the API." />
      <section className="mb-4 grid gap-3 rounded-token border border-border bg-surface p-4 md:grid-cols-[12rem_1fr_1fr]">
        <FieldWrapper id="audit-outcome" label="Outcome">
          <SelectInput id="audit-outcome" value={outcome} onChange={(event) => { setPage(1); setOutcome(event.target.value as "SUCCESS" | "FAILURE" | ""); }}>
            <option value="">All outcomes</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILURE">Failure</option>
          </SelectInput>
        </FieldWrapper>
        <FieldWrapper id="audit-event" label="Event type"><TextInput id="audit-event" value={eventType} onChange={(event) => { setPage(1); setEventType(event.target.value); }} /></FieldWrapper>
        <FieldWrapper id="audit-request" label="Request ID"><TextInput id="audit-request" value={requestId} onChange={(event) => { setPage(1); setRequestId(event.target.value); }} /></FieldWrapper>
      </section>
      {auditQuery.isLoading ? <LoadingState label="Loading audit logs" /> : null}
      {auditQuery.isError ? <ErrorState message={safeErrorMessage(auditQuery.error)} onRetry={() => void auditQuery.refetch()} /> : null}
      {!auditQuery.isLoading && rows.length === 0 ? <EmptyState title="No audit rows found" /> : null}
      {rows.length ? (
        <>
          <DataTable columns={["Event", "Outcome", "Actor", "Target", "Request", "Metadata", "Created"]}>
            {rows.map((row) => (
              <tr key={row.id} className="align-top">
                <td className="px-4 py-3 font-semibold text-ink">{row.event_type}</td>
                <td className="px-4 py-3"><Badge tone={row.outcome === "SUCCESS" ? "success" : "danger"}>{row.outcome}</Badge></td>
                <td className="px-4 py-3 text-muted">{row.actor_user_id ? truncateMiddle(row.actor_user_id) : "System"}</td>
                <td className="px-4 py-3 text-muted">{row.target_type ?? "None"}<br />{row.target_id ? truncateMiddle(row.target_id) : null}</td>
                <td className="px-4 py-3 text-muted">{row.request_id ? truncateMiddle(row.request_id) : "None"}</td>
                <td className="max-w-md px-4 py-3 font-mono text-xs text-muted"><pre className="whitespace-pre-wrap">{JSON.stringify(row.metadata, null, 2)}</pre></td>
                <td className="px-4 py-3 text-muted">{formatDateTime(row.created_at)}</td>
              </tr>
            ))}
          </DataTable>
          <div className="flex items-center justify-between border-t border-border px-4 py-3 text-sm text-muted">
            <span>Page {auditQuery.data?.page ?? page} of {Math.max(totalPages, 1)} - {auditQuery.data?.total ?? 0} total</span>
            <div className="flex gap-2">
              <Button type="button" variant="secondary" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</Button>
              <Button type="button" variant="secondary" disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>Next</Button>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}