import clsx from "clsx";
import { Pill } from "./pill";

const STAGES = [
  "intake", "sourcing", "screening", "outreach",
  "interview", "submission", "offer", "onboarding",
] as const;

interface Props {
  counts: Partial<Record<(typeof STAGES)[number], number>>;
  current?: (typeof STAGES)[number];
}

export function Pipeline({ counts, current }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-1 rounded-lg border border-border bg-surface p-2">
      {STAGES.map((stage, idx) => (
        <div key={stage} className="flex items-center gap-1">
          <div
            className={clsx(
              "rounded-md border border-border px-3 py-1.5 text-xs",
              current === stage ? "ring-2 ring-accent" : "hover:bg-primary/5",
            )}
          >
            <div className="font-medium capitalize text-primary">{stage}</div>
            <div className="mt-0.5 flex items-center gap-1">
              <Pill tone="stage" stage={stage} size="sm">{counts[stage] ?? 0}</Pill>
            </div>
          </div>
          {idx < STAGES.length - 1 && <span className="text-tertiary">›</span>}
        </div>
      ))}
    </div>
  );
}
