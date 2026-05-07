"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

interface PaletteItem {
  type: "candidate" | "requisition" | "client" | "audit" | "page";
  label: string;
  href: string;
  hint?: string;
}

const STATIC: PaletteItem[] = [
  { type: "page", label: "Dashboard", href: "/" },
  { type: "page", label: "Candidates", href: "/candidates" },
  { type: "page", label: "Requisitions", href: "/requisitions" },
  { type: "page", label: "Pipeline", href: "/pipeline" },
  { type: "page", label: "Clients", href: "/clients" },
  { type: "page", label: "Capture intelligence", href: "/capture" },
  { type: "page", label: "Bench management", href: "/bench" },
  { type: "page", label: "Audit log", href: "/audit", hint: "EEOC / OFCCP traceable" },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: Props) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return STATIC;
    return STATIC.filter((i) =>
      [i.label, i.hint ?? "", i.type].some((s) => s.toLowerCase().includes(q)),
    );
  }, [query]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 pt-32 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="vibrancy w-full max-w-xl rounded-lg border shadow-window"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-border px-4 py-3">
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type to search…"
            className="w-full bg-transparent text-sm text-primary outline-none placeholder:text-tertiary"
          />
        </div>
        <ul className="max-h-80 overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <li className="px-4 py-6 text-center text-xs text-secondary">no matches</li>
          ) : (
            filtered.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href as "/"}
                  onClick={onClose}
                  className="flex items-center gap-3 px-4 py-2 text-sm text-primary hover:bg-primary/5"
                >
                  <span className="font-mono text-xs uppercase text-secondary">{item.type}</span>
                  <span className="flex-1">{item.label}</span>
                  {item.hint ? (
                    <span className="text-xs text-tertiary">{item.hint}</span>
                  ) : null}
                </Link>
              </li>
            ))
          )}
        </ul>
        <div className="flex items-center justify-between border-t border-border px-4 py-2 text-xs text-tertiary">
          <span>↑↓ navigate · ↵ open</span>
          <span>esc to close</span>
        </div>
      </div>
    </div>
  );
}
