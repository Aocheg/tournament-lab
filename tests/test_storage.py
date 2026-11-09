"""Unit tests for JSON persistence, schema validation, and referential integrity."""

import json
from pathlib import Path
import tempfile
import unittest

from tournament.exceptions import StorageError
from tournament.fixtures import generate_schedule
from tournament.storage import load_tournament, save_tournament, validate_tournament_data
from tournament.teams import register_team


class TestStorage(unittest.TestCase):
    """Tests covering persistence, schema versioning, integrity, and validate-before-mutate."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "tournament.json"
        self.teams = []
        register_team(self.teams, "Thunder")
        register_team(self.teams, "Comets")
        register_team(self.teams, "Phoenix")
        register_team(self.teams, "Rockets")
        self.fixtures = generate_schedule(self.teams)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scenario_15_reload_preserves_ids_and_standings(self):
        """Scenario 15: Save and reload preserves exact IDs, teams, and fixture states."""
        # Set one fixture as played
        self.fixtures[0]["status"] = "played"
        self.fixtures[0]["home_score"] = 2
        self.fixtures[0]["away_score"] = 1

        save_tournament(self.test_file, self.teams, self.fixtures)
        loaded = load_tournament(self.test_file)

        self.assertEqual(loaded["schema_version"], 1)
        self.assertEqual(len(loaded["teams"]), 4)
        self.assertEqual(len(loaded["fixtures"]), 6)
        self.assertEqual(loaded["teams"][0]["id"], "TM001")
        self.assertEqual(loaded["teams"][0]["name"], "Thunder")

        # Check played match preserved
        self.assertEqual(loaded["fixtures"][0]["id"], "M001")
        self.assertEqual(loaded["fixtures"][0]["status"], "played")
        self.assertEqual(loaded["fixtures"][0]["home_score"], 2)
        self.assertEqual(loaded["fixtures"][0]["away_score"], 1)

    def test_scenario_14_reject_bad_reference_without_state_change(self):
        """Scenario 14: Fixture referencing an unknown team ID is rejected."""
        # Create a payload where fixture references phantom team TM999
        corrupt_fixtures = [dict(f) for f in self.fixtures]
        corrupt_fixtures[0]["away_id"] = "TM999"

        payload = {
            "schema_version": 1,
            "teams": self.teams,
            "fixtures": corrupt_fixtures,
        }
        with open(self.test_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        # In-memory original state
        original_teams_len = len(self.teams)

        with self.assertRaises(StorageError) as ctx:
            load_tournament(self.test_file)

        self.assertIn("unknown away team ID: 'TM999'", str(ctx.exception))
        # Ensure caller's state is completely unchanged
        self.assertEqual(len(self.teams), original_teams_len)

    def test_reject_unsupported_schema_version(self):
        """Reject unsupported schema versions."""
        payload = {
            "schema_version": 99,
            "teams": self.teams,
            "fixtures": self.fixtures,
        }
        with open(self.test_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        with self.assertRaises(StorageError) as ctx:
            load_tournament(self.test_file)
        self.assertIn("Unsupported schema version: 99", str(ctx.exception))

    def test_reject_missing_required_keys(self):
        """Reject missing schema_version, teams, or fixtures."""
        payload = {"teams": self.teams, "fixtures": self.fixtures}
        with open(self.test_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        with self.assertRaises(StorageError) as ctx:
            load_tournament(self.test_file)
        self.assertIn("Missing required key: 'schema_version'", str(ctx.exception))

    def test_reject_boolean_scores_in_storage(self):
        """Boolean scores (e.g. True/False) must be rejected because bool is not a valid score."""
        corrupt_fixtures = [dict(f) for f in self.fixtures]
        corrupt_fixtures[0]["status"] = "played"
        corrupt_fixtures[0]["home_score"] = True  # In Python, isinstance(True, int) is True!
        corrupt_fixtures[0]["away_score"] = 0

        payload = {
            "schema_version": 1,
            "teams": self.teams,
            "fixtures": corrupt_fixtures,
        }
        with open(self.test_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        with self.assertRaises(StorageError) as ctx:
            load_tournament(self.test_file)
        self.assertIn("must have non-negative integer scores (not boolean/float)", str(ctx.exception))

    def test_reject_negative_scores_in_storage(self):
        """Negative scores must be rejected."""
        corrupt_fixtures = [dict(f) for f in self.fixtures]
        corrupt_fixtures[0]["status"] = "played"
        corrupt_fixtures[0]["home_score"] = -1
        corrupt_fixtures[0]["away_score"] = 2

        payload = {
            "schema_version": 1,
            "teams": self.teams,
            "fixtures": corrupt_fixtures,
        }
        with open(self.test_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        with self.assertRaises(StorageError) as ctx:
            load_tournament(self.test_file)
        self.assertIn("must have non-negative integer scores", str(ctx.exception))

    def test_reject_duplicate_team_id_in_file(self):
        """Duplicate team IDs in file should raise StorageError."""
        bad_teams = [
            {"id": "TM001", "name": "Team A"},
            {"id": "TM001", "name": "Team B"},
        ]
        payload = {"schema_version": 1, "teams": bad_teams, "fixtures": []}
        with open(self.test_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        with self.assertRaises(StorageError) as ctx:
            load_tournament(self.test_file)
        self.assertIn("Duplicate team ID detected", str(ctx.exception))

    def test_reject_duplicate_fixture_id_in_file(self):
        """Duplicate fixture IDs should be rejected."""
        bad_fixtures = [
            {"id": "M001", "home_id": "TM001", "away_id": "TM002", "status": "pending", "home_score": None, "away_score": None},
            {"id": "M001", "home_id": "TM001", "away_id": "TM003", "status": "pending", "home_score": None, "away_score": None},
        ]
        payload = {"schema_version": 1, "teams": self.teams, "fixtures": bad_fixtures}
        with open(self.test_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        with self.assertRaises(StorageError) as ctx:
            load_tournament(self.test_file)
        self.assertIn("Duplicate fixture ID detected", str(ctx.exception))

    def test_reject_nonexistent_file(self):
        """Non-existent file path should raise StorageError."""
        ghost_path = Path(self.temp_dir.name) / "ghost.json"
        with self.assertRaises(StorageError) as ctx:
            load_tournament(ghost_path)
        self.assertIn("not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
