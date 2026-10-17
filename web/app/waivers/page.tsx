import { PlayerIdentity } from "@/components/PlayerRow";
import { Card, ConfidenceBadge, Empty, ErrorPanel } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { points, signed } from "@/lib/format";
import type { Waivers } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function WaiversPage() {
  let waivers: Waivers;
  try {
    waivers = await api.waivers(25);
  } catch (error) {
    const detail = error instanceof ApiError ? error.detail : "Unexpected error.";
    return <ErrorPanel title="Could not load free agents" detail={detail} />;
  }

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Waivers</h1>
        <p className="text-sm text-slate-500">
          Free agents ranked by what they add to your starting lineup, not by raw
          projection. Your baseline lineup is worth {points(waivers.baselineLineupValue)}
          {" "}points per week.
        </p>
      </div>

      <Card title="Replacement level" note="Best freely available player at each position">
        <div className="flex flex-wrap gap-x-6 gap-y-2 px-5 py-4">
          {Object.entries(waivers.replacementLevels).map(([position, value]) => (
            <div key={position}>
              <div className="stat-label">{position}</div>
              <div className="text-sm font-medium tabular-nums text-slate-200">
                {points(value)}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Targets" note={`${waivers.targets.length} worth adding`}>
        {waivers.targets.length === 0 ? (
          <Empty>
            No available free agent would crack your starting lineup. Your roster is
            deeper than the waiver wire at every position.
          </Empty>
        ) : (
          <ul className="divide-rows">
            {waivers.targets.map((target) => (
              <li key={target.playerId} className="px-5 py-3.5">
                <div className="flex items-center gap-3">
                  <div className="flex-1 overflow-hidden">
                    <PlayerIdentity player={target} />
                  </div>
                  <div className="w-16 shrink-0 text-right">
                    <div className="text-sm tabular-nums text-slate-300">
                      {points(target.seasonProjection)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-600">
                      proj/g
                    </div>
                  </div>
                  <div className="w-16 shrink-0 text-right">
                    <div className="text-sm font-semibold tabular-nums text-emerald-400">
                      {signed(target.lineupGain)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wide text-slate-600">
                      lineup
                    </div>
                  </div>
                  <ConfidenceBadge
                    confidence={
                      target.lineupGain >= 4 ? "high" : target.lineupGain >= 1.5 ? "medium" : "low"
                    }
                  />
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
                  {target.dropCandidate && (
                    <span>
                      Drop{" "}
                      <span className="text-rose-300/90">{target.dropCandidate.name}</span>
                      <span className="text-slate-600">
                        {" "}
                        ({target.dropCandidate.position},{" "}
                        {points(target.dropCandidate.seasonProjection)} proj/g)
                      </span>
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-500">{target.reason}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
