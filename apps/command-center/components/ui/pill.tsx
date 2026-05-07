import clsx from "clsx";

type PillTone =
  | "neutral"
  | "info"
  | "success"
  | "warning"
  | "danger"
  | "stage";

interface Props {
  children: React.ReactNode;
  tone?: PillTone;
  stage?: string; // when tone === "stage"
  size?: "sm" | "md";
}

const TONE_CLASSES: Record<PillTone, string> = {
  neutral: "bg-primary/10 text-primary/80",
  info: "bg-accent/15 text-accent",
  success: "bg-success/15 text-success",
  warning: "bg-warning/15 text-warning",
  danger: "bg-danger/15 text-danger",
  stage: "", // computed via inline style on the wrapper
};

export function Pill({ children, tone = "neutral", stage, size = "sm" }: Props) {
  const stageStyle =
    tone === "stage" && stage
      ? {
          backgroundColor: `color-mix(in oklab, var(--stage-${stage}) 18%, transparent)`,
          color: `var(--stage-${stage})`,
        }
      : undefined;
  return (
    <span
      style={stageStyle}
      className={clsx(
        "inline-flex items-center gap-1 rounded-full font-medium tabular-nums",
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs",
        TONE_CLASSES[tone],
      )}
    >
      {children}
    </span>
  );
}
