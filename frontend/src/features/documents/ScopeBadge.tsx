import type { AuthenticatedUser, DocumentItem } from "../../api/types";
import { Badge } from "../../components/ui/Badge";
import { accessScopeLabels } from "../../lib/labels";
import { visibleDepartmentName } from "../../lib/permissions";

const tones = { ORGANIZATION: "neutral", DEPARTMENT: "warning", PRIVATE: "accent" } as const;

/**
 * Names a Department only from data already in hand: the document's department_name (Admin callers only,
 * BR-4 option a) or the viewer's own department from /auth/me. Never looks names up.
 */
export function ScopeBadge({
  document,
  user,
}: {
  document: Pick<DocumentItem, "access_scope" | "department_id" | "department_name">;
  user: AuthenticatedUser | null;
}) {
  const name =
    document.access_scope === "DEPARTMENT"
      ? visibleDepartmentName(document.department_id, document.department_name, user)
      : null;
  return <Badge tone={tones[document.access_scope]}>{name ?? accessScopeLabels[document.access_scope]}</Badge>;
}
