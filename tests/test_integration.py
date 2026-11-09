"""Integration tests covering end-to-end tournament lifecycle and controlled dataset."""

from pathlib import Path
import tempfile
import unittest

from tournament.exceptions import ValidationError
from tournament.fixtures import generate_schedule, record_result
from tournament.models import STATUS_PLAYED
from tournament.standings import (
    compute_standings,
    get_champion,
    get_season_status,
    verify_league_invariants,
)
from tournament.storage import load_tournament, save_tournament
from tournament.teams import register_team


class TestControlledDemonstrationDataset(unittest.TestCase):
    """End-to-end test following Stage 4 Controlled Demonstration Dataset specifications."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_path = Path(self.temp_dir.name) / "demo_season.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_full_controlled_lifecycle(self):
        """Walkthrough of the full controlled demonstration dataset:

        1. Register four teams: Thunder, Comets, Phoenix, Rockets.
        2. Generate 6 fixtures.
        3. Enter scores for two fixtures (one win, one draw).
        4. Verify standings manually against expected values.
        5. Submit intentionally invalid score (confirm no state mutation).
        6. Save and reload from JSON; verify identical standings.
        7. Complete remaining fixtures and verify champion is crowned.
        """
        # Step 1: Register 4 teams
        teams = []
        register_team(teams, "Thunder")   # TM001
        register_team(teams, "Comets")    # TM002
        register_team(teams, "Phoenix")   # TM003
        register_team(teams, "Rockets")   # TM004
        self.assertEqual(len(teams), 4)

        # Step 2: Generate fixtures -> 6 fixtures expected
        fixtures = generate_schedule(teams)
        self.assertEqual(len(fixtures), 6)

        # Confirm fixtures:
        # M001: Thunder (TM001) vs Comets (TM002)
        # M002: Thunder (TM001) vs Phoenix (TM003)
        # M003: Thunder (TM001) vs Rockets (TM004)
        # M004: Comets (TM002) vs Phoenix (TM003)
        # M005: Comets (TM002) vs Rockets (TM004)
        # M006: Phoenix (TM003) vs Rockets (TM004)

        # Step 3: Enter scores for exactly two fixtures: one win, one draw
        # M001: Thunder 2 - 0 Comets (Win for Thunder)
        record_result(fixtures, "M001", 2, 0)
        # M002: Thunder 1 - 1 Phoenix (Draw)
        record_result(fixtures, "M002", 1, 1)

        # Step 4: Verify standings manually
        # Expected Table:
        # Thunder: P:2, W:1, D:1, L:0, GF:3, GA:1, GD:+2, PTS:4
        # Phoenix: P:1, W:0, D:1, L:0, GF:1, GA:1, GD: 0, PTS:1
        # Rockets: P:0, W:0, D:0, L:0, GF:0, GA:0, GD: 0, PTS:0 (Sorted before Comets on GD: 0 vs -2)
        # Comets:  P:1, W:0, D:0, L:1, GF:0, GA:2, GD:-2, PTS:0
        standings = compute_standings(teams, fixtures)
        self.assertEqual(len(standings), 4)

        # Thunder checks
        self.assertEqual(standings[0]["name"], "Thunder")
        self.assertEqual(standings[0]["played"], 2)
        self.assertEqual(standings[0]["won"], 1)
        self.assertEqual(standings[0]["drawn"], 1)
        self.assertEqual(standings[0]["lost"], 0)
        self.assertEqual(standings[0]["goals_for"], 3)
        self.assertEqual(standings[0]["goals_against"], 1)
        self.assertEqual(standings[0]["goal_difference"], 2)
        self.assertEqual(standings[0]["points"], 4)

        # Phoenix checks
        self.assertEqual(standings[1]["name"], "Phoenix")
        self.assertEqual(standings[1]["played"], 1)
        self.assertEqual(standings[1]["points"], 1)
        self.assertEqual(standings[1]["goal_difference"], 0)

        # Rockets checks (0 played, 0 pts, GD 0 > Comets GD -2)
        self.assertEqual(standings[2]["name"], "Rockets")
        self.assertEqual(standings[2]["points"], 0)
        self.assertEqual(standings[2]["goal_difference"], 0)

        # Comets checks (1 played, 0 pts, GD -2)
        self.assertEqual(standings[3]["name"], "Comets")
        self.assertEqual(standings[3]["points"], 0)
        self.assertEqual(standings[3]["goal_difference"], -2)

        # Verify invariants
        valid, inv_msg = verify_league_invariants(standings, fixtures)
        self.assertTrue(valid, inv_msg)

        # Confirm season status is in progress
        self.assertEqual(get_season_status(fixtures), "in_progress")
        champ, champ_msg = get_champion(teams, fixtures)
        self.assertIsNone(champ)
        self.assertIn("in progress", champ_msg)

        # Step 5: Submit an intentionally invalid score (negative number, boolean, float)
        # Confirm no standings change
        with self.assertRaises(ValidationError):
            record_result(fixtures, "M003", -1, 3)
        with self.assertRaises(ValidationError):
            record_result(fixtures, "M003", True, 2)
        with self.assertRaises(ValidationError):
            record_result(fixtures, "M003", 2, 1.5)

        # Confirm M003 is still pending and standings are completely identical
        self.assertEqual(fixtures[2]["status"], "pending")
        table_after_rejected = compute_standings(teams, fixtures)
        self.assertEqual(standings, table_after_rejected)

        # Step 6: Save and reload from JSON; verify identical standings
        save_tournament(self.save_path, teams, fixtures)
        loaded = load_tournament(self.save_path)
        loaded_teams = loaded["teams"]
        loaded_fixtures = loaded["fixtures"]

        reloaded_standings = compute_standings(loaded_teams, loaded_fixtures)
        self.assertEqual(standings, reloaded_standings)

        # Step 7: Complete remaining 4 fixtures:
        # M003: Thunder vs Rockets -> 3 - 0 (Thunder wins)
        record_result(loaded_fixtures, "M003", 3, 0)
        # M004: Comets vs Phoenix  -> 1 - 2 (Phoenix wins)
        record_result(loaded_fixtures, "M004", 1, 2)
        # M005: Comets vs Rockets  -> 2 - 1 (Comets wins)
        record_result(loaded_fixtures, "M005", 2, 1)
        # M006: Phoenix vs Rockets -> 0 - 0 (Draw)
        record_result(loaded_fixtures, "M006", 0, 0)

        # Verify all 6 fixtures played
        self.assertEqual(get_season_status(loaded_fixtures), "completed")

        final_standings = compute_standings(loaded_teams, loaded_fixtures)
        valid, inv_msg = verify_league_invariants(final_standings, loaded_fixtures)
        self.assertTrue(valid, inv_msg)

        # Thunder finished: 3 played, 2 wins, 1 draw, 0 loss = 7 pts. Champion!
        champion, crown_msg = get_champion(loaded_teams, loaded_fixtures)
        self.assertIsNotNone(champion)
        self.assertEqual(champion["name"], "Thunder")
        self.assertEqual(champion["points"], 7)
        self.assertIn("Thunder", crown_msg)


if __name__ == "__main__":
    unittest.main()
