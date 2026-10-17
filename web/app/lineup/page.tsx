import { LineupRow } from "@/components/PlayerRow";
import { Card, ConfidenceBadge, Empty, ErrorPanel, Stat } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { percent, points, signed } from "@/lib/format";
import type { MatchupContext } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function LineupPage({
  searchParams,
}: {
  searchParams: Promise<{ week?: string }>;
}) {
  const { week } = await searchParams;
  const requestedWeek = week ? Number(week) : undefined;

  let context: MatchupContext;
  try {
    context = await api.optimize(undefined, requestedWeek);
  } catch (error) {
    const detail = error instanceof ApiError ? error.detail : "Unexpected error.";
    return <ErrorPanel title="Could not load your lineup" detail={detail} />;
  }

  const { lineup, opponent } = context;

  if (!lineup) {
    return <Empty>{context.note ?? "No lineup available for this week."}</Empty>;
  }

  // Players in the optimal lineup who are not currently starting, so the optimal
  // column can highlight exactly what changed.
  const startingIds = new Set(context.lineup?.currentLineup.map((p) => p.playerId));
  const optimalIds = new Set(lineup.optimalLineup.map((p) => p.playerId));

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Lineup</h1>
        <p className="text-sm text-slate-500">
          Week {context.week}
          {opponent ? ` vs ${opponent.name}` : ""}
        </p>
      </div>

      <Card className="grid grid-cols-2 divide-x divide-edge sm:grid-cols-4">
        <Stat label="Current" value={points(lineup.currentProjected)} />
        <Stat label="Optimal" value={points(lineup.optimalProjected)} />
        <Stat
          label="Difference"
          value={signed(lineup.optimalProjected - lineup.currentProjected)}
          tone={lineup.pointsLeftOnBench > 0 ? "bad" : "good"}
        />
        <Stat
          label="Win probability"
          value={percent(context.winProbability)}
          hint={
            context.winProbabilityIfOptimal &&
            context.winProbabilityIfOptimal !== context.winProbability
              ? `${percent(context.winProbabilityIfOptimal)} if optimal`
              : undefined
          }
        />
      </Card>

      <Card
        title="Recommended changes"
        note={
          lineup.isOptimal
            ? "None — you are already starting the best available lineup"
            : `${points(lineup.pointsLeftOnBench)} points available`
        }
      >
        {lineup.swaps.length === 0 ? (
          <Empty>Your lineup is already optimal for this week.</Empty>
        ) : (
          <ul className="divide-rows">
            {lineup.swaps.map((swap) => (
              <li key={`${swap.start.playerId}-${swap.sit.playerId}`} className="px-5 py-3.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-slate-100">
                    <span className="font-medium text-emerald-300">{swap.start.name}</span>
                    <span className="text-slate-500"> in for </span>
                    <span className="font-medium text-rose-300">{swap.sit.name}</span>
                  </span>
                  <span className="ml-auto text-sm font-semibold tabular-nums text-emerald-400">
                    {signed(swap.gain)}
                  </span>
                  <ConfidenceBadge confidence={swap.confidence} />
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{swap.reason}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Current lineup" note={`${points(lineup.currentProjected)} projected`}>
          <ul className="divide-rows">
            {lineup.currentLineup.map((player) => (
              <li key={player.playerId}>
                <LineupRow
                  player={player}
                  highlight={optimalIds.has(player.playerId) ? undefined : "remove"}
                />
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Optimal lineup" note={`${points(lineup.optimalProjected)} projected`}>
          <ul className="divide-rows">
            {lineup.optimalLineup.map((player) => (
              <li key={player.playerId}>
                <LineupRow
                  player={player}
                  slot={player.slot}
                  highlight={startingIds.has(player.playerId) ? undefined : "add"}
                />
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Bench" note={`${lineup.bench.length} players`}>
        {lineup.bench.length === 0 ? (
          <Empty>No bench players.</Empty>
        ) : (
          <ul className="divide-rows">
            {lineup.bench.map((player) => (
              <li key={player.playerId}>
                <LineupRow
                  player={player}
                  highlight={optimalIds.has(player.playerId) ? "add" : undefined}
                />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
