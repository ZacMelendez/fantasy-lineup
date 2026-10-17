import Link from "next/link";

import { LineupRow } from "@/components/PlayerRow";
import { Card, Empty, ErrorPanel } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { points, record } from "@/lib/format";
import type { Matchup, MatchupSide } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function MatchupsPage({
  searchParams,
}: {
  searchParams: Promise<{ week?: string }>;
}) {
  const { week } = await searchParams;
  const requestedWeek = week ? Number(week) : undefined;

  let data: { week: number; matchups: Matchup[] };
  let myTeamId: number | null = null;
  try {
    const [matchups, league] = await Promise.all([
      api.matchups(requestedWeek),
      api.league(),
    ]);
    data = matchups;
    myTeamId = league.myTeamId;
  } catch (error) {
    const detail = error instanceof ApiError ? error.detail : "Unexpected error.";
    return <ErrorPanel title="Could not load matchups" detail={detail} />;
  }

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Matchups</h1>
          <p className="text-sm text-slate-500">Week {data.week}</p>
        </div>
        <WeekPicker current={data.week} />
      </div>

      {data.matchups.length === 0 ? (
        <Empty>No matchups scheduled for week {data.week}.</Empty>
      ) : (
        data.matchups.map((matchup, index) => (
          <Card
            key={index}
            title={`${matchup.away?.name ?? "Bye"} at ${matchup.home?.name ?? "Bye"}`}
            note={matchup.isPlayoff ? "Playoff" : undefined}
          >
            <div className="grid gap-px bg-edge sm:grid-cols-2">
              <SideColumn side={matchup.away} isMine={matchup.away?.teamId === myTeamId} />
              <SideColumn side={matchup.home} isMine={matchup.home?.teamId === myTeamId} />
            </div>
          </Card>
        ))
      )}
    </>
  );
}

function WeekPicker({ current }: { current: number }) {
  const weeks = Array.from({ length: 18 }, (_, i) => i + 1);
  return (
    <div className="flex flex-wrap gap-1">
      {weeks.map((week) => (
        <Link
          key={week}
          href={`/matchups?week=${week}`}
          className={`rounded px-2 py-1 text-xs tabular-nums transition-colors ${
            week === current
              ? "bg-slate-100 text-slate-900"
              : "text-slate-500 hover:bg-panel hover:text-slate-200"
          }`}
        >
          {week}
        </Link>
      ))}
    </div>
  );
}

function SideColumn({ side, isMine }: { side: MatchupSide | null; isMine: boolean }) {
  if (!side) {
    return (
      <div className="bg-panel px-5 py-6 text-sm text-slate-500">Bye — no opponent</div>
    );
  }

  const starters = side.lineup.filter((p) => p.started);
  const bench = side.lineup.filter((p) => !p.started);

  return (
    <div className="bg-panel">
      <div className="flex items-baseline justify-between px-5 py-3">
        <div>
          <Link
            href={`/team/${side.teamId}`}
            className="text-sm font-medium text-slate-100 hover:underline"
          >
            {side.name}
          </Link>
          <div className="text-xs text-slate-500">
            {record(side)}
            {isMine && <span className="ml-1.5 text-sky-400">your team</span>}
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-semibold tabular-nums text-slate-100">
            {points(side.score)}
          </div>
          <div className="text-[11px] text-slate-500">{points(side.projectedScore)} proj</div>
        </div>
      </div>

      <ul className="divide-rows border-t border-edge/60">
        {starters.map((player) => (
          <li key={player.playerId}>
            <LineupRow player={player} />
          </li>
        ))}
      </ul>

      {bench.length > 0 && (
        <>
          <div className="border-t border-edge px-5 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
            Bench
          </div>
          <ul className="divide-rows opacity-60">
            {bench.map((player) => (
              <li key={player.playerId}>
                <LineupRow player={player} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
