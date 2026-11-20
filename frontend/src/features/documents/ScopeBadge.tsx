import type { AuthenticatedUser, DocumentItem } from "../../api/types";
import { Badge } from "../../components/ui/Badge";
import { accessScopeLabels } from "../../lib/labels";

const tones = { ORGANIZATION: "neutral", DEPARTMENT: "warning", PRIVATE: "accent" } as const;

/** Names a Department only when it is the viewer's own (BR-4 department_name); never looks names up. */
export function ScopeBadge({
  document,
  user,
}: {
  document: Pick<DocumentItem, "access_scope" | "department_id">;
  user: AuthenticatedUser | null;
}) {
  const ownDepartment =
    document.access_scope === "DEPARTMENT" && user?.department_id && user.department_id === document.department_id
      ? user.department_name
      : null;
  return <Badge tone={tones[document.access_scope]}>{ownDepartment ?? accessScopeLabels[document.access_scope]}</Badge>;
}
