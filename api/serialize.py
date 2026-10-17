"""espn_api objects -> plain JSON-safe dicts.

Attributes are read with getattr defaults throughout: espn_api populates fields
conditionally depending on what ESPN returned for a given player or season, so a
missing attribute is normal rather than exceptional.
"""

from typing import Any

OUT_STATUSES = {"OUT", "INJURY_RESERVE", "SUSPENSION", "NOT_ACTIVE"}
QUESTIONABLE_STATUSES = {"QUESTIONABLE", "DOUBTFUL"}

BENCH_SLOTS = {"BE", "IR"}


def num(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if result == result else default  # filter NaN


def injury_status(player: Any) -> str:
    status = getattr(player, "injuryStatus", None) or "ACTIVE"
    return str(status).upper()


def is_out(player: Any) -> bool:
    return injury_status(player) in OUT_STATUSES


def season_projection(player: Any) -> float:
    """Per-game projection used for roster-level (week-agnostic) valuation.

    ESPN's season projected average is the best available signal; players with no
    projection yet fall back to their actual scoring average.
    """
    projected = num(getattr(player, "projected_avg_points", 0))
    if projected > 0:
        return projected
    return num(getattr(player, "avg_points", 0))


def week_projection(player: Any) -> float:
    """This-week projection for a BoxPlayer, zeroed for players who cannot play."""
    if is_out(player) or getattr(player, "on_bye_week", False):
        return 0.0
    return num(getattr(player, "projected_points", 0))


def player_dict(player: Any) -> dict:
    return {
        "playerId": getattr(player, "playerId", None),
        "name": getattr(player, "name", "Unknown"),
        "position": getattr(player, "position", "") or "",
        "proTeam": getattr(player, "proTeam", "") or "",
        "eligibleSlots": [s for s in (getattr(player, "eligibleSlots", []) or []) if s],
        "lineupSlot": getattr(player, "lineupSlot", "") or "",
        "injuryStatus": injury_status(player),
        "injured": bool(getattr(player, "injured", False)),
        "positionRank": getattr(player, "posRank", None),
        "percentOwned": num(getattr(player, "percent_owned", 0)),
        "percentStarted": num(getattr(player, "percent_started", 0)),
        "totalPoints": round(num(getattr(player, "total_points", 0)), 2),
        "avgPoints": round(num(getattr(player, "avg_points", 0)), 2),
        "projectedAvgPoints": round(num(getattr(player, "projected_avg_points", 0)), 2),
        "projectedTotalPoints": round(num(getattr(player, "projected_total_points", 0)), 2),
        "seasonProjection": round(season_projection(player), 2),
    }


def box_player_dict(player: Any) -> dict:
    """A roster entry inside a weekly matchup, with the week-specific extras."""
    data = player_dict(player)
    data.update(
        {
            "slot": getattr(player, "slot_position", "BE") or "BE",
            "started": (getattr(player, "slot_position", "BE") or "BE") not in BENCH_SLOTS,
            "points": round(num(getattr(player, "points", 0)), 2),
            "projectedPoints": round(num(getattr(player, "projected_points", 0)), 2),
            "effectiveProjection": round(week_projection(player), 2),
            "proOpponent": getattr(player, "pro_opponent", None),
            "proPositionRank": getattr(player, "pro_pos_rank", None),
            "onByeWeek": bool(getattr(player, "on_bye_week", False)),
            "gamePlayed": num(getattr(player, "game_played", 0)),
        }
    )
    return data


def team_summary(team: Any) -> dict:
    return {
        "teamId": team.team_id,
        "name": getattr(team, "team_name", "Unknown"),
        "abbrev": getattr(team, "team_abbrev", ""),
        "logo": getattr(team, "logo_url", "") or None,
        "owners": _owner_names(team),
        "wins": getattr(team, "wins", 0),
        "losses": getattr(team, "losses", 0),
        "ties": getattr(team, "ties", 0),
        "pointsFor": round(num(getattr(team, "points_for", 0)), 2),
        "pointsAgainst": round(num(getattr(team, "points_against", 0)), 2),
        "standing": getattr(team, "standing", None),
        "divisionName": getattr(team, "division_name", "") or None,
        "streakType": getattr(team, "streak_type", None),
        "streakLength": getattr(team, "streak_length", 0),
        "playoffPct": round(num(getattr(team, "playoff_pct", 0)), 1),
    }


def team_detail(team: Any) -> dict:
    data = team_summary(team)
    data["roster"] = [player_dict(p) for p in getattr(team, "roster", [])]
    return data


def _owner_names(team: Any) -> list[str]:
    names = []
    for owner in getattr(team, "owners", []) or []:
        if isinstance(owner, dict):
            full = " ".join(
                part for part in [owner.get("firstName"), owner.get("lastName")] if part
            ).strip()
            names.append(full or owner.get("displayName") or "Unknown")
        elif owner:
            names.append(str(owner))
    return names


def matchup_dict(box: Any, week: int) -> dict:
    return {
        "week": week,
        "isPlayoff": bool(getattr(box, "is_playoff", False)),
        "matchupType": getattr(box, "matchup_type", "NONE"),
        "home": _matchup_side(box.home_team, box.home_score, box.home_projected, box.home_lineup),
        "away": _matchup_side(box.away_team, box.away_score, box.away_projected, box.away_lineup),
    }


def _matchup_side(team: Any, score: Any, projected: Any, lineup: Any) -> dict | None:
    if team is None:
        return None
    # Before box_scores resolves them, these can still be raw team ids.
    if not hasattr(team, "team_id"):
        return {"teamId": team, "name": f"Team {team}", "score": num(score), "lineup": []}

    return {
        **team_summary(team),
        "score": round(num(score), 2),
        "projectedScore": round(num(projected), 2),
        "lineup": [box_player_dict(p) for p in (lineup or [])],
    }


def activity_dict(activity: Any) -> dict:
    actions = []
    for action in getattr(activity, "actions", []) or []:
        team, action_type, player, bid = (list(action) + [None] * 4)[:4]
        actions.append(
            {
                "team": getattr(team, "team_name", None) if team else None,
                "teamId": getattr(team, "team_id", None) if team else None,
                "action": action_type,
                "player": getattr(player, "name", None) if hasattr(player, "name") else player,
                "bidAmount": bid,
            }
        )
    return {"date": getattr(activity, "date", None), "actions": actions}
