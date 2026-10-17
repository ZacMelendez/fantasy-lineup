"""Trade search.

Every package is scored by how much it changes each side's *optimal starting lineup*,
not by comparing raw player value. That difference matters: giving up your third
receiver for a starting running back can be a clear win even when the receiver
projects higher, because the receiver was never going to start.

Only trades where both sides improve are kept, which is also the only kind worth
proposing.
"""

from itertools import combinations
from typing import Any, Sequence

import serialize
from engine import value as value_engine
from engine.lineup import LineupSolver, confidence_for

# Enumerating every 2-for-2 across a full league is millions of solves. Restricting
# each side's package candidates to its most valuable tradeable players keeps the
# search under a second while still surfacing the trades anyone would actually make.
MAX_PACKAGE_CANDIDATES = 9

# Positions nobody trades in a standard league.
UNTRADEABLE_POSITIONS = {"K", "D/ST"}

# Ignore rounding-level noise; both sides must gain at least this much per week.
MIN_GAIN = 0.4


def find_trades(
    my_team: Any,
    other_teams: Sequence[Any],
    free_agents: Sequence[Any],
    slot_counts: dict[str, int],
    limit: int = 12,
    max_package_size: int = 2,
) -> dict:
    levels = value_engine.replacement_levels(free_agents)
    solver = LineupSolver(slot_counts)

    my_roster = list(getattr(my_team, "roster", []))
    my_baseline = _total(solver, my_roster)
    my_candidates = _package_candidates(my_roster, levels)

    proposals: list[dict] = []
    for other in other_teams:
        their_roster = list(getattr(other, "roster", []))
        if not their_roster:
            continue

        their_baseline = _total(solver, their_roster)
        their_candidates = _package_candidates(their_roster, levels)

        for size in range(1, max_package_size + 1):
            for give in combinations(my_candidates, size):
                for get in combinations(their_candidates, size):
                    my_gain = (
                        _total(solver, _swap(my_roster, give, get)) - my_baseline
                    )
                    if my_gain < MIN_GAIN:
                        continue

                    their_gain = (
                        _total(solver, _swap(their_roster, get, give)) - their_baseline
                    )
                    if their_gain < MIN_GAIN:
                        continue

                    proposals.append(
                        _proposal(other, give, get, my_gain, their_gain, levels)
                    )

    proposals.sort(key=lambda p: p["myGain"], reverse=True)
    return {
        "baselineLineupValue": round(my_baseline, 2),
        "candidatesConsidered": len(my_candidates),
        "proposals": _diversify(_dedupe(proposals))[:limit],
    }


def _total(solver: LineupSolver, players: Sequence[Any]) -> float:
    return solver.total(players, [serialize.season_projection(p) for p in players])


def _swap(roster: Sequence[Any], out: Sequence[Any], incoming: Sequence[Any]) -> list[Any]:
    out_ids = {getattr(p, "playerId", None) for p in out}
    return [p for p in roster if getattr(p, "playerId", None) not in out_ids] + list(incoming)


def _package_candidates(roster: Sequence[Any], levels: dict[str, float]) -> list[Any]:
    tradeable = [
        p
        for p in roster
        if (getattr(p, "position", "") or "") not in UNTRADEABLE_POSITIONS
        and not serialize.is_out(p)
    ]
    tradeable.sort(key=lambda p: value_engine.value_over_replacement(p, levels), reverse=True)
    return tradeable[:MAX_PACKAGE_CANDIDATES]


def _proposal(
    other: Any,
    give: Sequence[Any],
    get: Sequence[Any],
    my_gain: float,
    their_gain: float,
    levels: dict[str, float],
) -> dict:
    return {
        "withTeamId": other.team_id,
        "withTeamName": getattr(other, "team_name", "Unknown"),
        "give": [value_engine.valued_player(p, levels) for p in give],
        "get": [value_engine.valued_player(p, levels) for p in get],
        "myGain": round(my_gain, 2),
        "theirGain": round(their_gain, 2),
        "fairness": _fairness(my_gain, their_gain),
        "confidence": confidence_for(min(my_gain, their_gain)),
        "reason": _trade_reason(other, give, get, my_gain, their_gain),
    }


def _fairness(my_gain: float, their_gain: float) -> str:
    """How the deal reads to the other manager, which drives whether they accept."""
    total = my_gain + their_gain
    if total <= 0:
        return "even"
    share = my_gain / total
    if share > 0.65:
        return "favors you"
    if share < 0.35:
        return "favors them"
    return "even"


def _trade_reason(
    other: Any, give: Sequence[Any], get: Sequence[Any], my_gain: float, their_gain: float
) -> str:
    give_names = ", ".join(getattr(p, "name", "?") for p in give)
    get_names = ", ".join(getattr(p, "name", "?") for p in get)
    team_name = getattr(other, "team_name", "the other team")

    positions_out = {getattr(p, "position", "") for p in give}
    positions_in = {getattr(p, "position", "") for p in get}
    shift = positions_in - positions_out

    parts = [
        f"Sending {give_names} for {get_names} adds {my_gain:.1f} points per week to "
        f"your starting lineup and {their_gain:.1f} to {team_name}'s, so both sides "
        f"have a reason to say yes."
    ]
    if shift:
        parts.append(
            f"It converts bench depth into a starting {'/'.join(sorted(p for p in shift if p))}."
        )
    return " ".join(parts)


# How many proposals to keep per opposing team before ranking globally.
PER_TEAM_LIMIT = 3


def _diversify(proposals: list[dict]) -> list[dict]:
    """Spread the results across teams and package sizes.

    Ranking purely by your own gain fills the whole list with near-identical
    two-for-two blockbusters against whichever single team happens to match up best,
    all of them lopsided enough that the other manager would decline. Keeping the best
    deal of each package size per team leaves you with a shortlist you can actually
    send.

    Assumes `proposals` is already sorted by descending gain.
    """
    kept: list[dict] = []
    by_team: dict[Any, list[dict]] = {}
    for proposal in proposals:
        by_team.setdefault(proposal["withTeamId"], []).append(proposal)

    for team_proposals in by_team.values():
        chosen: list[dict] = []
        seen_sizes: set[int] = set()

        # Best deal at each package size first, so a clean one-for-one is never
        # crowded out by variations on a larger package.
        for proposal in team_proposals:
            size = len(proposal["give"])
            if size not in seen_sizes:
                seen_sizes.add(size)
                chosen.append(proposal)

        for proposal in team_proposals:
            if len(chosen) >= PER_TEAM_LIMIT:
                break
            if proposal not in chosen:
                chosen.append(proposal)

        kept.extend(chosen[:PER_TEAM_LIMIT])

    kept.sort(key=lambda p: p["myGain"], reverse=True)
    return kept


def _dedupe(proposals: list[dict]) -> list[dict]:
    """Collapse packages that move the same players, keeping the best-scoring one."""
    seen: set[tuple] = set()
    unique = []
    for proposal in proposals:
        key = (
            proposal["withTeamId"],
            tuple(sorted(p["playerId"] for p in proposal["give"])),
            tuple(sorted(p["playerId"] for p in proposal["get"])),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(proposal)
    return unique
