import { useQuery } from "@tanstack/react-query";
import { clsx } from "clsx";
import { useMemo, useState } from "react";
import { apiClient } from "../../api/client";
import type { AuthenticatedUser, FeedbackRating, FeedbackReportItem } from "../../api/types";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { FieldWrapper, SelectInput } from "../../components/ui/Field";
import { Pagination } from "../../components/ui/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/State";
import { formatDateTime, truncateMiddle } from "../../lib/format";
import { feedbackRatingLabels } from "../../lib/labels";
import { useAuth } from "../auth/AuthProvider";

const RATING_FILTERS: { value: FeedbackRating | ""; label: string }[] = [
  { value: "", label: "Tất cả" },
  { value: "HELPFUL", label: feedbackRatingLabels.HELPFUL },
  { value: "NOT_HELPFUL", label: feedbackRatingLabels.NOT_HELPFUL },
];

export function FeedbackPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";
  const [page, setPage] = useState(1);
  const [rating, setRating] = useState<FeedbackRating | "">("");
  const [departmentId, setDepartmentId] = useState("");

  const feedbackQuery = useQuery({
    queryKey: ["feedback", page, rating, departmentId],
    queryFn: () =>
      apiClient.feedback.list({
        page,
        page_size: 20,
        rating: rating || undefined,
        department_id: departmentId || undefined,
      }),
  });

  // API_SPEC §9: the department filter is Admin-only; a Manager already sees only their department.
  const departmentsQuery = useQuery({
    queryKey: ["departments", "feedback-filter"],
    queryFn: () => apiClient.departments.list({ page: 1, page_size: 100 }),
    enabled: isAdmin,
    staleTime: 5 * 60_000,
  });
  const departmentNames = useMemo(
    () => new Map((departmentsQuery.data?.data ?? []).map((department) => [department.id, department.name])),
    [departmentsQuery.data],
  );

  const rows = feedbackQuery.data?.data ?? [];

  return (
    <div>
      {/* D-1: question and answer text are never shown here (API_SPEC §9 does not return them). */}
      <PageHeader
        title="Phản hồi câu trả lời"
        description="Đánh giá của người dùng cho từng câu trả lời. Nội dung câu hỏi và câu trả lời không hiện ở đây để giữ riêng tư."
      />
      <section className="mb-5 flex flex-wrap items-end gap-4" aria-label="Bộ lọc phản hồi">
        <div role="group" aria-label="Lọc theo đánh giá" className="inline-flex rounded-token bg-elevated p-1">
          {RATING_FILTERS.map((option) => (
            <button
              key={option.value || "all"}
              type="button"
              aria-pressed={rating === option.value}
              className={clsx(
                "rounded-[6px] px-3.5 py-1.5 text-sm transition",
                rating === option.value ? "bg-surface font-medium text-ink shadow-sm" : "text-muted hover:text-ink",
              )}
              onClick={() => {
                setPage(1);
                setRating(option.value);
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
        {isAdmin ? (
          <div className="w-60">
            <FieldWrapper id="feedback-department" label="Phòng ban">
              <SelectInput
                id="feedback-department"
                value={departmentId}
                onChange={(event) => {
                  setPage(1);
                  setDepartmentId(event.target.value);
                }}
              >
                <option value="">Tất cả phòng ban</option>
                {(departmentsQuery.data?.data ?? []).map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </SelectInput>
            </FieldWrapper>
          </div>
        ) : null}
        {feedbackQuery.data ? (
          <p className="ml-auto text-sm text-muted">{feedbackQuery.data.meta.total} phản hồi</p>
        ) : null}
      </section>

      {feedbackQuery.isLoading ? <LoadingState label="Đang tải phản hồi" /> : null}
      {feedbackQuery.isError ? (
        <ErrorState
          title="Không tải được phản hồi"
          error={feedbackQuery.error}
          onRetry={() => void feedbackQuery.refetch()}
        />
      ) : null}
      {!feedbackQuery.isLoading && !feedbackQuery.isError && rows.length === 0 ? (
        <EmptyState title="Chưa có phản hồi phù hợp" />
      ) : null}
      {rows.length ? (
        <>
          <ul className="flex flex-col gap-3">
            {rows.map((row) => (
              <li key={row.id} className="rounded-xl border border-border/70 bg-surface px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge tone={row.rating === "HELPFUL" ? "success" : "warning"}>{feedbackRatingLabels[row.rating]}</Badge>
                  <span className="text-xs text-muted">{formatDateTime(row.updated_at)}</span>
                </div>
                <p className="mt-3 text-sm text-ink/80">
                  <span className="text-muted">Ghi chú: </span>
                  {row.reason ?? "Không có ghi chú."}
                </p>
                <p className="mt-3 text-xs text-muted">
                  {/* TODO(BR-4 followup): user_full_name / department_name when the response carries them. */}
                  Người dùng {truncateMiddle(row.user_id, 14)} · {departmentText(row, user, departmentNames)}
                </p>
              </li>
            ))}
          </ul>
          {feedbackQuery.data?.meta ? <Pagination meta={feedbackQuery.data.meta} onPageChange={setPage} /> : null}
        </>
      ) : null}
    </div>
  );
}

function departmentText(
  row: FeedbackReportItem,
  user: AuthenticatedUser | null,
  departmentNames: ReadonlyMap<string, string>,
): string {
  if (!row.department_id) {
    return "Không thuộc phòng ban";
  }
  if (row.department_id === user?.department_id && user.department_name) {
    return user.department_name;
  }
  return departmentNames.get(row.department_id) ?? "Phòng ban";
}
