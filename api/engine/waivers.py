"""Free agent targets, scored by what they actually add to your starting lineup."""

from typing import Any, Sequence

import serialize
from engine import value as value_engine
from engine.lineup import LineupSolver


def waiver_targets(
    roster: Sequence[Any],
    free_agents: Sequence[Any],
    slot_counts: dict[str, int],
    limit: int = 15,
) -> dict:
    """Rank free agents by the gain in optimal starting lineup value from adding them.

    Scoring by lineup delta rather than by raw projection is what keeps this honest:
    a strong bench player at a position you are already deep at scores near zero,
    because they would not crack the lineup.
    """
    levels = value_engine.replacement_levels(free_agents)
    solver = LineupSolver(slot_counts)

    roster = list(roster)
    baseline_players = roster
    baseline = solver.total(baseline_players, [serialize.season_projection(p) for p in roster])

    targets = []
    for candidate in free_agents:
        if serialize.is_out(candidate):
            continue

        trial = roster + [candidate]
        trial_values = [serialize.season_projection(p) for p in trial]
        assignments, total = solver.solve(trial, trial_values)
        gain = total - baseline
        if gain <= 0.01:
            continue

        starters = {getattr(a.player, "playerId", None) for a in assignments}
        targets.append(
            {
                **value_engine.valued_player(candidate, levels),
                "lineupGain": round(gain, 2),
                "dropCandidate": _drop_candidate(roster, starters, levels),
                "reason": _target_reason(candidate, gain, levels),
            }
        )

    targets.sort(key=lambda t: t["lineupGain"], reverse=True)
    return {
        "replacementLevels": {k: round(v, 2) for k, v in sorted(levels.items())},
        "baselineLineupValue": round(baseline, 2),
        "targets": targets[:limit],
    }


def _drop_candidate(
    roster: Sequence[Any], starters: set, levels: dict[str, float]
) -> dict | None:
    """Least valuable rostered player who would not start once the add is made.

    Ranked on raw projection rather than value over replacement. VOR is the right
    currency for deciding who to *acquire*, but it misleads here: replacement level is
    set by the best available free agent, which is often the very player being added,
    and that inflated baseline can make a useful bench player look worse than a
    genuinely worthless one. Among players who do not crack the lineup either way,
    expected points is the honest measure of what you lose by cutting them.
    """
    benched = [p for p in roster if getattr(p, "playerId", None) not in starters]
    if not benched:
        return None

    # Prefer dropping someone already ruled out over a healthy body.
    worst = min(
        benched,
        key=lambda p: (not serialize.is_out(p), serialize.season_projection(p)),
    )
    return value_engine.valued_player(worst, levels)


def _target_reason(candidate: Any, gain: float, levels: dict[str, float]) -> str:
    name = getattr(candidate, "name", "Player")
    position = getattr(candidate, "position", "") or "player"
    owned = serialize.player_dict(candidate)["percentOwned"]

    parts = [
        f"Adding {name} raises your optimal lineup by {gain:.1f} points per week, "
        f"{value_engine.value_over_replacement(candidate, levels):.1f} above the best "
        f"{position} otherwise available."
    ]
    if owned > 0:
        parts.append(f"Rostered in {owned:.0f}% of ESPN leagues.")
    if serialize.injury_status(candidate) in serialize.QUESTIONABLE_STATUSES:
        parts.append(f"Listed {serialize.injury_status(candidate).lower()}.")
    return " ".join(parts)
