"""Standings computation, tie-break ranking, and champion determination."""

from typing import Optional
from tournament.exceptions import ValidationError
from tournament.models import (
    POINTS_DRAW,
    POINTS_WIN,
    STATUS_PLAYED,
    is_strict_non_negative_int,
)


def compute_standings(teams: list[dict], fixtures: list[dict]) -> list[dict]:
    """Compute league standings dynamically from the source of truth (played fixtures).

    Standings are never stored as mutable parallel state; they are always derived on demand.

    Columns computed per team:
    - rank: 1-indexed league position
    - team_id: stable identifier
    - name: display name
    - played: total matches completed
    - won: count of wins (awarded 3 points)
    - drawn: count of draws (awarded 1 point each)
    - lost: count of losses (awarded 0 points)
    - goals_for: total goals scored
    - goals_against: total goals conceded
    - goal_difference: goals_for - goals_against
    - points: 3 * won + 1 * drawn

    Tie-break ranking order (lexicographic multi-key):
    1. Points descending
    2. Goal difference descending
    3. Goals for descending
    4. Normalized team name ascending (casefolded alphabetical)
    """
    # Initialize zeroed record for all registered teams
    table: dict[str, dict] = {}
    for team in teams:
        t_id = team["id"]
        table[t_id] = {
            "team_id": t_id,
            "name": team["name"],
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 0,
        }

    # Aggregate stats over canonical played fixtures
    for fix in fixtures:
        if fix.get("status") != STATUS_PLAYED:
            continue

        home_id = fix["home_id"]
        away_id = fix["away_id"]
        h_score = fix["home_score"]
        a_score = fix["away_score"]

        if not is_strict_non_negative_int(h_score) or not is_strict_non_negative_int(a_score):
            raise ValidationError(
                f"Cannot compute standings: fixture {fix.get('id')} has invalid score ({h_score!r}, {a_score!r})."
            )

        if home_id not in table or away_id not in table:
            raise ValidationError(
                f"Cannot compute standings: fixture {fix.get('id')} references unregistered team."
            )

        home_row = table[home_id]
        away_row = table[away_id]

        home_row["played"] += 1
        away_row["played"] += 1

        home_row["goals_for"] += h_score
        home_row["goals_against"] += a_score

        away_row["goals_for"] += a_score
        away_row["goals_against"] += h_score

        if h_score > a_score:
            home_row["won"] += 1
            home_row["points"] += POINTS_WIN
            away_row["lost"] += 1
        elif h_score < a_score:
            away_row["won"] += 1
            away_row["points"] += POINTS_WIN
            home_row["lost"] += 1
        else:
            home_row["drawn"] += 1
            home_row["points"] += POINTS_DRAW
            away_row["drawn"] += 1
            away_row["points"] += POINTS_DRAW

    # Calculate goal differences
    for row in table.values():
        row["goal_difference"] = row["goals_for"] - row["goals_against"]

    # Sort using lexicographic multi-key tie-break
    sorted_rows = sorted(
        table.values(),
        key=lambda r: (
            -r["points"],
            -r["goal_difference"],
            -r["goals_for"],
            r["name"].strip().casefold(),
        ),
    )

    # Assign 1-indexed ranks
    for rank_idx, row in enumerate(sorted_rows, start=1):
        row["rank"] = rank_idx

    return sorted_rows


def verify_league_invariants(standings: list[dict], fixtures: list[dict]) -> tuple[bool, str]:
    """Verify mathematical integrity invariants across all played matches:

    1. Total League Points == 3 * (non-draw matches) + 2 * (draw matches)
    2. Total Goals For == Total Goals Against
    3. For every team: played == won + drawn + lost
    4. For every team: goal_difference == goals_for - goals_against
    5. For every team: points == 3 * won + drawn
    """
    played_fixtures = [f for f in fixtures if f.get("status") == STATUS_PLAYED]
    draws_count = sum(1 for f in played_fixtures if f["home_score"] == f["away_score"])
    non_draws_count = len(played_fixtures) - draws_count
    expected_total_points = 3 * non_draws_count + 2 * draws_count

    actual_total_points = sum(r["points"] for r in standings)
    if actual_total_points != expected_total_points:
        return (
            False,
            f"Point invariant violated: expected {expected_total_points} total pts, got {actual_total_points}",
        )

    total_gf = sum(r["goals_for"] for r in standings)
    total_ga = sum(r["goals_against"] for r in standings)
    if total_gf != total_ga:
        return False, f"Goal balance invariant violated: total GF ({total_gf}) != total GA ({total_ga})"

    for r in standings:
        if r["played"] != r["won"] + r["drawn"] + r["lost"]:
            return False, f"Match count invariant violated for team {r['team_id']}"
        if r["goal_difference"] != r["goals_for"] - r["goals_against"]:
            return False, f"GD invariant violated for team {r['team_id']}"
        if r["points"] != (r["won"] * POINTS_WIN + r["drawn"] * POINTS_DRAW):
            return False, f"Point formula invariant violated for team {r['team_id']}"

    return True, "All invariants verified."


def get_season_status(fixtures: list[dict]) -> str:
    """Return status: 'no_fixtures', 'in_progress', or 'completed'."""
    if not fixtures:
        return "no_fixtures"
    if all(f.get("status") == STATUS_PLAYED for f in fixtures):
        return "completed"
    return "in_progress"


def get_champion(teams: list[dict], fixtures: list[dict]) -> tuple[Optional[dict], str]:
    """Return the champion team dict and status message if season is complete.

    If any fixture is pending or no fixtures exist, champion is None and
    status is 'in_progress' or 'no_fixtures'.
    """
    status = get_season_status(fixtures)
    if status == "no_fixtures":
        return None, "No fixtures have been generated yet."
    if status == "in_progress":
        played_count = sum(1 for f in fixtures if f.get("status") == STATUS_PLAYED)
        total_count = len(fixtures)
        return (
            None,
            f"Season in progress ({played_count}/{total_count} matches played). Standings are provisional.",
        )

    standings = compute_standings(teams, fixtures)
    if not standings:
        return None, "No registered teams found."

    champion = standings[0]
    return champion, f"Champion: {champion['name']} (Rank #1, {champion['points']} PTS, GD: {champion['goal_difference']})"
