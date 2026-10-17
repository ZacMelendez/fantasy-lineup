"""Route and serialization tests against a fake league.

espn_client is the single choke point for ESPN access, so replacing its `league()`
with a stand-in exercises every route, the serializers and the dashboard aggregation
without a network call or real credentials.
"""

import pytest
from fastapi.testclient import TestClient

import espn_client
import main
from tests.test_engine import SLOTS, StubPlayer, StubTeam


class FakeSettings:
    def __init__(self):
        # Mirrors espn_api: every lineup slot appears, including unused ones and bench.
        self.position_slot_counts = {**SLOTS, "BE": 6, "IR": 1, "TQB": 0, "P": 0}
        self.scoring_format = [
            {"abbr": "PY", "label": "Passing Yards", "points": 0.04, "id": 3},
            {"abbr": "UNUSED", "label": "Unused", "points": 0, "id": 99},
        ]


class FakeBoxScore:
    def __init__(self, home, away, home_lineup, away_lineup):
        self.home_team = home
        self.away_team = away
        self.home_lineup = home_lineup
        self.away_lineup = away_lineup
        self.home_score = 88.4
        self.away_score = 71.2
        self.home_projected = 104.0
        self.away_projected = 99.0
        self.is_playoff = False
        self.matchup_type = "NONE"


class FakeActivity:
    def __init__(self, team, player):
        self.date = 1_726_000_000_000
        self.actions = [(team, "WAIVER ADDED", player, 14)]


def build_lineup(spec):
    return [StubPlayer(name, position, projection, slot=slot) for name, position, projection, slot in spec]


MY_LINEUP = [
    ("QB1", "QB", 20.0, "QB"),
    ("RB1", "RB", 15.0, "RB"),
    ("RB2", "RB", 12.0, "RB"),
    ("WR1", "WR", 14.0, "WR"),
    ("WR2", "WR", 11.0, "WR"),
    ("TE1", "TE", 9.0, "TE"),
    ("DST1", "D/ST", 7.0, "D/ST"),
    ("K1", "K", 8.0, "K"),
    ("WRbad", "WR", 3.0, "RB/WR/TE"),  # leaves points on the bench
    ("WRgood", "WR", 16.0, "BE"),
    ("RBdead", "RB", 0.5, "BE"),
]

THEIR_LINEUP = [
    ("QB9", "QB", 19.0, "QB"),
    ("RB9", "RB", 18.0, "RB"),
    ("RB8", "RB", 17.0, "RB"),
    ("WR9", "WR", 6.0, "WR"),
    ("WR8", "WR", 5.0, "WR"),
    ("TE9", "TE", 9.0, "TE"),
    ("DST9", "D/ST", 7.0, "D/ST"),
    ("K9", "K", 8.0, "K"),
    ("RB7", "RB", 16.0, "RB/WR/TE"),
    ("RB6", "RB", 15.0, "BE"),
]

FREE_AGENTS = [
    ("FA TE", "TE", 13.0, "FA"),
    ("FA WR", "WR", 4.0, "FA"),
    ("FA RB", "RB", 5.0, "FA"),
    ("FA QB", "QB", 9.0, "FA"),
]


class FakeLeague:
    def __init__(self):
        my_lineup = build_lineup(MY_LINEUP)
        their_lineup = build_lineup(THEIR_LINEUP)

        self.mine = StubTeam(1, "My Team", my_lineup)
        self.theirs = StubTeam(2, "Their Team", their_lineup)
        self.mine.owners = [{"firstName": "Zach", "lastName": "M"}]

        self.teams = [self.mine, self.theirs]
        self.settings = FakeSettings()
        self.current_week = 5
        self.nfl_week = 5
        self._box = FakeBoxScore(self.mine, self.theirs, my_lineup, their_lineup)
        self.refreshed = 0

    def standings(self):
        return self.teams

    def power_rankings(self, week=None):
        return [("12.34", self.mine), ("9.87", self.theirs)]

    def box_scores(self, week=None, player_team_cache=None):
        return [self._box]

    def free_agents(self, week=None, size=50, position=None):
        agents = build_lineup(FREE_AGENTS)
        if position:
            agents = [a for a in agents if a.position == position]
        return agents[:size]

    def recent_activity(self, size=25):
        return [FakeActivity(self.theirs, self.theirs.roster[0])]

    def refresh(self):
        self.refreshed += 1


@pytest.fixture
def client(monkeypatch):
    fake = FakeLeague()
    monkeypatch.setattr(espn_client, "league", lambda: fake)
    monkeypatch.setattr(espn_client, "_memo", {})
    return TestClient(main.app), fake


