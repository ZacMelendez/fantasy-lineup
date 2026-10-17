import type { Metadata } from "next";
import Link from "next/link";

import { Nav } from "@/components/Nav";
import { RefreshButton } from "@/components/RefreshButton";

import "./globals.css";

export const metadata: Metadata = {
  title: "Fantasy Lineup",
  description: "Lineup, trade and waiver analysis for an ESPN fantasy football league",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto max-w-6xl px-5 py-6">
          <header className="mb-7 flex flex-wrap items-center justify-between gap-4">
            <Link href="/" className="text-base font-semibold text-slate-100">
              Fantasy Lineup
            </Link>
            <div className="flex items-center gap-3">
              <Nav />
              <RefreshButton />
            </div>
          </header>
          <main className="space-y-6 pb-16">{children}</main>
        </div>
      </body>
    </html>
  );
}
