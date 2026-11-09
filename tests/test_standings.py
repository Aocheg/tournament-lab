"""Unit tests for result recording, standings calculation, tie-breaks, and champion crowning."""

import unittest
from tournament.exceptions import DuplicateError, NotFoundError, ValidationError
from tournament.fixtures import generate_schedule, record_result
from tournament.standings import (
    compute_standings,
    get_champion,
    get_season_status,
    verify_league_invariants,
)
from tournament.teams import register_team


class TestStandingsAndResults(unittest.TestCase):
    """Tests covering scoring rules, multi-key tie breaks, and champion determination."""

    def setUp(self):
        self.teams = []
        register_team(self.teams, "Red")
        register_team(self.teams, "Blue")
        register_team(self.teams, "Green")
        register_team(self.teams, "Yellow")
        self.fixtures = generate_schedule(self.teams)

    def test_scenario_8_reject_negative_goals(self):
        """Scenario 8: Reject negative goals."""
        with self.assertRaises(ValidationError) as ctx:
            record_result(self.fixtures, "M001", -1, 2)
        self.assertIn("must be non-negative integers", str(ctx.exception))
        # Ensure fixture remains pending
        fix = self.fixtures[0]
        self.assertEqual(fix["status"], "pending")
        self.assertIsNone(fix["home_score"])

    def test_scenario_8_reject_float_goals(self):
        """Scenario 8: Reject float goals."""
        with self.assertRaises(ValidationError) as ctx:
            record_result(self.fixtures, "M001", 2.5, 1)
        self.assertIn("must be non-negative integers", str(ctx.exception))
        self.assertEqual(self.fixtures[0]["status"], "pending")

    def test_scenario_8_reject_bool_goals(self):
        """Scenario 8: Reject boolean goals (since isinstance(True, int) is True)."""
        with self.assertRaises(ValidationError) as ctx:
            record_result(self.fixtures, "M001", True, 0)
        self.assertIn("must be non-negative integers", str(ctx.exception))
        with self.assertRaises(ValidationError) as ctx:
            record_result(self.fixtures, "M001", 0, False)
        self.assertIn("must be non-negative integers", str(ctx.exception))
        self.assertEqual(self.fixtures[0]["status"], "pending")

    def test_scenario_9_reject_unknown_fixture(self):
        """Scenario 9: Reject recording a result for an unknown fixture ID."""
        with self.assertRaises(NotFoundError) as ctx:
            record_result(self.fixtures, "M999", 2, 1)
        self.assertIn("not found", str(ctx.exception))

    def test_scenario_10_reject_duplicate_result(self):
        """Scenario 10: Reject duplicate result submission on an already played fixture."""
        record_result(self.fixtures, "M001", 2, 1)
        self.assertEqual(self.fixtures[0]["status"], "played")

        with self.assertRaises(DuplicateError) as ctx:
            record_result(self.fixtures, "M001", 3, 0)
        self.assertIn("already been played", str(ctx.exception))
        # Scores must remain unchanged (2-1)
        self.assertEqual(self.fixtures[0]["home_score"], 2)
        self.assertEqual(self.fixtures[0]["away_score"], 1)

    def test_scenario_11_correct_points_win_draw_loss(self):
        """Scenario 11: Award 3 pts for a win, 1 pt for a draw, 0 for a loss."""
        # M001: Red (TM001) vs Blue (TM002) -> 3-1 (Red wins, Blue loses)
        record_result(self.fixtures, "M001", 3, 1)
        # M002: Red (TM001) vs Green (TM003) -> 2-2 (Draw)
        record_result(self.fixtures, "M002", 2, 2)

        standings = compute_standings(self.teams, self.fixtures)
        red = next(r for r in standings if r["team_id"] == "TM001")
        blue = next(r for r in standings if r["team_id"] == "TM002")
        green = next(r for r in standings if r["team_id"] == "TM003")

        # Red: 1 win (3 pts) + 1 draw (1 pt) = 4 pts
        self.assertEqual(red["won"], 1)
        self.assertEqual(red["drawn"], 1)
        self.assertEqual(red["lost"], 0)
        self.assertEqual(red["points"], 4)

        # Blue: 0 win + 0 draw + 1 loss = 0 pts
        self.assertEqual(blue["won"], 0)
        self.assertEqual(blue["drawn"], 0)
        self.assertEqual(blue["lost"], 1)
        self.assertEqual(blue["points"], 0)

        # Green: 0 win + 1 draw = 1 pt
        self.assertEqual(green["won"], 0)
        self.assertEqual(green["drawn"], 1)
        self.assertEqual(green["lost"], 0)
        self.assertEqual(green["points"], 1)

    def test_scenario_12_tie_break_sorting(self):
        """Scenario 12: Rank by points desc, GD desc, GF desc, normalized name asc."""
        teams = [
            {"id": "TM001", "name": "Zulu"},
            {"id": "TM002", "name": "Alpha"},
            {"id": "TM003", "name": "Beta"},
            {"id": "TM004", "name": "Gamma"},
        ]
        # Craft fixtures to create exact tie-break conditions
        # Case A: Same points (3), different GD (+2 vs +1)
        # Case B: Same points (3), same GD (+1), different GF (4 vs 3)
        # Case C: Same points (3), same GD (+1), same GF (3), sorted alphabetically by name
        fixtures = [
            {"id": "M001", "home_id": "TM001", "away_id": "TM004", "status": "played", "home_score": 3, "away_score": 2}, # Zulu: 3pts, GF:3, GA:2, GD:+1
            {"id": "M002", "home_id": "TM002", "away_id": "TM004", "status": "played", "home_score": 3, "away_score": 2}, # Alpha: 3pts, GF:3, GA:2, GD:+1
            {"id": "M003", "home_id": "TM003", "away_id": "TM004", "status": "played", "home_score": 4, "away_score": 3}, # Beta: 3pts, GF:4, GA:3, GD:+1
        ]
        # Beta has same pts (3) and GD (+1) as Alpha and Zulu, but GF:4 > GF:3 -> Beta ranks above them.
        # Alpha and Zulu have same pts (3), GD (+1), and GF (3).
        # Alpha ('alpha') precedes Zulu ('zulu') alphabetically!
        standings = compute_standings(teams, fixtures)

        ranked_names = [r["name"] for r in standings]
        self.assertEqual(ranked_names[0], "Beta")   # GF = 4
        self.assertEqual(ranked_names[1], "Alpha")  # GF = 3, name 'Alpha'
        self.assertEqual(ranked_names[2], "Zulu")   # GF = 3, name 'Zulu'
        self.assertEqual(ranked_names[3], "Gamma")  # 0 pts

    def test_scenario_13_standings_recomputed_from_matches(self):
        """Scenario 13: Standings are dynamically derived; no stale or driftable scoreboard."""
        # Initial: 0 points for all
        initial = compute_standings(self.teams, self.fixtures)
        self.assertTrue(all(r["points"] == 0 for r in initial))

        # Record a match
        record_result(self.fixtures, "M001", 1, 0)
        updated = compute_standings(self.teams, self.fixtures)
        self.assertEqual(updated[0]["points"], 3)

        # Confirm source of truth integrity
        valid, _ = verify_league_invariants(updated, self.fixtures)
        self.assertTrue(valid)

    def test_scenario_16_champion_shown_only_when_all_matches_played(self):
        """Scenario 16: Champion is only crowned when all matches are played; otherwise in progress."""
        # With 0 played matches
        champ, msg = get_champion(self.teams, self.fixtures)
        self.assertIsNone(champ)
        self.assertIn("in progress", msg)
        self.assertEqual(get_season_status(self.fixtures), "in_progress")

        # Play 5 of 6 matches
        for fix in self.fixtures[:5]:
            record_result(self.fixtures, fix["id"], 1, 0)

        champ, msg = get_champion(self.teams, self.fixtures)
        self.assertIsNone(champ)
        self.assertIn("in progress", msg)

        # Play the last match
        record_result(self.fixtures, self.fixtures[5]["id"], 2, 2)
        self.assertEqual(get_season_status(self.fixtures), "completed")

        champ, msg = get_champion(self.teams, self.fixtures)
        self.assertIsNotNone(champ)
        self.assertEqual(champ["rank"], 1)
        self.assertIn("Champion:", msg)

    def test_diagnostic_stage_0_validation(self):
        """Verify the exact diagnostic scenario from Stage 0:
        Teams: Red, Blue, Green
        Matches:
        Red 2-0 Blue
        Blue 1-1 Green
        Red 0-1 Green
        Table expectation:
        Green: P2, W1, D1, L0, GF2, GA1, GD+1, PTS 4
        Red:   P2, W1, D0, L1, GF2, GA1, GD+1, PTS 3
        Blue:  P2, W0, D1, L1, GF1, GA3, GD-2, PTS 1
        """
        teams = [
            {"id": "TM001", "name": "Red"},
            {"id": "TM002", "name": "Blue"},
            {"id": "TM003", "name": "Green"},
        ]
        fixtures = [
            {"id": "M001", "home_id": "TM001", "away_id": "TM002", "status": "played", "home_score": 2, "away_score": 0},
            {"id": "M002", "home_id": "TM002", "away_id": "TM003", "status": "played", "home_score": 1, "away_score": 1},
            {"id": "M003", "home_id": "TM001", "away_id": "TM003", "status": "played", "home_score": 0, "away_score": 1},
        ]
        standings = compute_standings(teams, fixtures)
        self.assertEqual(standings[0]["name"], "Green")
        self.assertEqual(standings[0]["points"], 4)
        self.assertEqual(standings[0]["goal_difference"], 1)

        self.assertEqual(standings[1]["name"], "Red")
        self.assertEqual(standings[1]["points"], 3)
        self.assertEqual(standings[1]["goal_difference"], 1)

        self.assertEqual(standings[2]["name"], "Blue")
        self.assertEqual(standings[2]["points"], 1)
        self.assertEqual(standings[2]["goal_difference"], -2)

        # Invariants
        valid, msg = verify_league_invariants(standings, fixtures)
        self.assertTrue(valid, msg)


if __name__ == "__main__":
    unittest.main()
