import type { DocumentStatus } from "../../api/types";
import { Badge } from "./Badge";

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  if (status === "READY") return <Badge tone="success">READY</Badge>;
  if (status === "FAILED") return <Badge tone="danger">FAILED</Badge>;
  if (status === "PROCESSING") return <Badge tone="warning">PROCESSING</Badge>;
  if (status === "ARCHIVED") return <Badge tone="neutral">ARCHIVED</Badge>;
  return <Badge tone="accent">UPLOADED</Badge>;
}