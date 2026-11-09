"""Fixture generation and scheduling logic for TournamentLab."""

from typing import Optional
from tournament.exceptions import ValidationError
from tournament.models import (
    MAX_TEAMS,
    MIN_TEAMS,
    STATUS_PENDING,
)


def calculate_expected_fixture_count(n: int) -> int:
    """Calculate the number of round-robin fixtures for N teams: N * (N - 1) // 2."""
    if n < 0:
        return 0
    return n * (n - 1) // 2


def generate_schedule(teams: list[dict]) -> list[dict]:
    """Generate a fair, deterministic single round-robin schedule.

    Every distinct pair meets once; each team plays exactly N - 1 matches.
    Constraints:
    - 4 to 8 teams must be registered.
    - Unique unordered pairs only (no self-matches, no reverse duplicates).
    - Fixture IDs are deterministically formatted as M001, M002, etc.
    """
    n = len(teams)
    if n < MIN_TEAMS:
        raise ValidationError(
            f"Cannot generate fixtures: league requires at least {MIN_TEAMS} teams, but only {n} registered."
        )
    if n > MAX_TEAMS:
        raise ValidationError(
            f"Cannot generate fixtures: league allows at most {MAX_TEAMS} teams, but {n} registered."
        )

    fixtures: list[dict] = []
    fixture_id_counter = 1

    # Deterministic round-robin generation: all unique unordered pairs
    for i in range(n):
        for j in range(i + 1, n):
            home_team = teams[i]
            away_team = teams[j]

            fixture = {
                "id": f"M{fixture_id_counter:03d}",
                "home_id": home_team["id"],
                "away_id": away_team["id"],
                "status": STATUS_PENDING,
                "home_score": None,
                "away_score": None,
            }
            fixtures.append(fixture)
            fixture_id_counter += 1

    return fixtures


def find_fixture_by_id(fixtures: list[dict], fixture_id: str) -> Optional[dict]:
    """Find and return a fixture dict by its match ID (case-insensitive lookup)."""
    target = fixture_id.strip().upper()
    for fix in fixtures:
        if fix.get("id", "").upper() == target:
            return fix
    return None
