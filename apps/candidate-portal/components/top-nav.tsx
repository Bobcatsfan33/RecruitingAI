"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const NAV = [
  { label: "Home", href: "/" },
  { label: "Profile", href: "/profile" },
  { label: "Market", href: "/market" },
  { label: "Alerts", href: "/alerts" },
  { label: "Refer", href: "/refer" },
];

export function TopNav() {
  const pathname = usePathname();
  return (
    <header className="vibrancy sticky top-0 z-30 border-b">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
        <Link href="/" className="font-medium tracking-tight">
          Workforce
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href as "/"}
                className={clsx(
                  "rounded-md px-3 py-1.5 transition",
                  active
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-secondary hover:bg-primary/5",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
