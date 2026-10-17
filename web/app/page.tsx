import Link from "next/link";

import { ActionList } from "@/components/ActionList";
import { AdvicePanel } from "@/components/AdvicePanel";
import { PlayerIdentity } from "@/components/PlayerRow";
import { Card, Empty, ErrorPanel, Stat } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { percent, points, record, signed } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

// Rendered per request. Without this Next prerenders at build time, when the API
// container is not running, and bakes the failure state into the image. Response
// speed comes from the fetch cache and the API's own TTL cache instead.
export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let dashboard: Dashboard;
  try {
    dashboard = await api.dashboard();
  } catch (error) {
    const detail =
      error instanceof ApiError ? error.detail : "Unexpected error loading the league.";
    return <ErrorPanel title="Could not load your league" detail={detail} />;
  }

  const { team, opponent, lineup, winProbability, winProbabilityIfOptimal } = dashboard;

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">{team.name}</h1>
          <p className="text-sm text-slate-500">
            {record(team)} · {points(team.pointsFor)} points for · Week {dashboard.week}
          </p>
        </div>
        {team.standing && (
          <span className="text-sm text-slate-500">
            {team.standing === 1 ? "1st" : `#${team.standing}`} in the league
          </span>
        )}
      </div>

      {dashboard.note && <Empty>{dashboard.note}</Empty>}

      {lineup && (
        <Card className="grid grid-cols-2 divide-x divide-edge sm:grid-cols-4">
          <Stat
            label="Projected"
            value={points(lineup.currentProjected)}
            hint={
              opponent
                ? `${points(opponent.projected)} for ${opponent.abbrev || opponent.name}`
                : undefined
            }
          />
          <Stat
            label="Win probability"
            value={percent(winProbability)}
            tone={(winProbability ?? 0) >= 0.5 ? "good" : "bad"}
            hint={
              winProbabilityIfOptimal && winProbabilityIfOptimal !== winProbability
                ? `${percent(winProbabilityIfOptimal)} if optimal`
                : undefined
            }
          />
          <Stat
            label="On the bench"
            value={points(lineup.pointsLeftOnBench)}
            tone={lineup.pointsLeftOnBench > 0 ? "bad" : "good"}
            hint={lineup.isOptimal ? "Lineup is optimal" : "Points you are giving up"}
          />
          <Stat
            label="Optimal"
            value={points(lineup.optimalProjected)}
            hint={`${signed(lineup.optimalProjected - lineup.currentProjected)} vs current`}
          />
        </Card>
      )}

      <Card
        title="This week's moves"
        note="Highest impact first"
        action={
          <Link href="/lineup" className="text-xs text-slate-400 hover:text-slate-100">
            Full lineup →
          </Link>
        }
      >
        <ActionList actions={dashboard.actions} />
      </Card>

      {opponent && lineup && (
        <Card title="Matchup" note={`Week ${dashboard.week}`}>
          <div className="grid gap-px bg-edge sm:grid-cols-2">
            <MatchupColumn
              name={team.name}
              subtitle={record(team)}
              score={dashboard.score ?? 0}
              projected={lineup.currentProjected}
              players={lineup.currentLineup}
            />
            <MatchupColumn
              name={opponent.name}
              subtitle={record(opponent)}
              score={opponent.score}
              projected={opponent.projected}
              players={opponent.lineup}
            />
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Top waiver targets"
          action={
            <Link href="/waivers" className="text-xs text-slate-400 hover:text-slate-100">
              All →
            </Link>
          }
        >
          {dashboard.topWaivers.length === 0 ? (
            <Empty>No free agent would crack your starting lineup.</Empty>
          ) : (
            <ul className="divide-rows">
              {dashboard.topWaivers.map((target) => (
                <li key={target.playerId} className="row">
                  <div className="flex-1 overflow-hidden">
                    <PlayerIdentity player={target} />
                  </div>
                  <span className="text-sm font-semibold tabular-nums text-emerald-400">
                    {signed(target.lineupGain)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card
          title="Top trade ideas"
          action={
            <Link href="/trades" className="text-xs text-slate-400 hover:text-slate-100">
              All →
            </Link>
          }
        >
          {dashboard.topTrades.length === 0 ? (
            <Empty>No trade improves both sides right now.</Empty>
          ) : (
            <ul className="divide-rows">
              {dashboard.topTrades.map((trade, index) => (
                <li key={index} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs text-slate-500">{trade.withTeamName}</span>
                    <span className="text-sm font-semibold tabular-nums text-emerald-400">
                      {signed(trade.myGain)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-200">
                    <span className="text-rose-300/80">
                      {trade.give.map((p) => p.name).join(", ")}
                    </span>
                    {" → "}
                    <span className="text-emerald-300/90">
                      {trade.get.map((p) => p.name).join(", ")}
                    </span>
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {dashboard.aiEnabled && <AdvicePanel week={dashboard.week} />}
    </>
  );
}

function MatchupColumn({
  name,
  subtitle,
  score,
  projected,
  players,
}: {
  name: string;
  subtitle: string;
  score: number;
  projected: number;
  players: { playerId: number; name: string; slot: string; effectiveProjection: number; points: number }[];
}) {
  return (
    <div className="bg-panel">
      <div className="flex items-baseline justify-between px-5 py-3">
        <div>
          <div className="text-sm font-medium text-slate-100">{name}</div>
          <div className="text-xs text-slate-500">{subtitle}</div>
        </div>
        <div className="text-right">
          <div className="text-lg font-semibold tabular-nums text-slate-100">
            {points(score)}
          </div>
          <div className="text-[11px] text-slate-500">{points(projected)} proj</div>
        </div>
      </div>
      <ul className="divide-rows border-t border-edge/60">
        {players.map((player) => (
          <li key={player.playerId} className="flex items-center gap-3 px-5 py-1.5">
            <span className="w-14 shrink-0 text-[11px] font-semibold uppercase text-slate-600">
              {player.slot}
            </span>
            <span className="flex-1 truncate text-sm text-slate-300">{player.name}</span>
            <span className="w-12 text-right text-xs tabular-nums text-slate-500">
              {points(player.effectiveProjection)}
            </span>
            <span className="w-12 text-right text-sm tabular-nums text-slate-200">
              {points(player.points)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
