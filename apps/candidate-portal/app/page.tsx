import Link from "next/link";
import { Card } from "@/components/card";
import { Stat } from "@/components/stat";

export default function CandidateHome() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Welcome back.</h1>
        <p className="mt-2 text-sm text-secondary">
          Your career intelligence cockpit — comp benchmarks for your role, profile freshness, and any roles your background lines up with.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <Stat label="Profile freshness" value="—" hint="updates within last 90 days" />
        <Stat label="Open opportunities" value="—" hint="matching your profile" />
        <Stat label="Referrals submitted" value="—" hint="this year" />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Your profile" subtitle="What recruiters see">
          <p className="text-sm text-secondary">
            Connect your profile to populate. The platform never personalises signals to you — your data drives the match,
            not the other way around.
          </p>
          <Link
            href="/profile"
            className="mt-3 inline-flex items-center rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
          >
            Open profile
          </Link>
        </Card>
        <Card title="Market for your role" subtitle="Comp benchmarks + demand trends">
          <p className="text-sm text-secondary">
            Median comp + p25/p75 for your role + location + clearance, refreshed monthly.
          </p>
          <Link
            href="/market"
            className="mt-3 inline-flex items-center rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-primary/5"
          >
            View market
          </Link>
        </Card>
      </div>

      <Card title="Refer someone" subtitle="Earn a referral fee on hires">
        <p className="text-sm text-secondary">
          Refer a former colleague — if they're hired through the platform, you receive a referral fee on placement.
        </p>
        <Link
          href="/refer"
          className="mt-3 inline-flex items-center rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-primary/5"
        >
          Submit a referral
        </Link>
      </Card>
    </div>
  );
}
