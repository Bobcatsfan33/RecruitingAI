import clsx from "clsx";

interface Props {
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
  /** "elevated" gives it the macOS soft window shadow + border. */
  variant?: "elevated" | "flat";
}

export function Card({ title, subtitle, action, className, children, variant = "elevated" }: Props) {
  return (
    <section
      className={clsx(
        "rounded-lg bg-surface text-primary",
        variant === "elevated" ? "shadow-elevated" : "border border-border",
        className,
      )}
    >
      {(title || action) && (
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            {title && <h2 className="text-sm font-medium text-primary">{title}</h2>}
            {subtitle && <p className="text-xs text-secondary">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