def test_health_does_not_touch_espn():
    # No fake installed: /health must still answer, so the container reports healthy
    # before the first slow league fetch.
    response = TestClient(main.app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_league_route(client):
    api, _ = client
    body = api.get("/league").json()

    assert body["currentWeek"] == 5
    assert body["myTeamId"] == 1
    # Bench, IR and zero-count slots must not reach the optimizer.
    assert body["slotCounts"] == SLOTS
    # Scoring rules worth zero points are noise.
    assert [item["abbr"] for item in body["scoringFormat"]] == ["PY"]
    assert [t["name"] for t in body["teams"]] == ["My Team", "Their Team"]
    assert body["powerRankings"][0]["score"] == 12.34


def test_teams_and_team_detail(client):
    api, _ = client
    assert len(api.get("/teams").json()) == 2

    body = api.get("/team/1").json()
    assert body["name"] == "My Team"
    assert body["owners"] == ["Zach M"]
    assert len(body["roster"]) == len(MY_LINEUP)
    # Valued roster is sorted by value over replacement, best first.
    values = [p["valueOverReplacement"] for p in body["valuedRoster"]]
    assert values == sorted(values, reverse=True)


def test_team_detail_404(client):
    api, _ = client
    assert api.get("/team/99").status_code == 404


def test_matchups_route(client):
    api, _ = client
    body = api.get("/matchups?week=5").json()

    assert body["week"] == 5
    matchup = body["matchups"][0]
    assert matchup["home"]["name"] == "My Team"
    assert matchup["away"]["name"] == "Their Team"
    assert matchup["home"]["score"] == 88.4
    assert len(matchup["home"]["lineup"]) == len(MY_LINEUP)

    bench = [p for p in matchup["home"]["lineup"] if not p["started"]]
    assert {p["name"] for p in bench} == {"WRgood", "RBdead"}


def test_optimize_route_reports_the_swap(client):
    api, _ = client
    body = api.get("/optimize").json()

    assert body["week"] == 5
    assert body["team"]["name"] == "My Team"
    assert body["opponent"]["name"] == "Their Team"

    lineup = body["lineup"]
    assert lineup["currentProjected"] == 99.0
    assert lineup["pointsLeftOnBench"] == 13.0
    assert lineup["isOptimal"] is False
    assert [s["start"]["name"] for s in lineup["swaps"]] == ["WRgood"]
    assert [s["sit"]["name"] for s in lineup["swaps"]] == ["WRbad"]

    # Opponent is projected higher, so fixing the lineup should improve the odds.
    assert body["winProbability"] < body["winProbabilityIfOptimal"]
    assert 0 <= body["winProbability"] <= 1


def test_optimize_for_a_specific_team(client):
    api, _ = client
    body = api.get("/optimize?team_id=2").json()
    assert body["team"]["name"] == "Their Team"
    assert body["opponent"]["name"] == "My Team"


def test_free_agents_route(client):
    api, _ = client
    body = api.get("/free-agents?size=10").json()

    assert body["count"] == 4
    assert body["replacementLevels"]["TE"] == 13.0
    names = [p["name"] for p in body["players"]]
    assert names[0] == "FA TE"


def test_waivers_route(client):
    api, _ = client
    body = api.get("/waivers").json()

    # The free agent tight end outprojects TE1, so it should be the top target and
    # the worthless running back should be the drop.
    assert body["targets"][0]["name"] == "FA TE"
    assert body["targets"][0]["lineupGain"] == 4.0
    assert body["targets"][0]["dropCandidate"]["name"] == "RBdead"
    # A receiver who would not start must not be recommended.
    assert "FA WR" not in [t["name"] for t in body["targets"]]


def test_trades_route(client):
    api, _ = client
    body = api.get("/trades").json()

    assert body["teamId"] == 1
    for proposal in body["proposals"]:
        assert proposal["withTeamName"] == "Their Team"
        assert proposal["myGain"] > 0
        assert proposal["theirGain"] > 0
        assert proposal["fairness"] in {"even", "favors you", "favors them"}


def test_dashboard_aggregates_actions(client):
    api, _ = client
    body = api.get("/dashboard").json()

    assert body["team"]["name"] == "My Team"
    assert body["lineup"]["pointsLeftOnBench"] == 13.0
    assert isinstance(body["topWaivers"], list)
    assert isinstance(body["topTrades"], list)

    actions = body["actions"]
    assert actions, "expected at least the lineup swap as an action"
    # Highest impact first, and the 13-point lineup fix should lead.
    assert actions == sorted(actions, key=lambda a: a["impact"], reverse=True)
    assert actions[0]["kind"] == "lineup"
    assert actions[0]["headline"] == "Start WRgood over WRbad"
    assert {a["kind"] for a in actions} <= {"lineup", "waiver", "trade"}


def test_activity_route(client):
    api, _ = client
    body = api.get("/activity").json()

    assert body[0]["actions"][0]["team"] == "Their Team"
    assert body[0]["actions"][0]["action"] == "WAIVER ADDED"
    assert body[0]["actions"][0]["bidAmount"] == 14


def test_advice_is_inert_without_a_key(client):
    """conftest clears both provider keys, so this exercises the disabled path: no
    outbound request, no error, just a flag the UI uses to hide the panel."""
    api, _ = client
    assert espn_client.config().ai_enabled is False

    assert api.post("/advice").json() == {
        "enabled": False,
        "narrative": None,
        "detail": "Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable AI commentary.",
    }


def test_config_route(client):
    api, _ = client
    body = api.get("/config").json()
    assert body["leagueId"] == 424242
    assert body["teamId"] == 1
