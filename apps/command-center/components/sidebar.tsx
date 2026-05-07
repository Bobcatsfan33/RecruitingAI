"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

interface NavItem {
  label: string;
  href: string;
  glyph: string; // single emoji used as a placeholder for the SF-style object icon
}

const NAV: NavItem[] = [
  { label: "Dashboard", href: "/", glyph: "◆" },
  { label: "Candidates", href: "/candidates", glyph: "◐" },
  { label: "Requisitions", href: "/requisitions", glyph: "◇" },
  { label: "Pipeline", href: "/pipeline", glyph: "≡" },
  { label: "Clients", href: "/clients", glyph: "◑" },
  { label: "Capture", href: "/capture", glyph: "◓" },
  { label: "Bench", href: "/bench", glyph: "◔" },
  { label: "Audit", href: "/audit", glyph: "❍" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="vibrancy hidden w-64 shrink-0 flex-col border-r md:flex">
      <div className="flex h-12 items-center px-4 text-sm">
        {/* SF-style "app launcher" waffle + macOS-style traffic-light vibe */}
        <div className="flex items-center gap-3">
          <span className="grid h-6 w-6 grid-cols-3 grid-rows-3 gap-[2px] opacity-80">
            {Array.from({ length: 9 }).map((_, i) => (
              <span key={i} className="rounded-[1px] bg-primary/70" />
            ))}
          </span>
          <span className="font-medium tracking-tight text-primary">
            Workforce
          </span>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 p-2">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition",
                "hover:bg-primary/5",
                active && "bg-primary/10 font-medium",
              )}
            >
              <span className="font-mono text-primary/60 group-hover:text-primary">
                {item.glyph}
              </span>
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="px-3 py-3 text-xs text-secondary">
        <div className="mb-1">v0.1 — internal preview</div>
        <div className="opacity-70">⌘K opens the command palette</div>
      </div>
    </aside>
  );
}
