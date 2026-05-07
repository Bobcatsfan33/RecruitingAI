import { Card } from "@/components/ui/card";
import { Pill } from "@/components/ui/pill";

export default function BenchPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Bench management</h1>
        <p className="text-sm text-secondary">
          Active contractors + clearance expiration tracking + co-employment risk + redeployment.
        </p>
      </header>
      <Card title="Contractors on bench"><p className="text-sm text-secondary">No contractors yet.</p></Card>
      <Card title="Clearance expirations">
        <p className="text-sm text-secondary">Nothing expiring in the next 90 days. <Pill tone="success">all current</Pill></p>
      </Card>
      <Card title="Co-employment risk">
        <p className="text-sm text-secondary">No high-risk thresholds breached.</p>
      </Card>
    </div>
  );
}
