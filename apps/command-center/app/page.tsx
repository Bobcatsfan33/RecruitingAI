import { Card } from "@/components/ui/card";
import { Pipeline } from "@/components/ui/pipeline";
import { Pill } from "@/components/ui/pill";

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <header className="flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Talent Command Center</h1>
          <p className="text-sm text-secondary">
            Pipeline at a glance. Real-time signals from every agent.
          </p>
        </div>
        <Pill tone="info">Internal preview</Pill>
      </header>

      <div className="grid gap-4 md:grid-cols-4">
        <Stat label="Active reqs" value="—" hint="connect /requisitions to populate" />
        <Stat label="Candidates in pipeline" value="—" hint="connect /pipeline" />
        <Stat label="Submissions this week" value="—" hint="last 7 days" />
        <Stat label="Falloff rate" value="—" hint="Close Protection telemetry" />
      </div>

      <Card title="Aggregate pipeline" subtitle="all active requisitions, current stage counts">
        <Pipeline counts={{}} />
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Velocity reqs (≤48h SLA)">
          <p className="text-sm text-secondary">No velocity-tier reqs in flight.</p>
        </Card>
        <Card title="Precision reqs (≥$300K OTE)">
          <p className="text-sm text-secondary">No precision-tier reqs in flight.</p>
        </Card>
      </div>

      <Card title="Recent agent activity" subtitle="audit log feed (last 25 events)">
        <p className="text-sm text-secondary">
          Wire up the candidates service + audit endpoint to populate this stream.
        </p>
      </Card>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card variant="flat">
      <div className="text-xs uppercase tracking-wide text-secondary">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-tertiary">{hint}</div>}
    </Card>
  );
}
