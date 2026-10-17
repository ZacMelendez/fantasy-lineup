"""Thin, cached wrapper around the espn_api football League.

Every ESPN request goes through here. The library is not thread-safe and each call
costs a second or more, so all access is serialized behind one lock and memoized with
a TTL. FastAPI runs our sync endpoints in a threadpool, which is why the lock matters.
"""

import threading
import time
from typing import Any, Callable

from espn_api.football import League
from espn_api.requests.espn_requests import ESPNAccessDenied, ESPNInvalidLeague

from config import Config, load_config


class LeagueUnavailable(Exception):
    """ESPN refused the league, with a message worth showing the user verbatim."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status

_lock = threading.RLock()
_config: Config | None = None
_league: League | None = None
_league_loaded_at: float = 0.0
_memo: dict[tuple, tuple[float, Any]] = {}


def config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def _fresh(loaded_at: float) -> bool:
    return (time.monotonic() - loaded_at) < config().cache_ttl


def league() -> League:
    """Return the shared League, (re)fetching it when the cache has gone stale."""
    global _league, _league_loaded_at

    with _lock:
        cfg = config()
        if _league is not None and _fresh(_league_loaded_at):
            return _league

        if _league is None:
            _league = _connect(cfg)
        else:
            # Cheaper than constructing a new League: re-pulls teams, scores and rosters
            # without re-downloading the full player universe.
            _league.refresh()

        _league_loaded_at = time.monotonic()
        return _league


def _connect(cfg: Config) -> League:
    """First contact with ESPN, where bad configuration shows up.

    espn_api's own errors are terse ("espn_s2 and swid are required"), and getting
    the cookies is the step people get wrong, so they are translated into something
    that says what to do about it.
    """
    try:
        return League(
            league_id=cfg.league_id,
            year=cfg.year,
            espn_s2=cfg.espn_s2,
            swid=cfg.swid,
        )
    except ESPNAccessDenied as exc:
        if not (cfg.espn_s2 and cfg.swid):
            raise LeagueUnavailable(
                f"League {cfg.league_id} is private, so ESPN_S2 and ESPN_SWID must be "
                "set in .env. Log in to fantasy.espn.com, open your browser devtools, "
                "and copy the espn_s2 and SWID cookies (SWID includes the curly "
                "braces). See the README for the walkthrough.",
                status=401,
            ) from exc
        raise LeagueUnavailable(
            f"ESPN rejected the stored credentials for league {cfg.league_id}. The "
            "espn_s2 cookie expires periodically; copy a fresh pair from your browser "
            "and restart the api container.",
            status=401,
        ) from exc
    except ESPNInvalidLeague as exc:
        raise LeagueUnavailable(
            f"ESPN has no league {cfg.league_id} for {cfg.year}. Check ESPN_LEAGUE_ID "
            "and ESPN_YEAR against your league URL.",
            status=404,
        ) from exc


def refresh() -> None:
    """Drop every cache so the next read hits ESPN."""
    global _league_loaded_at
    with _lock:
        _memo.clear()
        _league_loaded_at = 0.0
    league()


def cached(key: tuple, producer: Callable[[], Any]) -> Any:
    with _lock:
        entry = _memo.get(key)
        if entry is not None and _fresh(entry[0]):
            return entry[1]

        value = producer()
        _memo[key] = (time.monotonic(), value)
        return value


def current_week() -> int:
    lg = league()
    # current_week is the scoring period; nfl_week can run ahead of it in the offseason.
    return max(1, int(getattr(lg, "current_week", 1) or 1))


def box_scores(week: int | None = None) -> list:
    week = week or current_week()
    return cached(("box_scores", week), lambda: league().box_scores(week))


def free_agents(week: int | None = None, size: int = 100, position: str | None = None) -> list:
    week = week or current_week()
    return cached(
        ("free_agents", week, size, position),
        lambda: league().free_agents(week=week, size=size, position=position),
    )


def teams() -> list:
    return league().teams


def team_by_id(team_id: int):
    for team in teams():
        if team.team_id == team_id:
            return team
    return None


def my_team():
    return team_by_id(config().team_id)


def starting_slot_counts() -> dict[str, int]:
    """League starting lineup requirements, e.g. {'QB': 1, 'RB': 2, 'RB/WR/TE': 1}.

    espn_api exposes every lineup slot in `position_slot_counts`, including bench and
    IR and slots the league does not use (count 0). Only real starting slots matter to
    the optimizer.
    """
    counts = getattr(league().settings, "position_slot_counts", {}) or {}
    excluded = {"BE", "IR", "ER", "Rookie", ""}
    return {slot: int(n) for slot, n in counts.items() if int(n) > 0 and slot not in excluded}
