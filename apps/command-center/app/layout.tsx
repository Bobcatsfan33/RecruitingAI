import type { Metadata } from "next";
import "@/styles/globals.css";
import { Sidebar } from "@/components/sidebar";
import { Toolbar } from "@/components/toolbar";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "Workforce Intelligence — Talent Command Center",
  description: "AI-native recruiting operating system.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>
          <div className="flex min-h-screen w-full bg-canvas text-primary">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <Toolbar />
              <main className="flex-1 overflow-auto">
                <div className="mx-auto w-full max-w-[1400px] px-8 py-6">
                  {children}
                </div>
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
