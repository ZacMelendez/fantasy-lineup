"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

export function RefreshButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setFetching(true);
    setError(null);
    try {
      const response = await fetch("/api/refresh", { method: "POST" });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { error?: string };
        setError(body.error ?? "Refresh failed");
        return;
      }
      startTransition(() => router.refresh());
    } catch {
      setError("Refresh failed");
    } finally {
      setFetching(false);
    }
  };

  const busy = fetching || pending;

  return (
    <div className="flex items-center gap-2">
      {error && <span className="text-xs text-rose-400">{error}</span>}
      <button
        type="button"
        onClick={refresh}
        disabled={busy}
        title="Re-pull rosters and scores from ESPN"
        className="rounded-lg border border-edge px-3 py-1.5 text-sm font-medium text-slate-300 transition-colors hover:bg-panel hover:text-slate-100 disabled:opacity-50"
      >
        {busy ? "Refreshing…" : "Refresh"}
      </button>
    </div>
  );
}
