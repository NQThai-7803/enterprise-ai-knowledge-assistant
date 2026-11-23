import { ChevronLeft, ChevronRight } from "lucide-react";
import type { PaginationMeta } from "../../api/types";
import { Button } from "./Button";

export function Pagination({
  meta,
  onPageChange,
}: {
  meta: PaginationMeta;
  onPageChange: (page: number) => void;
}) {
  const canPrevious = meta.page > 1;
  const canNext = meta.page < meta.total_pages;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-4 text-sm text-muted">
      <span>
        Trang {meta.page} / {Math.max(meta.total_pages, 1)} · {meta.total} kết quả
      </span>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={!canPrevious}
          onClick={() => onPageChange(meta.page - 1)}
          icon={<ChevronLeft className="h-4 w-4" aria-hidden="true" />}
        >
          Trước
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={!canNext}
          onClick={() => onPageChange(meta.page + 1)}
          icon={<ChevronRight className="h-4 w-4" aria-hidden="true" />}
        >
          Sau
        </Button>
      </div>
    </div>
  );
}