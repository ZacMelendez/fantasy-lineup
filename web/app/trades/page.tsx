import Link from "next/link";

import { PlayerIdentity } from "@/components/PlayerRow";
import { Card, ConfidenceBadge, Empty, ErrorPanel } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { points, signed } from "@/lib/format";
import type { TradeProposal, Trades, ValuedPlayer } from "@/lib/types";

const FAIRNESS_TONE: Record<TradeProposal["fairness"], string> = {
  even: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  "favors you": "bg-amber-500/15 text-amber-300 ring-amber-500/30",
  "favors them": "bg-sky-500/15 text-sky-300 ring-sky-500/30",
};

export const dynamic = "force-dynamic";

export default async function TradesPage() {
  let trades: Trades;
  try {
    trades = await api.trades(20);
  } catch (error) {
    const detail = error instanceof ApiError ? error.detail : "Unexpected error.";
    return <ErrorPanel title="Could not load trades" detail={detail} />;
  }

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Trades</h1>
        <p className="text-sm text-slate-500">
          Packages that raise both starting lineups, scored in points per week.
          Your baseline lineup is worth {points(trades.baselineLineupValue)}.
        </p>
      </div>

      {trades.proposals.length === 0 ? (
        <Card>
          <Empty>
            No trade improves both teams right now. That usually means your roster is
            already balanced against the rest of the league, or the teams with the
            pieces you need have no surplus at your deep positions.
          </Empty>
        </Card>
      ) : (
        <div className="space-y-4">
          {trades.proposals.map((proposal, index) => (
            <Card key={index}>
              <div className="card-header">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    href={`/team/${proposal.withTeamId}`}
                    className="card-title hover:underline"
                  >
                    {proposal.withTeamName}
                  </Link>
                  <span className={`badge ${FAIRNESS_TONE[proposal.fairness]}`}>
                    {proposal.fairness}
                  </span>
                  <ConfidenceBadge confidence={proposal.confidence} />
                </div>
                <div className="flex items-center gap-4 text-right">
                  <div>
                    <div className="text-sm font-semibold tabular-nums text-emerald-400">
                      {signed(proposal.myGain)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-600">you</div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold tabular-nums text-slate-300">
                      {signed(proposal.theirGain)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-600">them</div>
                  </div>
                </div>
              </div>

              <div className="grid gap-px bg-edge sm:grid-cols-2">
                <PackageColumn label="You send" players={proposal.give} tone="give" />
                <PackageColumn label="You receive" players={proposal.get} tone="get" />
              </div>

              <p className="border-t border-edge px-5 py-3 text-xs leading-relaxed text-slate-400">
                {proposal.reason}
              </p>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

function PackageColumn({
  label,
  players,
  tone,
}: {
  label: string;
  players: ValuedPlayer[];
  tone: "give" | "get";
}) {
  return (
    <div className="bg-panel">
      <div
        className={`px-5 py-1.5 text-[10px] font-semibold uppercase tracking-widest ${
          tone === "give" ? "text-rose-400/70" : "text-emerald-400/70"
        }`}
      >
        {label}
      </div>
      <ul className="divide-rows border-t border-edge/60">
        {players.map((player) => (
          <li key={player.playerId} className="row">
            <div className="flex-1 overflow-hidden">
              <PlayerIdentity player={player} />
            </div>
            <div className="w-16 shrink-0 text-right">
              <div className="text-sm tabular-nums text-slate-300">
                {points(player.seasonProjection)}
              </div>
              <div className="text-[10px] uppercase tracking-wide text-slate-600">proj/g</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
