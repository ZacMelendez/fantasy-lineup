"""HTTP surface for the fantasy dashboard."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import espn_client
import serialize
from engine import advice as advice_engine
from engine import lineup as lineup_engine
from engine import trades as trades_engine
from engine import value as value_engine
from engine import waivers as waivers_engine

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fantasy-api")

app = FastAPI(title="Fantasy Lineup API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(espn_client.LeagueUnavailable)
def league_unavailable(request, exc: espn_client.LeagueUnavailable):
    log.warning("League unavailable on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=exc.status, content={"detail": str(exc)})


@app.exception_handler(Exception)
def unhandled_exception(request, exc):  # pragma: no cover - safety net
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=502, content={"detail": f"Upstream failure: {exc}"})


@app.get("/health")
def health() -> dict:
    """Liveness only. Deliberately does not touch ESPN so the container can report
    healthy before the first (slow) league fetch."""
    return {"status": "ok"}


@app.get("/config")
def get_config() -> dict:
    cfg = espn_client.config()
    return {
        "leagueId": cfg.league_id,
        "year": cfg.year,
        "teamId": cfg.team_id,
        "privateLeague": bool(cfg.espn_s2 and cfg.swid),
        "aiEnabled": cfg.ai_enabled,
        "cacheTtlSeconds": cfg.cache_ttl,
    }


@app.post("/refresh")
def post_refresh() -> dict:
    espn_client.refresh()
    return {"status": "refreshed", "week": espn_client.current_week()}


@app.get("/league")
def get_league() -> dict:
    league = espn_client.league()
    cfg = espn_client.config()

    return {
        "leagueId": cfg.league_id,
        "year": cfg.year,
        "myTeamId": cfg.team_id,
        "currentWeek": espn_client.current_week(),
        "nflWeek": getattr(league, "nfl_week", None),
        "slotCounts": espn_client.starting_slot_counts(),
        "scoringFormat": [
            item for item in (getattr(league.settings, "scoring_format", []) or []) if item.get("points")
        ],
        "teams": [serialize.team_summary(t) for t in espn_client.teams()],
        "standings": [serialize.team_summary(t) for t in league.standings()],
        "powerRankings": _power_rankings(league),
    }


def _power_rankings(league: Any) -> list[dict]:
    try:
        rankings = league.power_rankings()
    except Exception:  # ESPN returns nothing usable before week 1 has scored
        log.warning("Power rankings unavailable", exc_info=True)
        return []

    return [
        {"score": serialize.num(score), "team": serialize.team_summary(team)}
        for score, team in rankings
        if team is not None
    ]


@app.get("/teams")
def get_teams() -> list[dict]:
    return [serialize.team_summary(t) for t in espn_client.teams()]


@app.get("/team/{team_id}")
def get_team(team_id: int) -> dict:
    team = espn_client.team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail=f"No team with id {team_id}")

    levels = value_engine.replacement_levels(espn_client.free_agents(size=200))
    return {
        **serialize.team_detail(team),
        "valuedRoster": value_engine.roster_valuation(getattr(team, "roster", []), levels),
    }


@app.get("/matchups")
def get_matchups(week: int | None = Query(default=None, ge=1, le=18)) -> dict:
    week = week or espn_client.current_week()
    boxes = espn_client.box_scores(week)
    return {
        "week": week,
        "matchups": [serialize.matchup_dict(box, week) for box in boxes],
    }


@app.get("/free-agents")
def get_free_agents(
    position: str | None = Query(default=None),
    size: int = Query(default=100, ge=1, le=400),
) -> dict:
    players = espn_client.free_agents(size=size, position=position)
    levels = value_engine.replacement_levels(players)
    valued = value_engine.roster_valuation(players, levels)
    return {"count": len(valued), "replacementLevels": levels, "players": valued}


@app.get("/activity")
def get_activity(size: int = Query(default=25, ge=1, le=100)) -> list[dict]:
    try:
        activities = espn_client.league().recent_activity(size=size)
    except Exception:
        log.warning("Recent activity unavailable", exc_info=True)
        return []
    return [serialize.activity_dict(a) for a in activities]


@app.get("/optimize")
def get_optimize(
    team_id: int | None = Query(default=None),
    week: int | None = Query(default=None, ge=1, le=18),
) -> dict:
    cfg = espn_client.config()
    return _matchup_context(team_id or cfg.team_id, week or espn_client.current_week())


def _matchup_context(team_id: int, week: int) -> dict:
    """Everything about one team's week: lineup analysis, opponent, win probability."""
    team = espn_client.team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail=f"No team with id {team_id}")

    slot_counts = espn_client.starting_slot_counts()
    boxes = espn_client.box_scores(week)

    found: tuple[str, Any] | None = None
    for box in boxes:
        if getattr(box.home_team, "team_id", None) == team_id:
            found = ("home", box)
            break
        if getattr(box.away_team, "team_id", None) == team_id:
            found = ("away", box)
            break

    if found is None:
        # Bye week in the playoffs, or a week that has not been scheduled yet.
        return {
            "week": week,
            "team": serialize.team_summary(team),
            "lineup": None,
            "opponent": None,
            "winProbability": None,
            "note": "No matchup scheduled for this team this week.",
        }

    side, box = found
    my_lineup = box.home_lineup if side == "home" else box.away_lineup
    my_score = box.home_score if side == "home" else box.away_score

    opponent_team = box.away_team if side == "home" else box.home_team
    opponent_lineup = box.away_lineup if side == "home" else box.home_lineup
    opponent_score = box.away_score if side == "home" else box.home_score

    analysis = lineup_engine.lineup_analysis(my_lineup, slot_counts)
    opponent_analysis = (
        lineup_engine.lineup_analysis(opponent_lineup, slot_counts)
        if opponent_lineup
        else None
    )

    opponent_projection = (
        opponent_analysis["currentProjected"] if opponent_analysis else 0.0
    )

    return {
        "week": week,
        "team": serialize.team_summary(team),
        "score": round(serialize.num(my_score), 2),
        "lineup": analysis,
        "opponent": (
            {
                **serialize.team_summary(opponent_team),
                "score": round(serialize.num(opponent_score), 2),
                "projected": opponent_projection,
                "optimalProjected": (
                    opponent_analysis["optimalProjected"] if opponent_analysis else 0.0
                ),
                "lineup": opponent_analysis["currentLineup"] if opponent_analysis else [],
                "bench": opponent_analysis["bench"] if opponent_analysis else [],
            }
            if opponent_team is not None
            else None
        ),
        "winProbability": lineup_engine.win_probability(
            analysis["currentProjected"], opponent_projection
        ),
        "winProbabilityIfOptimal": lineup_engine.win_probability(
            analysis["optimalProjected"], opponent_projection
        ),
    }


