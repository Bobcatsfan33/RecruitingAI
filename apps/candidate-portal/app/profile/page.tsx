"use client";

import { useState } from "react";
import { Card } from "@/components/card";

export default function ProfilePage() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [metro, setMetro] = useState("");
  const [clearance, setClearance] = useState("none");
  const [motion, setMotion] = useState("enterprise");
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Profile</h1>
        <p className="mt-1 text-sm text-secondary">
          Self-service updates. Fresh profiles surface in matches; stale ones decay over time.
        </p>
      </header>
      <Card title="Identity">
        <form
          className="grid grid-cols-1 gap-4 md:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(true);
          }}
        >
          <Field label="First name" value={firstName} onChange={setFirstName} />
          <Field label="Last name" value={lastName} onChange={setLastName} />
          <Field label="Email" value={email} onChange={setEmail} type="email" />
          <Field label="LinkedIn URL" value={linkedin} onChange={setLinkedin} />
          <Field label="Metro" value={metro} onChange={setMetro} placeholder="DC Metro" />
          <Select
            label="Clearance"
            value={clearance}
            onChange={setClearance}
            options={["none", "public_trust", "secret", "top_secret", "ts_sci"]}
          />
          <Select
            label="Primary sales motion"
            value={motion}
            onChange={setMotion}
            options={["enterprise", "mid_market", "smb_velocity", "plg", "channel"]}
          />
          <div className="md:col-span-2">
            <button
              type="submit"
              className="inline-flex items-center rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              Save profile
            </button>
            {submitted && (
              <span className="ml-3 text-sm text-success">Saved (mock — wire POST /v1/candidates).</span>
            )}
          </div>
        </form>
      </Card>
      <Card title="Why we ask" subtitle="Transparency on data use">
        <ul className="list-disc space-y-1 pl-6 text-sm text-secondary">
          <li>Your profile is matched against open requisitions; signals are never personalised TO you (regulatory invariant).</li>
          <li>Compensation entries are stored only when w2-verified; we don't fabricate.</li>
          <li>Every recruiter action on your record is audit-logged — request a copy any time.</li>
        </ul>
      </Card>
    </div>
  );
}

function Field({
  label, value, onChange, type = "text", placeholder,
}: {
  label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string;
}) {
  return (
    <label className="flex flex-col text-sm">
      <span className="mb-1 text-xs uppercase tracking-wide text-secondary">{label}</span>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-border bg-elevated px-3 text-sm outline-none focus:border-accent"
      />
    </label>
  );
}

function Select({
  label, value, onChange, options,
}: {
  label: string; value: string; onChange: (v: string) => void; options: string[];
}) {
  return (
    <label className="flex flex-col text-sm">
      <span className="mb-1 text-xs uppercase tracking-wide text-secondary">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-border bg-elevated px-3 text-sm outline-none focus:border-accent"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}
