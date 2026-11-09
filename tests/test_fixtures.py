"""Unit tests for round-robin fixture generation."""

import unittest
from tournament.exceptions import ValidationError
from tournament.fixtures import calculate_expected_fixture_count, generate_schedule


class TestFixtureGeneration(unittest.TestCase):
    """Tests covering fixture count formula, pair uniqueness, and boundary constraints."""

    def _create_teams(self, count: int) -> list[dict]:
        return [{"id": f"TM{i:03d}", "name": f"Team {chr(65 + i)}"} for i in range(count)]

    def test_fixture_formula(self):
        """Formula N * (N - 1) // 2 must return correct counts."""
        self.assertEqual(calculate_expected_fixture_count(4), 6)
        self.assertEqual(calculate_expected_fixture_count(6), 15)
        self.assertEqual(calculate_expected_fixture_count(8), 28)

    def test_scenario_3_reject_fewer_than_four_teams(self):
        """Scenario 3: Reject fixture generation with fewer than 4 teams."""
        for count in (0, 1, 2, 3):
            teams = self._create_teams(count)
            with self.assertRaises(ValidationError) as ctx:
                generate_schedule(teams)
            self.assertIn("at least 4 teams", str(ctx.exception))

    def test_reject_more_than_eight_teams(self):
        """Cannot generate schedule if team count exceeds 8."""
        teams = self._create_teams(9)
        with self.assertRaises(ValidationError) as ctx:
            generate_schedule(teams)
        self.assertIn("at most 8 teams", str(ctx.exception))

    def test_scenario_4_four_teams_produce_six_fixtures(self):
        """Scenario 4: 4 teams produce exactly 6 fixtures."""
        teams = self._create_teams(4)
        fixtures = generate_schedule(teams)
        self.assertEqual(len(fixtures), 6)

    def test_scenario_5_six_teams_produce_fifteen_fixtures(self):
        """Scenario 5: 6 teams produce exactly 15 fixtures."""
        teams = self._create_teams(6)
        fixtures = generate_schedule(teams)
        self.assertEqual(len(fixtures), 15)

    def test_scenario_6_no_self_match(self):
        """Scenario 6: No fixture can have identical home and away teams."""
        teams = self._create_teams(5)
        fixtures = generate_schedule(teams)
        for fix in fixtures:
            self.assertNotEqual(
                fix["home_id"],
                fix["away_id"],
                f"Self-match detected in fixture {fix['id']}"
            )

    def test_scenario_7_no_duplicate_unordered_pair(self):
        """Scenario 7: Every unordered pair of teams must appear exactly once."""
        teams = self._create_teams(5)
        fixtures = generate_schedule(teams)
        seen_pairs = set()

        for fix in fixtures:
            pair = frozenset([fix["home_id"], fix["away_id"]])
            self.assertNotIn(
                pair,
                seen_pairs,
                f"Duplicate pair detected for fixture {fix['id']}: {pair}"
            )
            seen_pairs.add(pair)

        # Expected unique pairs count
        expected_count = 5 * 4 // 2
        self.assertEqual(len(seen_pairs), expected_count)

    def test_deterministic_fixture_ids_and_initial_pending_state(self):
        """Fixture IDs should be sequential (M001, M002...) and start as pending with None scores."""
        teams = self._create_teams(4)
        fixtures = generate_schedule(teams)
        for idx, fix in enumerate(fixtures, start=1):
            expected_id = f"M{idx:03d}"
            self.assertEqual(fix["id"], expected_id)
            self.assertEqual(fix["status"], "pending")
            self.assertIsNone(fix["home_score"])
            self.assertIsNone(fix["away_score"])


if __name__ == "__main__":
    unittest.main()
