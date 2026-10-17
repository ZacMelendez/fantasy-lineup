"""Value over replacement: the shared currency for waiver and trade decisions.

Raw projections make positions incomparable. A 12-point-per-game RB and a 12-point
WR are not worth the same if the best RB you could stream is worth 6 and the best WR
is worth 11. Replacement level is the projection of the best freely available player
at a position, so value is measured against what you could get for nothing.
"""

from typing import Any, Iterable

import serialize

# Positions with no meaningful streaming market get a floor so that a stud is not
# valued at zero just because the waiver wire happens to be thin that week.
_MIN_REPLACEMENT = 0.0


def replacement_levels(free_agents: Iterable[Any]) -> dict[str, float]:
    """Position -> projection of the best available free agent at that position."""
    levels: dict[str, float] = {}
    for player in free_agents:
        position = getattr(player, "position", "") or ""
        if not position:
            continue
        projection = serialize.season_projection(player)
        if projection > levels.get(position, _MIN_REPLACEMENT):
            levels[position] = projection
    return levels


def value_over_replacement(player: Any, levels: dict[str, float]) -> float:
    position = getattr(player, "position", "") or ""
    return serialize.season_projection(player) - levels.get(position, _MIN_REPLACEMENT)


def value_map(players: Iterable[Any], levels: dict[str, float]) -> dict[int, float]:
    return {
        getattr(p, "playerId", None): round(value_over_replacement(p, levels), 2)
        for p in players
    }


def valued_player(player: Any, levels: dict[str, float]) -> dict:
    """Serialized player plus its valuation fields."""
    position = getattr(player, "position", "") or ""
    return {
        **serialize.player_dict(player),
        "replacementLevel": round(levels.get(position, _MIN_REPLACEMENT), 2),
        "valueOverReplacement": round(value_over_replacement(player, levels), 2),
    }


def roster_valuation(roster: Iterable[Any], levels: dict[str, float]) -> list[dict]:
    players = [valued_player(p, levels) for p in roster]
    players.sort(key=lambda p: p["valueOverReplacement"], reverse=True)
    return players
