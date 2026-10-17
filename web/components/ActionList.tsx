import { signed } from "@/lib/format";
import type { ActionItem } from "@/lib/types";

import { ConfidenceBadge, Empty } from "./ui";

const KIND_LABEL: Record<ActionItem["kind"], string> = {
  lineup: "Lineup",
  waiver: "Waiver",
  trade: "Trade",
};

const KIND_TONE: Record<ActionItem["kind"], string> = {
  lineup: "bg-sky-500/15 text-sky-300 ring-sky-500/30",
  waiver: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  trade: "bg-violet-500/15 text-violet-300 ring-violet-500/30",
};

export function ActionList({ actions }: { actions: ActionItem[] }) {
  if (actions.length === 0) {
    return <Empty>Nothing to change. Your lineup is optimal and no clear upgrades are available.</Empty>;
  }

  return (
    <ul className="divide-rows">
      {actions.map((action, index) => (
        <li key={`${action.kind}-${index}`} className="px-5 py-3.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`badge ${KIND_TONE[action.kind]}`}>{KIND_LABEL[action.kind]}</span>
            <span className="flex-1 text-sm font-medium text-slate-100">
              {action.headline}
            </span>
            <span className="text-sm font-semibold tabular-nums text-emerald-400">
              {signed(action.impact)}
            </span>
            <span className="text-[11px] text-slate-500">{action.unit}</span>
            <ConfidenceBadge confidence={action.confidence} />
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{action.detail}</p>
        </li>
      ))}
    </ul>
  );
}
