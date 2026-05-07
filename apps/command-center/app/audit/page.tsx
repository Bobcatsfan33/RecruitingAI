import { Card } from "@/components/ui/card";
import { DataTable, Column } from "@/components/ui/data-table";
import { Pill } from "@/components/ui/pill";

interface AuditRow {
  ts: string;
  agent: string;
  action: string;
  candidate: string;
  decision: string;
  confidence: number;
  cost: string;
}

const COLUMNS: Column<AuditRow>[] = [
  { key: "ts", header: "Timestamp", render: (r) => <span className="font-mono text-xs text-secondary">{r.ts}</span> },
  { key: "agent", header: "Agent" },
  { key: "action", header: "Action", render: (r) => <Pill tone="info">{r.action}</Pill> },
  { key: "candidate", header: "Candidate" },
  { key: "decision", header: "Decision" },
  { key: "confidence", header: "Confidence", render: (r) => <span className="tabular-nums">{r.confidence.toFixed(2)}</span> },
  { key: "cost", header: "Cost" },
];

export default function AuditPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Audit log</h1>
        <p className="text-sm text-secondary">
          Every AI decision is recorded for EEOC / OFCCP / contract compliance. 7-year retention.
        </p>
      </header>
      <Card>
        <DataTable<AuditRow>
          columns={COLUMNS}
          rows={[]}
          rowKey={(r, i) => `${r.ts}-${i}`}
          emptyState="No audit entries yet. Wire the screening or pipeline service to ClickHouse to populate."
        />
      </Card>
    </div>
  );
}
