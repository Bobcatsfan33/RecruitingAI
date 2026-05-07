import clsx from "clsx";

interface Props {
  title?: string;
  subtitle?: string;
  className?: string;
  children: React.ReactNode;
}

export function Card({ title, subtitle, className, children }: Props) {
  return (
    <section
      className={clsx(
        "rounded-lg border border-border bg-surface p-5 shadow-elevated",
        className,
      )}
    >
      {title && (
        <header className="mb-3">
          <h2 className="text-base font-semibold tracking-tight">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-secondary">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}
