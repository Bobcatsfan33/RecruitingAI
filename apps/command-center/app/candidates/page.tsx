"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { DataTable, Column } from "@/components/ui/data-table";
import { Pill } from "@/components/ui/pill";

interface CandidateRow {
  id: string;
  name: string;
  title: string;
  metro: string;
  clearance: string;
  motion: string;
  approachability: number;
  status: "active" | "passive" | "placed" | "do_not_contact" | "benched";
}

// Placeholder rows. Hook up to GET /api/v1/candidates/recent in production.
const SAMPLE: CandidateRow[] = [
  { id: "—", name: "—", title: "—", metro: "—", clearance: "—", motion: "—", approachability: 0, status: "active" },
];

const COLUMNS: Column<CandidateRow>[] = [
  { key: "name", header: "Candidate", render: (r) => (
      <div>
        <div className="font-medium">{r.name}</div>
        <div className="text-xs text-secondary">{r.title}</div>
      </div>
    ),
  },
  { key: "metro", header: "Metro" },
  { key: "clearance", header: "Clearance", render: (r) => (
      <Pill tone={r.clearance === "—" ? "neutral" : "info"}>{r.clearance}</Pill>
    ),
  },
  { key: "motion", header: "Motion" },
  {
    key: "approachability",
    header: "Approachability",
    render: (r) => (
      <Pill tone={r.approachability >= 70 ? "success" : r.approachability >= 40 ? "warning" : "neutral"}>
        {r.approachability || "—"}
      </Pill>
    ),
  },
  {
    key: "status",
    header: "Status",
    render: (r) => <Pill tone={r.status === "placed" ? "success" : r.status === "do_not_contact" ? "danger" : "neutral"}>{r.status}</Pill>,
  },
];

export default function CandidatesPage() {
  const [query, setQuery] = useState("");
  const filtered = SAMPLE.filter((r) =>
    [r.name, r.metro, r.title].some((s) => s.toLowerCase().includes(query.toLowerCase())),
  );
  return (
    <div className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Candidates</h1>
        <Pill tone="neutral">{filtered.length} shown</Pill>
      </header>
      <Card>
        <div className="mb-3 flex items-center gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by name, title, metro…"
            className="h-8 w-72 rounded-md border border-border bg-elevated px-3 text-sm outline-none focus:border-accent"
          />
        </div>
        <DataTable<CandidateRow>
          columns={COLUMNS}
          rows={filtered}
          rowKey={(r, i) => `${r.id}-${i}`}
          emptyState="No candidates yet. Use POST /v1/candidates or upload a resume to populate."
        />
      </Card>
    </div>
  );
}
