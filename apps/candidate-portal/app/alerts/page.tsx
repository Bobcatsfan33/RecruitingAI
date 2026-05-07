import { Card } from "@/components/card";

export default function AlertsPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Job alerts</h1>
        <p className="mt-1 text-sm text-secondary">
          Personalised matches with explanation. We tell you why a role fits, not just that it does.
        </p>
      </header>
      <Card title="Active alerts">
        <p className="text-sm text-secondary">No alerts configured.</p>
        <button className="mt-3 inline-flex items-center rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90">
          Set up an alert
        </button>
      </Card>
      <Card title="Recent matches" subtitle="Roles your profile lined up with this week">
        <p className="text-sm text-secondary">No matches yet. Profile freshness affects match quality.</p>
      </Card>
    </div>
  );
}
