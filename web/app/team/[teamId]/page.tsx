import { LineupRow, ValueRow } from "@/components/PlayerRow";
import { Card, Empty, ErrorPanel, Stat } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { percent, points, record } from "@/lib/format";
import type { MatchupContext, TeamDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function TeamPage({
  params,
}: {
  params: Promise<{ teamId: string }>;
}) {
  const { teamId } = await params;
  const id = Number(teamId);

  let team: TeamDetail;
  let context: MatchupContext | null = null;
  try {
    team = await api.team(id);
    // A team can be on a bye in the playoffs; the roster view still works without it.
    context = await api.optimize(id).catch(() => null);
  } catch (error) {
    const detail = error instanceof ApiError ? error.detail : "Unexpected error.";
    return <ErrorPanel title="Could not load this team" detail={detail} />;
  }

  const lineup = context?.lineup ?? null;

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-100">{team.name}</h1>
        <p className="text-sm text-slate-500">
          {record(team)}
          {team.owners.length > 0 && ` · ${team.owners.join(", ")}`}
          {team.divisionName && ` · ${team.divisionName}`}
        </p>
      </div>

      <Card className="grid grid-cols-2 divide-x divide-edge sm:grid-cols-4">
        <Stat label="Points for" value={points(team.pointsFor)} />
        <Stat label="Points against" value={points(team.pointsAgainst)} />
        <Stat
          label="Standing"
          value={team.standing ? `#${team.standing}` : "—"}
          hint={
            team.streakType && team.streakLength
              ? `${team.streakLength} ${team.streakType.toLowerCase()} streak`
              : undefined
          }
        />
        <Stat
          label="Playoff odds"
          value={team.playoffPct > 0 ? `${team.playoffPct.toFixed(0)}%` : "—"}
        />
      </Card>

      {lineup && context && (
        <Card
          title={`Week ${context.week} lineup`}
          note={
            context.opponent
              ? `vs ${context.opponent.name} · ${percent(context.winProbability)} to win`
              : undefined
          }
        >
          <div className="flex flex-wrap gap-x-8 gap-y-2 border-b border-edge px-5 py-3 text-sm">
            <span className="text-slate-400">
              Starting{" "}
              <span className="font-medium tabular-nums text-slate-100">
                {points(lineup.currentProjected)}
              </span>
            </span>
            <span className="text-slate-400">
              Optimal{" "}
              <span className="font-medium tabular-nums text-slate-100">
                {points(lineup.optimalProjected)}
              </span>
            </span>
            <span className="text-slate-400">
              Left on bench{" "}
              <span
                className={`font-medium tabular-nums ${
                  lineup.pointsLeftOnBench > 0 ? "text-rose-400" : "text-emerald-400"
                }`}
              >
                {points(lineup.pointsLeftOnBench)}
              </span>
            </span>
          </div>
          <ul className="divide-rows">
            {lineup.currentLineup.map((player) => (
              <li key={player.playerId}>
                <LineupRow player={player} />
              </li>
            ))}
          </ul>
          {lineup.bench.length > 0 && (
            <>
              <div className="border-t border-edge px-5 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
                Bench
              </div>
              <ul className="divide-rows opacity-70">
                {lineup.bench.map((player) => (
                  <li key={player.playerId}>
                    <LineupRow player={player} />
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      )}

      <Card title="Roster value" note="Season projection against replacement level">
        {team.valuedRoster.length === 0 ? (
          <Empty>No players on this roster.</Empty>
        ) : (
          <ul className="divide-rows">
            {team.valuedRoster.map((player) => (
              <li key={player.playerId}>
                <ValueRow player={player} />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
