"""Unit tests for team registration and validation."""

import unittest
from tournament.exceptions import DuplicateError, ValidationError
from tournament.models import MAX_TEAMS
from tournament.teams import register_team, validate_team_name, generate_team_id


class TestTeamRegistration(unittest.TestCase):
    """Tests covering team validation, uniqueness, and ID generation."""

    def setUp(self):
        self.teams = []

    def test_register_single_team_success(self):
        """Should successfully register a valid team and assign TM001."""
        team = register_team(self.teams, "Red Comets")
        self.assertEqual(team["id"], "TM001")
        self.assertEqual(team["name"], "Red Comets")
        self.assertEqual(len(self.teams), 1)

    def test_scenario_1_reject_duplicate_casefolded_team_name(self):
        """Scenario 1: Reject duplicate casefolded team name."""
        register_team(self.teams, "Red Comets")
        with self.assertRaises(DuplicateError) as ctx:
            register_team(self.teams, "  red comets  ")
        self.assertIn("already registered", str(ctx.exception))
        # Ensure list still has only 1 team
        self.assertEqual(len(self.teams), 1)

    def test_scenario_2_reject_blank_and_too_short_name(self):
        """Scenario 2: Reject blank name or name shorter than 2 characters."""
        with self.assertRaises(ValidationError):
            register_team(self.teams, "")
        with self.assertRaises(ValidationError):
            register_team(self.teams, "   ")
        with self.assertRaises(ValidationError):
            register_team(self.teams, "A")
        with self.assertRaises(ValidationError):
            register_team(self.teams, " A ")
        self.assertEqual(len(self.teams), 0)

    def test_scenario_2_reject_too_long_name(self):
        """Scenario 2: Reject team name longer than 30 characters after trim."""
        long_name = "A" * 31
        with self.assertRaises(ValidationError):
            register_team(self.teams, long_name)
        # Exactly 30 chars should succeed
        valid_30 = "A" * 30
        team = register_team(self.teams, valid_30)
        self.assertEqual(team["name"], valid_30)

    def test_name_trimming(self):
        """Names should be trimmed of leading/trailing whitespace."""
        team = register_team(self.teams, "   Blue Wolves   ")
        self.assertEqual(team["name"], "Blue Wolves")

    def test_reject_non_string_name(self):
        """Non-string names should raise ValidationError."""
        with self.assertRaises(ValidationError):
            register_team(self.teams, 12345)
        with self.assertRaises(ValidationError):
            register_team(self.teams, None)

    def test_maximum_eight_teams_enforced(self):
        """Cannot register more than 8 teams."""
        for i in range(MAX_TEAMS):
            register_team(self.teams, f"Team {i + 1}")
        self.assertEqual(len(self.teams), 8)

        with self.assertRaises(ValidationError) as ctx:
            register_team(self.teams, "Team 9")
        self.assertIn("Maximum league capacity reached", str(ctx.exception))
        self.assertEqual(len(self.teams), 8)

    def test_stable_sequential_team_ids(self):
        """Team IDs should follow TM001, TM002, TM003 format predictably."""
        t1 = register_team(self.teams, "Alpha")
        t2 = register_team(self.teams, "Bravo")
        t3 = register_team(self.teams, "Charlie")
        self.assertEqual(t1["id"], "TM001")
        self.assertEqual(t2["id"], "TM002")
        self.assertEqual(t3["id"], "TM003")


if __name__ == "__main__":
    unittest.main()
