"""Engine tests against hand-built rosters.

These use stub players rather than live ESPN data so the interesting cases (flex
eligibility, a thin waiver pool, a trade that only works for one side) can be set up
exactly.
"""

from engine import lineup as lineup_engine
from engine import trades as trades_engine
from engine import value as value_engine
from engine import waivers as waivers_engine

SLOTS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "RB/WR/TE": 1, "D/ST": 1, "K": 1}

ELIGIBILITY = {
    "QB": ["QB", "OP", "BE", "IR"],
    "RB": ["RB", "RB/WR", "RB/WR/TE", "OP", "BE", "IR"],
    "WR": ["WR", "RB/WR", "WR/TE", "RB/WR/TE", "OP", "BE", "IR"],
    "TE": ["TE", "WR/TE", "RB/WR/TE", "OP", "BE", "IR"],
    "D/ST": ["D/ST", "BE", "IR"],
    "K": ["K", "BE", "IR"],
}

_next_id = iter(range(1, 10_000))


class StubPlayer:
    def __init__(self, name, position, projection, slot="BE", injury="ACTIVE", bye=False):
        self.playerId = next(_next_id)
        self.name = name
        self.position = position
        self.proTeam = "SF"
        self.eligibleSlots = list(ELIGIBILITY[position])
        self.slot_position = slot
        self.injuryStatus = injury
        self.injured = injury != "ACTIVE"
        self.on_bye_week = bye
        self.projected_points = projection
        self.projected_avg_points = projection
        self.avg_points = projection
        self.total_points = projection * 4
        self.projected_total_points = projection * 17
        self.points = 0.0
        self.percent_owned = 50.0
        self.percent_started = 40.0
        self.posRank = 10
        self.pro_opponent = "SEA"
        self.pro_pos_rank = 28
        self.game_played = 0


class StubTeam:
    def __init__(self, team_id, name, roster):
        self.team_id = team_id
        self.team_name = name
        self.team_abbrev = name[:4].upper()
        self.roster = roster
        self.wins = 3
        self.losses = 2
        self.ties = 0
        self.points_for = 500.0
        self.points_against = 480.0
        self.standing = team_id
        self.owners = []
        self.logo_url = ""


def starters(count_by_slot):
    """Build a legal-looking starting lineup plus bench from a spec."""
    return count_by_slot


def test_solver_uses_flex_optimally():
    """A bench receiver who outprojects a rostered starter should be promoted into
    the flex slot, displacing the weakest flex-eligible starter."""
    players = [
        StubPlayer("QB1", "QB", 20, slot="QB"),
        StubPlayer("RB1", "RB", 15, slot="RB"),
        StubPlayer("RB2", "RB", 12, slot="RB"),
        StubPlayer("WR1", "WR", 14, slot="WR"),
        StubPlayer("WR2", "WR", 11, slot="WR"),
        StubPlayer("TE1", "TE", 9, slot="TE"),
        StubPlayer("DST", "D/ST", 7, slot="D/ST"),
        StubPlayer("K1", "K", 8, slot="K"),
        StubPlayer("WR3", "WR", 13, slot="BE"),  # outprojects WR2, belongs in the lineup
        StubPlayer("TE2", "TE", 4, slot="BE"),
    ]

    assignments, total = lineup_engine.optimal_lineup(
        players, SLOTS, lambda p: p.projected_points
    )

    # WR2 and WR3 are interchangeable between the WR and flex columns, so assert on
    # who starts rather than on which column each lands in.
    assert len(assignments) == 9
    assert {a.player.name for a in assignments} == {
        "QB1", "RB1", "RB2", "WR1", "WR2", "WR3", "TE1", "DST", "K1"
    }
    assert total == 20 + 15 + 12 + 14 + 11 + 9 + 7 + 8 + 13
    assert sorted(a.slot for a in assignments) == sorted(
        ["QB", "RB", "RB", "WR", "WR", "TE", "RB/WR/TE", "D/ST", "K"]
    )


