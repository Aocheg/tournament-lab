"""Fixture generation, scheduling, and match result recording logic for TournamentLab."""

from typing import Any, Optional
from tournament.exceptions import DuplicateError, NotFoundError, ValidationError
from tournament.models import (
    MAX_TEAMS,
    MIN_TEAMS,
    STATUS_PENDING,
    STATUS_PLAYED,
    is_strict_non_negative_int,
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
    if not isinstance(fixture_id, str):
        return None
    target = fixture_id.strip().upper()
    for fix in fixtures:
        if fix.get("id", "").upper() == target:
            return fix
    return None


def record_result(
    fixtures: list[dict],
    fixture_id: str,
    home_score: Any,
    away_score: Any,
) -> dict:
    """Safely and atomically record a match result for a pending fixture.

    Rules:
    - Fixture must exist; otherwise raises NotFoundError.
    - Fixture must be in 'pending' status; duplicate submissions raise DuplicateError.
    - Both scores must be strictly non-negative integers (booleans, floats, strings rejected).
    - Validate-before-mutate: If validation fails, no fixture state is altered.
    """
    fixture = find_fixture_by_id(fixtures, fixture_id)
    if fixture is None:
        raise NotFoundError(f"Fixture with ID '{fixture_id}' not found.")

    if fixture["status"] == STATUS_PLAYED:
        raise DuplicateError(
            f"Fixture '{fixture['id']}' has already been played ({fixture['home_score']}-{fixture['away_score']}). "
            "Scores cannot be overwritten without an explicit reset."
        )

    if not is_strict_non_negative_int(home_score) or not is_strict_non_negative_int(away_score):
        raise ValidationError(
            f"Invalid score: both scores must be non-negative integers (not booleans or floats). "
            f"Got home={home_score!r} ({type(home_score).__name__}), away={away_score!r} ({type(away_score).__name__})."
        )

    # Atomic update
    fixture["home_score"] = home_score
    fixture["away_score"] = away_score
    fixture["status"] = STATUS_PLAYED

    return fixture
