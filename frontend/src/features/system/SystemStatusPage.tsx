import { useQuery } from "@tanstack/react-query";
import { Activity, Database, Server, Wifi } from "lucide-react";
import { apiClient } from "../../api/client";
import { safeErrorMessage } from "../../api/errors";
import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { Panel } from "../../components/ui/Panel";
import { ErrorState, LoadingState } from "../../components/ui/State";

export function SystemStatusPage() {
  const liveQuery = useQuery({ queryKey: ["health", "live"], queryFn: apiClient.health.live, refetchInterval: 30_000 });
  const readyQuery = useQuery({ queryKey: ["health", "ready"], queryFn: apiClient.health.ready, refetchInterval: 30_000, retry: 1 });

  return (
    <div>
      <PageHeader title="System and LLM provider status" description="This page uses only current public backend health APIs and does not call external LLM providers." />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatusPanel icon={<Activity className="h-5 w-5" aria-hidden="true" />} label="API live" status={liveQuery.data?.status ?? (liveQuery.isError ? "unavailable" : "checking")} ok={liveQuery.data?.status === "ok"} />
        <StatusPanel icon={<Server className="h-5 w-5" aria-hidden="true" />} label="API ready" status={readyQuery.data?.status ?? (readyQuery.isError ? "unavailable" : "checking")} ok={readyQuery.data?.status === "ready"} />
        <StatusPanel icon={<Database className="h-5 w-5" aria-hidden="true" />} label="PostgreSQL" status={readyQuery.data?.checks.database ?? "unavailable"} ok={readyQuery.data?.checks.database === "ok"} />
        <StatusPanel icon={<Wifi className="h-5 w-5" aria-hidden="true" />} label="Redis" status={readyQuery.data?.checks.redis ?? "unavailable"} ok={readyQuery.data?.checks.redis === "ok"} />
      </div>

      {readyQuery.isLoading ? <LoadingState label="Checking readiness" /> : null}
      {readyQuery.isError ? <div className="mt-4"><ErrorState message={safeErrorMessage(readyQuery.error)} onRetry={() => void readyQuery.refetch()} /></div> : null}

      <Panel className="mt-4 p-5">
        <h3 className="text-sm font-semibold">LLM provider visibility</h3>
        <dl className="mt-4 grid gap-4 md:grid-cols-2">
          <StatusLine label="Provider status endpoint" value="Not exposed by current backend API" />
          <StatusLine label="External provider call" value="Not executed by frontend" />
          <StatusLine label="SSE capability" value="Chat endpoint supports POST text/event-stream" />
          <StatusLine label="Grounding strategy" value="buffer_after_validation" />
        </dl>
      </Panel>
    </div>
  );
}

function StatusPanel({ icon, label, status, ok }: { icon: React.ReactNode; label: string; status: string; ok: boolean }) {
  return (
    <Panel className="p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-accent">{icon}<span className="font-semibold text-ink">{label}</span></div>
        <Badge tone={ok ? "success" : status === "checking" ? "warning" : "danger"}>{status}</Badge>
      </div>
    </Panel>
  );
}

function StatusLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-muted">{label}</dt>
      <dd className="mt-1 text-sm text-ink">{value}</dd>
    </div>
  );
}