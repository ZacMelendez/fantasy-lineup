import Link from "next/link";

import { Card, Empty, ErrorPanel } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { points, record, relativeDate } from "@/lib/format";
import type { Activity, League } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function LeaguePage() {
  let league: League;
  let activity: Activity[] = [];
  try {
    [league, activity] = await Promise.all([api.league(), api.activity(20)]);
  } catch (error) {
    const detail = error instanceof ApiError ? error.detail : "Unexpected error.";
    return <ErrorPanel title="Could not load the league" detail={detail} />;
  }

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-100">League</h1>
        <p className="text-sm text-slate-500">
          {league.year} season · Week {league.currentWeek} · {league.teams.length} teams
        </p>
      </div>

      <Card title="Starting lineup" note="Slots this league requires each week">
        <div className="flex flex-wrap gap-x-6 gap-y-2 px-5 py-4">
          {Object.entries(league.slotCounts).map(([slot, count]) => (
            <div key={slot}>
              <div className="stat-label">{slot}</div>
              <div className="text-sm font-medium tabular-nums text-slate-200">{count}</div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Standings">
          <ul className="divide-rows">
            {league.standings.map((team, index) => (
              <li key={team.teamId} className="row">
                <span className="w-6 shrink-0 text-xs tabular-nums text-slate-600">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/team/${team.teamId}`}
                    className={`truncate text-sm hover:underline ${
                      team.teamId === league.myTeamId
                        ? "font-medium text-sky-300"
                        : "text-slate-200"
                    }`}
                  >
                    {team.name}
                  </Link>
                  {team.divisionName && (
                    <div className="text-[11px] text-slate-600">{team.divisionName}</div>
                  )}
                </div>
                <span className="w-14 shrink-0 text-right text-sm tabular-nums text-slate-300">
                  {record(team)}
                </span>
                <span className="w-16 shrink-0 text-right text-sm tabular-nums text-slate-400">
                  {points(team.pointsFor)}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Power rankings" note="Two-step dominance, scores and margins">
          {league.powerRankings.length === 0 ? (
            <Empty>Power rankings need at least one completed week.</Empty>
          ) : (
            <ul className="divide-rows">
              {league.powerRankings.map((entry, index) => (
                <li key={entry.team.teamId} className="row">
                  <span className="w-6 shrink-0 text-xs tabular-nums text-slate-600">
                    {index + 1}
                  </span>
                  <Link
                    href={`/team/${entry.team.teamId}`}
                    className={`min-w-0 flex-1 truncate text-sm hover:underline ${
                      entry.team.teamId === league.myTeamId
                        ? "font-medium text-sky-300"
                        : "text-slate-200"
                    }`}
                  >
                    {entry.team.name}
                  </Link>
                  <span className="w-14 shrink-0 text-right text-sm tabular-nums text-slate-300">
                    {entry.score.toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Recent activity">
        {activity.length === 0 ? (
          <Empty>No recent transactions.</Empty>
        ) : (
          <ul className="divide-rows">
            {activity.flatMap((entry, entryIndex) =>
              entry.actions.map((action, actionIndex) => (
                <li
                  key={`${entryIndex}-${actionIndex}`}
                  className="flex items-center gap-3 px-5 py-2"
                >
                  <span className="w-14 shrink-0 text-[11px] text-slate-600">
                    {relativeDate(entry.date)}
                  </span>
                  <span className="w-32 shrink-0 truncate text-xs text-slate-400">
                    {action.team ?? "—"}
                  </span>
                  <span className="w-28 shrink-0 text-[11px] font-medium uppercase tracking-wide text-slate-500">
                    {action.action?.toLowerCase() ?? "—"}
                  </span>
                  <span className="flex-1 truncate text-sm text-slate-200">
                    {action.player ?? "—"}
                  </span>
                  {action.bidAmount ? (
                    <span className="text-xs tabular-nums text-slate-500">
                      ${action.bidAmount}
                    </span>
                  ) : null}
                </li>
              )),
            )}
          </ul>
        )}
      </Card>
    </>
  );
}