@app.get("/waivers")
def get_waivers(
    team_id: int | None = Query(default=None),
    size: int = Query(default=150, ge=1, le=400),
    limit: int = Query(default=15, ge=1, le=50),
) -> dict:
    cfg = espn_client.config()
    team = espn_client.team_by_id(team_id or cfg.team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    return {
        "teamId": team.team_id,
        **waivers_engine.waiver_targets(
            roster=getattr(team, "roster", []),
            free_agents=espn_client.free_agents(size=size),
            slot_counts=espn_client.starting_slot_counts(),
            limit=limit,
        ),
    }


@app.get("/trades")
def get_trades(
    team_id: int | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
    max_package_size: int = Query(default=2, ge=1, le=2),
) -> dict:
    cfg = espn_client.config()
    team = espn_client.team_by_id(team_id or cfg.team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    others = [t for t in espn_client.teams() if t.team_id != team.team_id]
    return {
        "teamId": team.team_id,
        **trades_engine.find_trades(
            my_team=team,
            other_teams=others,
            free_agents=espn_client.free_agents(size=200),
            slot_counts=espn_client.starting_slot_counts(),
            limit=limit,
            max_package_size=max_package_size,
        ),
    }


@app.get("/dashboard")
def get_dashboard(week: int | None = Query(default=None, ge=1, le=18)) -> dict:
    """One round trip for the home page, so the UI does not fan out four slow calls."""
    cfg = espn_client.config()
    week = week or espn_client.current_week()
    team = espn_client.my_team()
    if team is None:
        raise HTTPException(
            status_code=404,
            detail=f"ESPN_TEAM_ID {cfg.team_id} is not in league {cfg.league_id}.",
        )

    context = _matchup_context(team.team_id, week)
    free_agents = espn_client.free_agents(size=150)
    slot_counts = espn_client.starting_slot_counts()

    waivers = waivers_engine.waiver_targets(
        roster=getattr(team, "roster", []),
        free_agents=free_agents,
        slot_counts=slot_counts,
        limit=5,
    )
    trades = trades_engine.find_trades(
        my_team=team,
        other_teams=[t for t in espn_client.teams() if t.team_id != team.team_id],
        free_agents=free_agents,
        slot_counts=slot_counts,
        limit=5,
    )

    return {
        **context,
        "aiEnabled": cfg.ai_enabled,
        "topWaivers": waivers["targets"],
        "topTrades": trades["proposals"],
        "actions": _action_items(context, waivers["targets"], trades["proposals"]),
    }


def _action_items(context: dict, waivers: list[dict], trades: list[dict]) -> list[dict]:
    """The few things actually worth doing this week, highest impact first."""
    items: list[dict] = []

    analysis = context.get("lineup") or {}
    for swap in (analysis.get("swaps") or [])[:3]:
        items.append(
            {
                "kind": "lineup",
                "headline": f"Start {swap['start']['name']} over {swap['sit']['name']}",
                "impact": swap["gain"],
                "unit": "pts this week",
                "confidence": swap["confidence"],
                "detail": swap["reason"],
            }
        )

    for target in waivers[:2]:
        drop = target.get("dropCandidate")
        headline = f"Add {target['name']}"
        if drop:
            headline += f", drop {drop['name']}"
        items.append(
            {
                "kind": "waiver",
                "headline": headline,
                "impact": target["lineupGain"],
                "unit": "pts/week",
                "confidence": lineup_engine.confidence_for(target["lineupGain"]),
                "detail": target["reason"],
            }
        )

    for trade in trades[:2]:
        items.append(
            {
                "kind": "trade",
                "headline": (
                    f"Offer {', '.join(p['name'] for p in trade['give'])} to "
                    f"{trade['withTeamName']} for {', '.join(p['name'] for p in trade['get'])}"
                ),
                "impact": trade["myGain"],
                "unit": "pts/week",
                "confidence": trade["confidence"],
                "detail": trade["reason"],
            }
        )

    items.sort(key=lambda i: i["impact"], reverse=True)
    return items[:6]


@app.post("/advice")
def post_advice(week: int | None = Query(default=None, ge=1, le=18)) -> dict:
    cfg = espn_client.config()
    if not cfg.ai_enabled:
        return advice_engine.generate_advice(cfg, {})

    dashboard = get_dashboard(week=week)
    context = {
        "week": dashboard["week"],
        "team": dashboard["team"]["name"],
        "record": {
            "wins": dashboard["team"]["wins"],
            "losses": dashboard["team"]["losses"],
            "ties": dashboard["team"]["ties"],
        },
        "matchup": (
            {
                "opponent": dashboard["opponent"]["name"],
                "opponentProjected": dashboard["opponent"]["projected"],
            }
            if dashboard.get("opponent")
            else None
        ),
        "winProbability": dashboard.get("winProbability"),
        "lineup": dashboard.get("lineup"),
        "trades": dashboard.get("topTrades"),
        "waivers": dashboard.get("topWaivers"),
    }
    return advice_engine.generate_advice(cfg, context)
