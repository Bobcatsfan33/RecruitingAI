import { Card } from "@/components/ui/card";
import { DataTable, Column } from "@/components/ui/data-table";
import { Pill } from "@/components/ui/pill";

interface ClientRow {
  name: string;
  industry: string;
  contracts: string;
  active_reqs: number;
  health: "good" | "watch" | "at_risk";
}

const COLUMNS: Column<ClientRow>[] = [
  { key: "name", header: "Client", render: (r) => <div className="font-medium">{r.name}</div> },
  { key: "industry", header: "Industry" },
  { key: "contracts", header: "Vehicles" },
  { key: "active_reqs", header: "Active reqs", render: (r) => <span className="tabular-nums">{r.active_reqs}</span> },
  { key: "health", header: "Health", render: (r) => (
      <Pill tone={r.health === "good" ? "success" : r.health === "watch" ? "warning" : "danger"}>{r.health}</Pill>
    ),
  },
];

export default function ClientsPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Clients</h1>
        <p className="text-sm text-secondary">Accounts + their pipeline health.</p>
      </header>
      <Card>
        <DataTable<ClientRow>
          columns={COLUMNS}
          rows={[]}
          rowKey={(_, i) => `client-${i}`}
          emptyState="No clients yet."
        />
      </Card>
    </div>
  );
}
