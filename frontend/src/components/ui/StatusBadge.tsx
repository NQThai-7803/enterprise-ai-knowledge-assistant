import { useState } from "react";
import type { DocumentStatus } from "../../api/types";
import { documentStatusLabels } from "../../lib/labels";
import { Badge } from "./Badge";

const tones = {
  READY: "success",
  FAILED: "danger",
  PROCESSING: "warning",
  ARCHIVED: "neutral",
  UPLOADED: "accent",
} as const;

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  // Only a status that changes while on screen animates; rows that load READY stay still.
  const [firstStatus] = useState(status);
  return (
    <Badge key={status} tone={tones[status]} className={status !== firstStatus ? "pop" : undefined}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {documentStatusLabels[status]}
    </Badge>
  );
}
