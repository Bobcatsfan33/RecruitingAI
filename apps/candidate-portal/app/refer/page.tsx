"use client";

import { useState } from "react";
import { Card } from "@/components/card";

export default function ReferPage() {
  const [referralName, setReferralName] = useState("");
  const [referralEmail, setReferralEmail] = useState("");
  const [referralCompany, setReferralCompany] = useState("");
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Refer a colleague</h1>
        <p className="mt-1 text-sm text-secondary">
          Solicited 90 days post-placement. If your referral is hired through us, you receive a referral fee on placement.
        </p>
      </header>
      <Card title="Submit a referral">
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(true);
          }}
        >
          <Field label="Their name" value={referralName} onChange={setReferralName} />
          <Field label="Their email" value={referralEmail} onChange={setReferralEmail} type="email" />
          <Field label="Current company" value={referralCompany} onChange={setReferralCompany} />
          <button
            type="submit"
            className="inline-flex items-center rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Send referral
          </button>
          {submitted && (
            <span className="ml-3 text-sm text-success">Submitted (mock — wire POST /v1/referrals).</span>
          )}
        </form>
      </Card>
      <Card title="Your referral history">
        <p className="text-sm text-secondary">No referrals submitted yet.</p>
      </Card>
    </div>
  );
}

function Field({
  label, value, onChange, type = "text",
}: {
  label: string; value: string; onChange: (v: string) => void; type?: string;
}) {
  return (
    <label className="flex flex-col text-sm">
      <span className="mb-1 text-xs uppercase tracking-wide text-secondary">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 max-w-md rounded-md border border-border bg-elevated px-3 text-sm outline-none focus:border-accent"
      />
    </label>
  );
}
