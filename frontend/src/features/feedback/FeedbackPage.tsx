import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import type { FeedbackRating } from "../../api/types";
import { DataTable } from "../../components/data/DataTable";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { FieldWrapper, SelectInput, TextInput } from "../../components/ui/Field";
import { Pagination } from "../../components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatDateTime, truncateMiddle } from "../../lib/format";

export function FeedbackPage() {
  const [page, setPage] = useState(1);
  const [rating, setRating] = useState<FeedbackRating | "">("");
  const [departmentId, setDepartmentId] = useState("");

  const feedbackQuery = useQuery({
    queryKey: ["feedback", page, rating, departmentId],
    queryFn: () => apiClient.feedback.list({ page, page_size: 20, rating: rating || undefined, department_id: departmentId.trim() || undefined }),
  });

  const rows = feedbackQuery.data?.data ?? [];

  return (
    <div>
      <PageHeader title="Feedback management" description="Report data is scoped by backend RBAC and never includes chat question or answer text." />
      <section className="mb-4 grid gap-3 rounded-token border border-border bg-surface p-4 md:grid-cols-[12rem_1fr]">
        <FieldWrapper id="feedback-rating" label="Rating">
          <SelectInput id="feedback-rating" value={rating} onChange={(event) => { setPage(1); setRating(event.target.value as FeedbackRating | ""); }}>
            <option value="">All ratings</option>
            <option value="HELPFUL">Helpful</option>
            <option value="NOT_HELPFUL">Not helpful</option>
          </SelectInput>
        </FieldWrapper>
        <FieldWrapper id="feedback-department" label="Department ID">
          <TextInput id="feedback-department" value={departmentId} onChange={(event) => { setPage(1); setDepartmentId(event.target.value); }} />
        </FieldWrapper>
      </section>
      {feedbackQuery.isLoading ? <LoadingState label="Loading feedback" /> : null}
      {feedbackQuery.isError ? <ErrorState message={safeErrorMessage(feedbackQuery.error)} onRetry={() => void feedbackQuery.refetch()} /> : null}
      {!feedbackQuery.isLoading && rows.length === 0 ? <EmptyState title="No feedback found" /> : null}
      {rows.length ? (
        <>
          <DataTable columns={["Rating", "Reason", "User", "Department", "Updated"]}>
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="px-4 py-3"><Badge tone={row.rating === "HELPFUL" ? "success" : "warning"}>{row.rating}</Badge></td>
                <td className="max-w-lg px-4 py-3 text-sm text-muted">{row.reason ?? "No reason"}</td>
                <td className="px-4 py-3 text-muted">{truncateMiddle(row.user_id)}</td>
                <td className="px-4 py-3 text-muted">{row.department_id ? truncateMiddle(row.department_id) : "Unscoped"}</td>
                <td className="px-4 py-3 text-muted">{formatDateTime(row.updated_at)}</td>
              </tr>
            ))}
          </DataTable>
          {feedbackQuery.data?.meta ? <Pagination meta={feedbackQuery.data.meta} onPageChange={setPage} /> : null}
        </>
      ) : null}
    </div>
  );
}