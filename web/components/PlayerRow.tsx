import { injuryLabel, isSeriousInjury, points } from "@/lib/format";
import type { BoxPlayer, Player, ValuedPlayer } from "@/lib/types";

const POSITION_TONE: Record<string, string> = {
  QB: "text-rose-300",
  RB: "text-emerald-300",
  WR: "text-sky-300",
  TE: "text-amber-300",
  "D/ST": "text-violet-300",
  K: "text-slate-300",
};

export function PositionTag({ position }: { position: string }) {
  return (
    <span className={`text-[11px] font-semibold ${POSITION_TONE[position] ?? "text-slate-400"}`}>
      {position || "—"}
    </span>
  );
}

export function InjuryBadge({ status }: { status: string }) {
  const label = injuryLabel(status);
  if (!label) return null;
  return (
    <span
      className={`badge ${
        isSeriousInjury(status)
          ? "bg-rose-500/15 text-rose-300 ring-rose-500/30"
          : "bg-amber-500/15 text-amber-300 ring-amber-500/30"
      }`}
    >
      {label}
    </span>
  );
}

/** Name, position, pro team and health, used everywhere a player is listed. */
export function PlayerIdentity({
  player,
  showOpponent = false,
}: {
  player: Player | BoxPlayer;
  showOpponent?: boolean;
}) {
  const box = player as BoxPlayer;
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-2">
        <span className="truncate text-sm font-medium text-slate-100">{player.name}</span>
        <InjuryBadge status={player.injuryStatus} />
        {box.onByeWeek && (
          <span className="badge bg-slate-500/15 text-slate-400 ring-slate-500/30">bye</span>
        )}
      </div>
      <div className="mt-0.5 flex items-center gap-2 text-[11px] text-slate-500">
        <PositionTag position={player.position} />
        <span>{player.proTeam}</span>
        {showOpponent && box.proOpponent && box.proOpponent !== "None" && (
          <span>vs {box.proOpponent}</span>
        )}
      </div>
    </div>
  );
}

/** A lineup slot row: slot label, player, projection and actual points. */
export function LineupRow({
  player,
  slot,
  highlight,
}: {
  player: BoxPlayer;
  slot?: string;
  highlight?: "add" | "remove";
}) {
  const tone =
    highlight === "add"
      ? "bg-emerald-500/[0.07]"
      : highlight === "remove"
        ? "bg-rose-500/[0.07]"
        : "";

  return (
    <div className={`row ${tone}`}>
      <span className="w-16 shrink-0 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {slot ?? player.slot}
      </span>
      <div className="flex-1 overflow-hidden">
        <PlayerIdentity player={player} showOpponent />
      </div>
      <div className="w-14 shrink-0 text-right">
        <div className="text-sm tabular-nums text-slate-300">
          {points(player.effectiveProjection)}
        </div>
        <div className="text-[10px] uppercase tracking-wide text-slate-600">proj</div>
      </div>
      <div className="w-14 shrink-0 text-right">
        <div className="text-sm font-medium tabular-nums text-slate-100">
          {player.gamePlayed > 0 || player.points > 0 ? points(player.points) : "—"}
        </div>
        <div className="text-[10px] uppercase tracking-wide text-slate-600">pts</div>
      </div>
    </div>
  );
}

/** A roster row keyed on season-long value rather than a single week. */
export function ValueRow({ player }: { player: ValuedPlayer }) {
  return (
    <div className="row">
      <div className="flex-1 overflow-hidden">
        <PlayerIdentity player={player} />
      </div>
      <div className="w-16 shrink-0 text-right">
        <div className="text-sm tabular-nums text-slate-300">
          {points(player.seasonProjection)}
        </div>
        <div className="text-[10px] uppercase tracking-wide text-slate-600">proj/g</div>
      </div>
      <div className="w-16 shrink-0 text-right">
        <div
          className={`text-sm font-medium tabular-nums ${
            player.valueOverReplacement > 0 ? "text-emerald-400" : "text-slate-500"
          }`}
        >
          {points(player.valueOverReplacement)}
        </div>
        <div className="text-[10px] uppercase tracking-wide text-slate-600">vor</div>
      </div>
    </div>
  );
}
