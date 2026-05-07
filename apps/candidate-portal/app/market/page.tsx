import { Card } from "@/components/card";
import { Stat } from "@/components/stat";

export default function MarketPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Market</h1>
        <p className="mt-1 text-sm text-secondary">
          Comp benchmarks for your role + location + clearance band, refreshed monthly from verified candidate data.
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-4">
        <Stat label="p25" value="—" />
        <Stat label="p50 (median)" value="—" />
        <Stat label="p75" value="—" />
        <Stat label="p90" value="—" />
      </div>
      <Card title="Demand for your skills" subtitle="30-day vs 90-day momentum">
        <p className="text-sm text-secondary">
          Wire <code className="rounded bg-primary/10 px-1.5 py-0.5 text-xs">POST /api/v1/market/velocity</code>
          {" "}with your skills + clearance to populate.
        </p>
      </Card>
      <Card title="Career trajectory recommendations">
        <p className="text-sm text-secondary">
          When ML models are warm (post-Sprint 9), this surface shows roles your background most resembles.
        </p>
      </Card>
    </div>
  );
}