def test_solver_never_double_starts_a_player():
    players = [
        StubPlayer("QB1", "QB", 20),
        StubPlayer("RB1", "RB", 15),
        StubPlayer("WR1", "WR", 14),
    ]
    assignments, _ = lineup_engine.optimal_lineup(players, SLOTS, lambda p: p.projected_points)

    names = [a.player.name for a in assignments]
    assert len(names) == len(set(names))
    # Only three players exist, so only three of the nine slots can be filled.
    assert len(names) == 3


def test_solver_respects_slot_eligibility():
    """A kicker must never be assigned anywhere but K, even if slots go unfilled."""
    players = [StubPlayer("K1", "K", 8), StubPlayer("K2", "K", 7)]
    assignments, _ = lineup_engine.optimal_lineup(players, SLOTS, lambda p: p.projected_points)

    assert [a.slot for a in assignments] == ["K"]


def test_lineup_analysis_flags_the_benched_starter():
    lineup = [
        StubPlayer("QB1", "QB", 20, slot="QB"),
        StubPlayer("RB1", "RB", 15, slot="RB"),
        StubPlayer("RB2", "RB", 12, slot="RB"),
        StubPlayer("WR1", "WR", 14, slot="WR"),
        StubPlayer("WR2", "WR", 11, slot="WR"),
        StubPlayer("TE1", "TE", 9, slot="TE"),
        StubPlayer("DST", "D/ST", 7, slot="D/ST"),
        StubPlayer("K1", "K", 8, slot="K"),
        StubPlayer("WRbad", "WR", 3, slot="RB/WR/TE"),
        StubPlayer("WRgood", "WR", 16, slot="BE"),
    ]

    analysis = lineup_engine.lineup_analysis(lineup, SLOTS)

    assert analysis["isOptimal"] is False
    assert analysis["pointsLeftOnBench"] == 13.0
    assert len(analysis["swaps"]) == 1
    swap = analysis["swaps"][0]
    assert swap["start"]["name"] == "WRgood"
    assert swap["sit"]["name"] == "WRbad"
    assert swap["gain"] == 13.0
    assert swap["confidence"] == "high"


def test_out_and_bye_players_project_zero():
    hurt = StubPlayer("Hurt", "RB", 14, slot="RB", injury="OUT")
    bye = StubPlayer("Bye", "WR", 13, slot="WR", bye=True)

    assert lineup_engine.serialize.week_projection(hurt) == 0.0
    assert lineup_engine.serialize.week_projection(bye) == 0.0


def test_win_probability_is_centred_and_monotonic():
    assert lineup_engine.win_probability(100, 100) == 0.5
    assert lineup_engine.win_probability(130, 100) > 0.7
    assert lineup_engine.win_probability(70, 100) < 0.3


def test_value_over_replacement_uses_best_free_agent():
    free_agents = [
        StubPlayer("FA RB", "RB", 6),
        StubPlayer("FA WR", "WR", 11),
        StubPlayer("FA WR2", "WR", 9),
    ]
    levels = value_engine.replacement_levels(free_agents)

    assert levels["RB"] == 6
    assert levels["WR"] == 11

    rb = StubPlayer("My RB", "RB", 12)
    wr = StubPlayer("My WR", "WR", 12)
    # Same projection, but the running back is worth far more given the pools.
    assert value_engine.value_over_replacement(rb, levels) == 6
    assert value_engine.value_over_replacement(wr, levels) == 1


def test_waiver_target_ignores_a_player_who_would_not_start():
    roster = [
        StubPlayer("QB1", "QB", 20),
        StubPlayer("RB1", "RB", 15),
        StubPlayer("RB2", "RB", 14),
        StubPlayer("WR1", "WR", 18),
        StubPlayer("WR2", "WR", 17),
        StubPlayer("WR3", "WR", 16),
        StubPlayer("TE1", "TE", 10),
        StubPlayer("DST", "D/ST", 7),
        StubPlayer("K1", "K", 8),
        StubPlayer("Deadweight", "WR", 1),
    ]
    free_agents = [
        StubPlayer("Marginal WR", "WR", 5),  # buried behind three better receivers
        StubPlayer("Upgrade TE", "TE", 14),  # clear starter over TE1
    ]

    result = waivers_engine.waiver_targets(roster, free_agents, SLOTS, limit=10)
    names = [t["name"] for t in result["targets"]]

    assert names == ["Upgrade TE"]
    assert result["targets"][0]["lineupGain"] == 4.0
    assert result["targets"][0]["dropCandidate"]["name"] == "Deadweight"


