import type { ReactNode } from "react";

import { confidenceClass } from "@/lib/format";
import type { Confidence } from "@/lib/types";

export function Card({
  title,
  note,
  action,
  children,
  className = "",
}: {
  title?: string;
  note?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || note || action) && (
        <div className="card-header">
          <div className="flex items-baseline gap-3">
            {title && <h2 className="card-title">{title}</h2>}
            {note && <span className="card-note">{note}</span>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "good" | "bad";
}) {
  const toneClass =
    tone === "good" ? "text-emerald-400" : tone === "bad" ? "text-rose-400" : "";
  return (
    <div className="px-5 py-4">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${toneClass}`}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return <span className={`badge ${confidenceClass[confidence]}`}>{confidence}</span>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="px-5 py-8 text-center text-sm text-slate-500">{children}</p>;
}

export function ErrorPanel({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="card border-rose-900/60 bg-rose-950/20 p-5">
      <h2 className="text-sm font-semibold text-rose-200">{title}</h2>
      <p className="mt-1.5 whitespace-pre-wrap text-sm text-rose-300/80">{detail}</p>
    </div>
  );
}
