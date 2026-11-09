"""Team registration and validation logic for TournamentLab."""

from typing import Any, Optional
from tournament.exceptions import DuplicateError, ValidationError
from tournament.models import MAX_TEAMS, MAX_TEAM_NAME_LEN, MIN_TEAM_NAME_LEN


def validate_team_name(name: Any, existing_teams: Optional[list[dict]] = None) -> str:
    """Validate a team name and return the trimmed name.

    Rules:
    - Must be a string.
    - Trimmed length must be between 2 and 30 characters inclusive.
    - Must be case-insensitively unique among existing teams.
    """
    if not isinstance(name, str):
        raise ValidationError(f"Team name must be a string, got {type(name).__name__}.")

    trimmed = name.strip()
    if len(trimmed) < MIN_TEAM_NAME_LEN:
        raise ValidationError(
            f"Team name '{trimmed}' is too short; minimum length is {MIN_TEAM_NAME_LEN} characters."
        )
    if len(trimmed) > MAX_TEAM_NAME_LEN:
        raise ValidationError(
            f"Team name '{trimmed}' is too long; maximum length is {MAX_TEAM_NAME_LEN} characters."
        )

    if existing_teams:
        normalized = trimmed.casefold()
        for team in existing_teams:
            if team.get("name", "").strip().casefold() == normalized:
                raise DuplicateError(
                    f"Team name '{trimmed}' already registered (case-insensitive match with '{team['name']}')."
                )

    return trimmed


def generate_team_id(existing_teams: list[dict]) -> str:
    """Generate the next sequential unique team ID, e.g. TM001, TM002."""
    existing_ids = {t["id"] for t in existing_teams if "id" in t}
    counter = 1
    while True:
        candidate = f"TM{counter:03d}"
        if candidate not in existing_ids:
            return candidate
        counter += 1


def register_team(teams: list[dict], raw_name: str) -> dict:
    """Register a new team with a unique ID and trimmed name.

    Appends the new team dict to the provided teams list and returns it.
    Enforces maximum team limit (8 teams).
    """
    if len(teams) >= MAX_TEAMS:
        raise ValidationError(f"Maximum league capacity reached ({MAX_TEAMS} teams).")

    clean_name = validate_team_name(raw_name, existing_teams=teams)
    team_id = generate_team_id(teams)
    new_team = {"id": team_id, "name": clean_name}
    teams.append(new_team)
    return new_team


def find_team_by_id(teams: list[dict], team_id: str) -> Optional[dict]:
    """Find and return a team dict by its stable ID."""
    for team in teams:
        if team.get("id") == team_id:
            return team
    return None