def test_trade_finder_surfaces_a_mutually_beneficial_swap():
    """I have a fourth receiver who cannot crack the lineup and a replacement-level
    second running back. They are the mirror image. Swapping the two surplus pieces
    should improve both starting lineups even though the players are worth the same
    in isolation."""
    mine = StubTeam(
        1,
        "Mine",
        [
            StubPlayer("QB1", "QB", 20),
            StubPlayer("RB1", "RB", 12),
            StubPlayer("RB2", "RB", 4),  # the hole
            StubPlayer("WR1", "WR", 20),
            StubPlayer("WR2", "WR", 19),
            StubPlayer("WR3", "WR", 18),
            StubPlayer("WR4", "WR", 17),  # the surplus: benched behind three better WRs
            StubPlayer("TE1", "TE", 10),
            StubPlayer("DST", "D/ST", 7),
            StubPlayer("K1", "K", 8),
        ],
    )
    theirs = StubTeam(
        2,
        "Theirs",
        [
            StubPlayer("QB9", "QB", 19),
            StubPlayer("RB9", "RB", 19),
            StubPlayer("RB8", "RB", 18),
            StubPlayer("RB7", "RB", 17),
            StubPlayer("RB6", "RB", 16),  # their surplus
            StubPlayer("WR9", "WR", 5),  # their hole
            StubPlayer("WR8", "WR", 4),
            StubPlayer("TE9", "TE", 9),
            StubPlayer("DST9", "D/ST", 7),
            StubPlayer("K9", "K", 8),
        ],
    )
    free_agents = [StubPlayer("FA RB", "RB", 3), StubPlayer("FA WR", "WR", 3)]

    result = trades_engine.find_trades(mine, [theirs], free_agents, SLOTS, limit=5)
    proposals = result["proposals"]

    assert proposals, "expected at least one mutually beneficial trade"
    assert all(p["myGain"] > 0 and p["theirGain"] > 0 for p in proposals)
    assert all(p["withTeamName"] == "Theirs" for p in proposals)
    # Every deal should bring running backs in, since that is the only hole I have.
    assert all({x["position"] for x in p["get"]} == {"RB"} for p in proposals)

    # The plain surplus-for-surplus swap should be among the options: my fourth
    # receiver, who never starts, for a back who immediately does.
    one_for_ones = [
        p for p in proposals if len(p["give"]) == 1 and p["give"][0]["name"] == "WR4"
    ]
    assert one_for_ones, "expected the WR4-for-a-running-back swap to be found"
    assert one_for_ones[0]["myGain"] >= 11.0


def test_trade_finder_rejects_one_sided_deals():
    """Two identical rosters have nothing to gain from trading with each other."""
    def roster():
        return [
            StubPlayer("QB", "QB", 20),
            StubPlayer("RB1", "RB", 15),
            StubPlayer("RB2", "RB", 14),
            StubPlayer("WR1", "WR", 13),
            StubPlayer("WR2", "WR", 12),
            StubPlayer("TE", "TE", 10),
            StubPlayer("DST", "D/ST", 7),
            StubPlayer("K", "K", 8),
        ]

    result = trades_engine.find_trades(
        StubTeam(1, "A", roster()), [StubTeam(2, "B", roster())], [], SLOTS
    )
    assert result["proposals"] == []


def test_kickers_and_defenses_are_not_traded():
    mine = StubTeam(1, "Mine", [StubPlayer("K1", "K", 3), StubPlayer("DST", "D/ST", 2)])
    theirs = StubTeam(2, "Theirs", [StubPlayer("K9", "K", 12), StubPlayer("DST9", "D/ST", 11)])

    result = trades_engine.find_trades(mine, [theirs], [], SLOTS)
    assert result["proposals"] == []
    assert result["candidatesConsidered"] == 0
