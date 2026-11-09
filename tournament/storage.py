"""Persistence layer for TournamentLab with strict schema and integrity validation."""

import json
from pathlib import Path
from typing import Any, Union
from tournament.exceptions import StorageError
from tournament.models import (
    MAX_TEAMS,
    MAX_TEAM_NAME_LEN,
    MIN_TEAM_NAME_LEN,
    SCHEMA_VERSION,
    STATUS_PENDING,
    STATUS_PLAYED,
    VALID_STATUSES,
    is_strict_non_negative_int,
)


def validate_tournament_data(data: Any) -> dict:
    """Validate tournament payload strictly against schema and referential integrity rules.

    Raises StorageError on any inconsistency.
    Returns a clean, validated dictionary: {"schema_version": 1, "teams": [...], "fixtures": [...]}.
    """
    if not isinstance(data, dict):
        raise StorageError("Invalid file structure: top-level JSON must be an object.")

    # Check top-level keys
    for req_key in ("schema_version", "teams", "fixtures"):
        if req_key not in data:
            raise StorageError(f"Missing required key: '{req_key}'.")

    if data["schema_version"] != SCHEMA_VERSION:
        raise StorageError(
            f"Unsupported schema version: {data['schema_version']}. Expected {SCHEMA_VERSION}."
        )

    teams_raw = data["teams"]
    fixtures_raw = data["fixtures"]

    if not isinstance(teams_raw, list):
        raise StorageError("'teams' field must be a list.")
    if not isinstance(fixtures_raw, list):
        raise StorageError("'fixtures' field must be a list.")

    # Validate teams
    if len(teams_raw) > MAX_TEAMS:
        raise StorageError(f"Exceeded maximum team limit of {MAX_TEAMS} (found {len(teams_raw)}).")

    validated_teams: list[dict] = []
    seen_team_ids: set[str] = set()
    seen_normalized_names: set[str] = set()

    for idx, team in enumerate(teams_raw):
        if not isinstance(team, dict):
            raise StorageError(f"Team at index {idx} must be an object.")

        if "id" not in team or "name" not in team:
            raise StorageError(f"Team at index {idx} missing 'id' or 'name'.")

        team_id = team["id"]
        team_name = team["name"]

        if not isinstance(team_id, str) or not team_id.strip():
            raise StorageError(f"Invalid team ID at index {idx}: must be non-empty string.")

        team_id = team_id.strip()
        if team_id in seen_team_ids:
            raise StorageError(f"Duplicate team ID detected: '{team_id}'.")
        seen_team_ids.add(team_id)

        if not isinstance(team_name, str):
            raise StorageError(f"Team name for ID '{team_id}' must be a string.")

        clean_name = team_name.strip()
        if len(clean_name) < MIN_TEAM_NAME_LEN or len(clean_name) > MAX_TEAM_NAME_LEN:
            raise StorageError(
                f"Team name '{clean_name}' must be between {MIN_TEAM_NAME_LEN} and {MAX_TEAM_NAME_LEN} characters."
            )

        norm_name = clean_name.casefold()
        if norm_name in seen_normalized_names:
            raise StorageError(f"Duplicate team name detected: '{clean_name}' (case-insensitive).")
        seen_normalized_names.add(norm_name)

        validated_teams.append({"id": team_id, "name": clean_name})

    # Validate fixtures
    validated_fixtures: list[dict] = []
    seen_fixture_ids: set[str] = set()
    seen_pairs: set[frozenset[str]] = set()

    for idx, fix in enumerate(fixtures_raw):
        if not isinstance(fix, dict):
            raise StorageError(f"Fixture at index {idx} must be an object.")

        required_fix_keys = ("id", "home_id", "away_id", "status", "home_score", "away_score")
        for key in required_fix_keys:
            if key not in fix:
                raise StorageError(f"Fixture at index {idx} missing required key: '{key}'.")

        fix_id = fix["id"]
        home_id = fix["home_id"]
        away_id = fix["away_id"]
        status = fix["status"]
        home_score = fix["home_score"]
        away_score = fix["away_score"]

        if not isinstance(fix_id, str) or not fix_id.strip():
            raise StorageError(f"Invalid fixture ID at index {idx}.")
        fix_id = fix_id.strip()

        if fix_id in seen_fixture_ids:
            raise StorageError(f"Duplicate fixture ID detected: '{fix_id}'.")
        seen_fixture_ids.add(fix_id)

        # Referential integrity checks
        if home_id not in seen_team_ids:
            raise StorageError(
                f"Fixture '{fix_id}' references unknown home team ID: '{home_id}'."
            )
        if away_id not in seen_team_ids:
            raise StorageError(
                f"Fixture '{fix_id}' references unknown away team ID: '{away_id}'."
            )
        if home_id == away_id:
            raise StorageError(f"Fixture '{fix_id}' has identical home and away team: '{home_id}'.")

        pair_key = frozenset([home_id, away_id])
        if pair_key in seen_pairs:
            raise StorageError(
                f"Duplicate unordered team pair detected in fixture '{fix_id}' ({home_id} vs {away_id})."
            )
        seen_pairs.add(pair_key)

        # Status and score integrity
        if status not in VALID_STATUSES:
            raise StorageError(
                f"Fixture '{fix_id}' has invalid status '{status}'. Expected 'pending' or 'played'."
            )

        if status == STATUS_PENDING:
            if home_score is not None or away_score is not None:
                raise StorageError(
                    f"Pending fixture '{fix_id}' must have null scores, got ({home_score}, {away_score})."
                )
        elif status == STATUS_PLAYED:
            if not is_strict_non_negative_int(home_score) or not is_strict_non_negative_int(away_score):
                raise StorageError(
                    f"Played fixture '{fix_id}' must have non-negative integer scores (not boolean/float), "
                    f"got ({home_score!r}, {away_score!r})."
                )

        validated_fixtures.append({
            "id": fix_id,
            "home_id": home_id,
            "away_id": away_id,
            "status": status,
            "home_score": home_score,
            "away_score": away_score,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "teams": validated_teams,
        "fixtures": validated_fixtures,
    }


def save_tournament(filepath: Union[str, Path], teams: list[dict], fixtures: list[dict]) -> None:
    """Save tournament state to a JSON file.

    Validates schema and referential integrity before writing to disk.
    """
    path = Path(filepath)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "teams": teams,
        "fixtures": fixtures,
    }
    # Pre-validate before writing
    clean_data = validate_tournament_data(payload)

    # Write safely with formatting
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=2)


def load_tournament(filepath: Union[str, Path]) -> dict:
    """Load and strictly validate a tournament JSON file.

    Ensures validate-before-mutate: returns a clean dictionary or raises StorageError.
    """
    path = Path(filepath)
    if not path.is_file():
        raise StorageError(f"Tournament file not found: '{filepath}'.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as err:
        raise StorageError(f"Malformed JSON in file '{filepath}': {err}") from err
    except OSError as err:
        raise StorageError(f"Error reading file '{filepath}': {err}") from err

    # Perform strict business and referential integrity validation
    return validate_tournament_data(raw_data)
