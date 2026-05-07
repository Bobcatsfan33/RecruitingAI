import type { Metadata } from "next";
import "@/styles/globals.css";
import { TopNav } from "@/components/top-nav";

export const metadata: Metadata = {
  title: "Workforce Intelligence — Candidate Portal",
  description: "Your career intelligence cockpit.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen w-full flex-col bg-canvas text-primary">
          <TopNav />
          <main className="flex-1 overflow-auto">
            <div className="mx-auto w-full max-w-5xl px-6 py-8">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
