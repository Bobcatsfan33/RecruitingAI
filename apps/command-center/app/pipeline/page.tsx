import { Card } from "@/components/ui/card";
import { Pipeline } from "@/components/ui/pipeline";
import { Pill } from "@/components/ui/pill";

export default function PipelinePage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Pipeline</h1>
        <p className="text-sm text-secondary">
          Stage counts roll up across every active requisition. Click any stage to drill into the candidates currently sitting there.
        </p>
      </header>
      <Card title="Aggregate" subtitle="all requisitions, all stages">
        <Pipeline counts={{}} />
      </Card>
      <Card title="SLA breaches" subtitle="any stage > budget">
        <p className="text-sm text-secondary">No active SLA breaches. <Pill tone="success">healthy</Pill></p>
      </Card>
      <Card title="Silver-medalist health" subtitle="backups warm at penultimate stage">
        <p className="text-sm text-secondary">No requisitions currently at offer; backup pool not provisioned.</p>
      </Card>
    </div>
  );
}
