"""Optimal lineup assignment and matchup win probability."""

import math
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

import serialize

# Week-to-week scoring noise for a full fantasy lineup, used only for the win
# probability curve.
WEEKLY_STDEV = 26.0

# Weight given to pairings the solver was forced to make when a league has more
# starting slots than playable players. Filtered out of the result.
_INELIGIBLE = -1e6

_SLOT_ORDER = [
    "QB", "TQB", "RB", "RB/WR", "WR", "WR/TE", "TE", "RB/WR/TE", "OP",
    "D/ST", "K", "P", "HC", "DP", "DL", "LB", "DB", "CB", "S", "DT", "DE",
]


@dataclass
class Assignment:
    slot: str
    player: Any
    value: float


def expand_slots(slot_counts: dict[str, int]) -> list[str]:
    """{'QB': 1, 'RB': 2} -> ['QB', 'RB', 'RB']"""
    slots: list[str] = []
    for slot, count in slot_counts.items():
        slots.extend([slot] * int(count))
    return slots


def slot_order(slot: str) -> int:
    try:
        return _SLOT_ORDER.index(slot)
    except ValueError:
        return len(_SLOT_ORDER)


class LineupSolver:
    """Maximum-value legal starting lineup for a league's slot configuration.

    Modelled as a rectangular assignment problem: rows are players, columns are
    individual starting slots, and cell weight is the player's value in that slot (or
    a large penalty when they are not eligible for it). The Hungarian algorithm gives
    the exact optimum, which greedy slot-filling does not once flex slots and
    multi-position eligibility interact.

    The trade search runs thousands of solves over overlapping rosters, so per-player
    eligibility rows are built once and cached.
    """

    def __init__(self, slot_counts: dict[str, int]):
        self.slots = expand_slots(slot_counts)
        self._masks: dict[Any, np.ndarray] = {}

    def _mask(self, player: Any) -> np.ndarray:
        # Keyed on playerId so the cache survives across the Player and BoxPlayer
        # representations of the same person, which share eligibility.
        key = getattr(player, "playerId", None) or id(player)
        cached = self._masks.get(key)
        if cached is None:
            eligible = set(getattr(player, "eligibleSlots", []) or [])
            cached = np.array([slot in eligible for slot in self.slots], dtype=bool)
            self._masks[key] = cached
        return cached

    def _matrix(self, players: Sequence[Any], values: Sequence[float]) -> np.ndarray:
        masks = np.stack([self._mask(p) for p in players])
        column = np.asarray(values, dtype=float)[:, None]
        return np.where(masks, column, _INELIGIBLE)

    def solve(self, players: Sequence[Any], values: Sequence[float]) -> tuple[list[Assignment], float]:
        players = list(players)
        if not players or not self.slots:
            return [], 0.0

        matrix = self._matrix(players, values)
        rows, cols = linear_sum_assignment(matrix, maximize=True)

        assignments = [
            Assignment(slot=self.slots[j], player=players[i], value=float(matrix[i, j]))
            for i, j in zip(rows, cols)
            if matrix[i, j] > _INELIGIBLE
        ]
        assignments.sort(key=lambda a: (slot_order(a.slot), -a.value))
        return assignments, sum(a.value for a in assignments)

    def total(self, players: Sequence[Any], values: Sequence[float]) -> float:
        players = list(players)
        if not players or not self.slots:
            return 0.0
        matrix = self._matrix(players, values)
        rows, cols = linear_sum_assignment(matrix, maximize=True)
        picked = matrix[rows, cols]
        return float(picked[picked > _INELIGIBLE].sum())


def optimal_lineup(
    players: Iterable[Any],
    slot_counts: dict[str, int],
    value_fn: Callable[[Any], float],
) -> tuple[list[Assignment], float]:
    players = list(players)
    solver = LineupSolver(slot_counts)
    return solver.solve(players, [value_fn(p) for p in players])


