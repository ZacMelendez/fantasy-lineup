"use client";

import { useState } from "react";

import type { Advice } from "@/lib/types";

import { Card } from "./ui";

/** Renders the model's markdown-ish prose without pulling in a markdown library:
 * paragraphs, bullets and bold are the only things the prompt asks for. */
function Prose({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).filter(Boolean);

  return (
    <div className="space-y-3 text-sm leading-relaxed text-slate-300">
      {blocks.map((block, index) => {
        const lines = block.split("\n");
        const isList = lines.every((line) => /^\s*[-*]\s+/.test(line));

        if (isList) {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5">
              {lines.map((line, i) => (
                <li key={i}>{emphasize(line.replace(/^\s*[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        return <p key={index}>{emphasize(block.replace(/\n/g, " "))}</p>;
      })}
    </div>
  );
}

function emphasize(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={index} className="font-semibold text-slate-100">
        {part.slice(2, -2)}
      </strong>
    ) : (
      part
    ),
  );
}

export function AdvicePanel({ week }: { week: number }) {
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/advice?week=${week}`, { method: "POST" });
      setAdvice((await response.json()) as Advice);
    } catch {
      setAdvice({ enabled: true, narrative: null, detail: "Request failed." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      title="AI read"
      note="Commentary on the numbers above"
      action={
        <button
          type="button"
          onClick={generate}
          disabled={loading}
          className="rounded-lg border border-edge px-3 py-1 text-xs font-medium text-slate-300 transition-colors hover:bg-surface hover:text-slate-100 disabled:opacity-50"
        >
          {loading ? "Thinking…" : advice ? "Regenerate" : "Generate"}
        </button>
      }
    >
      <div className="px-5 py-4">
        {!advice && !loading && (
          <p className="text-sm text-slate-500">
            Ask the model to talk through this week&apos;s close calls.
          </p>
        )}
        {loading && <p className="text-sm text-slate-500">Reading your roster…</p>}
        {advice?.narrative && <Prose text={advice.narrative} />}
        {advice && !advice.narrative && (
          <p className="text-sm text-amber-300/80">
            {advice.detail ?? "No commentary returned."}
          </p>
        )}
      </div>
    </Card>
  );
}
