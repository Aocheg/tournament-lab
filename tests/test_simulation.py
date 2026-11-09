"""Unit tests for demo fixture simulation reproducibility."""

import unittest
from tournament.fixtures import generate_schedule
from tournament.models import STATUS_PLAYED
from tournament.simulation import simulate_demo_fixtures
from tournament.standings import compute_standings
from tournament.teams import register_team


class TestSimulation(unittest.TestCase):
    """Tests covering seeded reproducibility and partial simulation behavior."""

    def setUp(self):
        self.teams = []
        for name in ("Alpha", "Bravo", "Charlie", "Delta"):
            register_team(self.teams, name)

    def test_reproducible_simulation_with_seed(self):
        """Identical seeds must produce identical match scores and standings."""
        fixtures_1 = generate_schedule(self.teams)
        simulate_demo_fixtures(fixtures_1, seed=123)

        fixtures_2 = generate_schedule(self.teams)
        simulate_demo_fixtures(fixtures_2, seed=123)

        for f1, f2 in zip(fixtures_1, fixtures_2):
            self.assertEqual(f1["home_score"], f2["home_score"])
            self.assertEqual(f1["away_score"], f2["away_score"])
            self.assertEqual(f1["status"], STATUS_PLAYED)

        standings_1 = compute_standings(self.teams, fixtures_1)
        standings_2 = compute_standings(self.teams, fixtures_2)

        for r1, r2 in zip(standings_1, standings_2):
            self.assertEqual(r1["team_id"], r2["team_id"])
            self.assertEqual(r1["points"], r2["points"])
            self.assertEqual(r1["goal_difference"], r2["goal_difference"])

    def test_simulation_does_not_overwrite_played_fixtures(self):
        """Simulation must only affect pending fixtures."""
        fixtures = generate_schedule(self.teams)
        # Manually play fixture M001
        fixtures[0]["status"] = STATUS_PLAYED
        fixtures[0]["home_score"] = 7
        fixtures[0]["away_score"] = 5

        # Simulate remaining 5 fixtures
        count = simulate_demo_fixtures(fixtures, seed=99)
        self.assertEqual(count, 5)

        # M001 must still have original scores
        self.assertEqual(fixtures[0]["home_score"], 7)
        self.assertEqual(fixtures[0]["away_score"], 5)


if __name__ == "__main__":
    unittest.main()