def lineup_analysis(lineup: list[Any], slot_counts: dict[str, int]) -> dict:
    """Compare a team's actual weekly lineup against its optimum.

    `lineup` is the BoxPlayer list from `league.box_scores()`, which carries both the
    slot ESPN has the player in and their projection for that week.
    """
    value_fn = serialize.week_projection

    current = [p for p in lineup if _slot_of(p) not in serialize.BENCH_SLOTS]
    current_total = sum(value_fn(p) for p in current)

    assignments, optimal_points = optimal_lineup(lineup, slot_counts, value_fn)
    optimal_ids = {getattr(a.player, "playerId", None) for a in assignments}
    current_ids = {getattr(p, "playerId", None) for p in current}

    bench_up = [p for p in lineup if getattr(p, "playerId", None) in optimal_ids - current_ids]
    sit_down = [p for p in current if getattr(p, "playerId", None) in current_ids - optimal_ids]

    return {
        "currentProjected": round(current_total, 2),
        "optimalProjected": round(optimal_points, 2),
        "pointsLeftOnBench": round(max(0.0, optimal_points - current_total), 2),
        "isOptimal": not bench_up and not sit_down,
        "optimalLineup": [
            {**serialize.box_player_dict(a.player), "slot": a.slot, "slotProjection": round(a.value, 2)}
            for a in assignments
        ],
        "currentLineup": [
            serialize.box_player_dict(p)
            for p in sorted(current, key=lambda x: slot_order(_slot_of(x)))
        ],
        "bench": [
            serialize.box_player_dict(p) for p in lineup if _slot_of(p) in serialize.BENCH_SLOTS
        ],
        "swaps": _build_swaps(bench_up, sit_down, value_fn),
    }


def _slot_of(player: Any) -> str:
    return getattr(player, "slot_position", "BE") or "BE"


def _build_swaps(
    bench_up: list[Any], sit_down: list[Any], value_fn: Callable[[Any], float]
) -> list[dict]:
    """Pair each promotion with a demotion, best gain first.

    The optimizer works on the whole lineup at once, so a strict one-to-one mapping
    does not always exist (three players can rotate through two slots). Pairing the
    highest projected addition with the lowest projected removal still names the
    actionable move in those cases.
    """
    starts = sorted(bench_up, key=value_fn, reverse=True)
    sits = sorted(sit_down, key=value_fn)

    swaps = []
    for start, sit in zip(starts, sits):
        gain = value_fn(start) - value_fn(sit)
        swaps.append(
            {
                "start": serialize.box_player_dict(start),
                "sit": serialize.box_player_dict(sit),
                "gain": round(gain, 2),
                "confidence": confidence_for(gain),
                "reason": _swap_reason(start, sit, gain),
            }
        )
    swaps.sort(key=lambda s: s["gain"], reverse=True)
    return swaps


def confidence_for(gain: float) -> str:
    if gain >= 4.0:
        return "high"
    if gain >= 1.5:
        return "medium"
    return "low"


def _swap_reason(start: Any, sit: Any, gain: float) -> str:
    start_name = getattr(start, "name", "Player")
    sit_name = getattr(sit, "name", "Player")
    parts = [
        f"{start_name} projects for {serialize.week_projection(start):.1f} against "
        f"{serialize.week_projection(sit):.1f} from {sit_name}, a gain of {gain:.1f}."
    ]

    if serialize.is_out(sit):
        parts.append(f"{sit_name} is listed {serialize.injury_status(sit).lower()}.")
    elif getattr(sit, "on_bye_week", False):
        parts.append(f"{sit_name} is on bye.")

    rank = getattr(start, "pro_pos_rank", 0) or 0
    opponent = getattr(start, "pro_opponent", None)
    if rank and opponent and opponent != "None":
        parts.append(f"{start_name} draws {opponent}, ranked {ordinal(rank)} against the position.")

    if serialize.injury_status(start) in serialize.QUESTIONABLE_STATUSES:
        parts.append(f"Note that {start_name} is {serialize.injury_status(start).lower()}.")
    return " ".join(parts)


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def win_probability(my_projection: float, opponent_projection: float) -> float:
    """P(my score > opponent score), treating the margin as normally distributed.

    Two independent lineups each carrying WEEKLY_STDEV of noise give the margin a
    standard deviation of sqrt(2) * WEEKLY_STDEV.
    """
    margin_stdev = WEEKLY_STDEV * math.sqrt(2)
    z = (my_projection - opponent_projection) / margin_stdev
    return round(0.5 * (1.0 + math.erf(z / math.sqrt(2))), 4)
