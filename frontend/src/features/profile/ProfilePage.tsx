import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Panel } from "../../components/ui/Panel";
import { roleLabel } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";

export function ProfilePage() {
  const { user } = useAuth();
  return (
    <div>
      <PageHeader title="Profile and account" description="Current user data is loaded from the backend on each authenticated session check." />
      <Panel className="max-w-2xl p-5">
        <dl className="grid gap-4 sm:grid-cols-2">
          <Detail label="Name" value={user?.full_name ?? "Unavailable"} />
          <Detail label="Email" value={user?.email ?? "Unavailable"} />
          <Detail label="Role" value={user ? <Badge tone="accent">{roleLabel(user.role)}</Badge> : "Unavailable"} />
          <Detail label="Department" value={user?.department_id ?? "Unscoped"} />
          <Detail label="Account" value={user?.is_active ? <Badge tone="success">ACTIVE</Badge> : <Badge tone="danger">INACTIVE</Badge>} />
        </dl>
      </Panel>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-muted">{label}</dt>
      <dd className="mt-1 break-words text-sm text-ink">{value}</dd>
    </div>
  );
}