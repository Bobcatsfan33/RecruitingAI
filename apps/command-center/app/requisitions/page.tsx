import { Card } from "@/components/ui/card";
import { DataTable, Column } from "@/components/ui/data-table";
import { Pill } from "@/components/ui/pill";

interface ReqRow {
  id: string;
  title: string;
  client: string;
  type: string;
  urgency: string;
  stage: string;
  inflight: number;
  budget: string;
}

const COLUMNS: Column<ReqRow>[] = [
  { key: "title", header: "Requisition", render: (r) => (
      <div>
        <div className="font-medium">{r.title}</div>
        <div className="text-xs text-secondary">{r.client}</div>
      </div>
    ),
  },
  { key: "type", header: "Type", render: (r) => <Pill tone="info">{r.type}</Pill> },
  { key: "urgency", header: "Urgency", render: (r) => (
      <Pill tone={r.urgency === "critical_48h" ? "danger" : "neutral"}>{r.urgency}</Pill>
    ),
  },
  { key: "stage", header: "Stage", render: (r) => <Pill tone="stage" stage={r.stage}>{r.stage}</Pill> },
  { key: "inflight", header: "In flight", render: (r) => <span className="tabular-nums">{r.inflight}</span> },
  { key: "budget", header: "Budget" },
];

export default function RequisitionsPage() {
  const rows: ReqRow[] = [];
  return (
    <div className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Requisitions</h1>
        <Pill tone="info">{rows.length} active</Pill>
      </header>
      <Card>
        <DataTable<ReqRow>
          columns={COLUMNS}
          rows={rows}
          rowKey={(r, i) => `${r.id}-${i}`}
          emptyState="No requisitions yet. Create one via POST /v1/requisitions or load synthetic seeds."
        />
      </Card>
    </div>
  );
}
