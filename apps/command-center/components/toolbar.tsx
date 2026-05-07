"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { CommandPalette } from "./command-palette";

export function Toolbar() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [dark, setDark] = useState(true);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const meta = event.metaKey || event.ctrlKey;
      if (meta && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((s) => !s);
      }
      if (meta && event.shiftKey && event.key.toLowerCase() === "l") {
        event.preventDefault();
        setDark((d) => !d);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  return (
    <>
      <header className="vibrancy sticky top-0 z-30 flex h-12 items-center gap-3 border-b px-4">
        <div className="flex items-center gap-2 text-sm font-medium tracking-tight text-secondary">
          <span className="text-primary/80">Talent</span>
          <span className="text-primary/30">›</span>
          <span>Command Center</span>
        </div>
        <button
          type="button"
          onClick={() => setPaletteOpen(true)}
          className={clsx(
            "ml-4 flex h-7 max-w-md flex-1 items-center gap-2 rounded-md border border-border bg-elevated px-3 text-xs text-secondary",
            "transition hover:bg-elevated/80",
          )}
        >
          <span>⌘K</span>
          <span className="opacity-70">Search candidates, reqs, clients…</span>
        </button>
        <div className="ml-auto flex items-center gap-3 text-xs text-secondary">
          <button
            type="button"
            onClick={() => setDark((d) => !d)}
            className="rounded-md px-2 py-1 hover:bg-primary/5"
            title="Toggle dark mode (⌘⇧L)"
          >
            {dark ? "◐ dark" : "◑ light"}
          </button>
          <div className="flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-accent/15 text-[11px] text-accent">
              AW
            </span>
            <span className="hidden sm:inline">Alex Walker</span>
          </div>
        </div>
      </header>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
}
