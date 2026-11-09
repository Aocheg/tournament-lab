"""Reproducible, seeded simulation of demo fixtures for TournamentLab."""

import random
from tournament.fixtures import record_result
from tournament.models import STATUS_PENDING


def simulate_demo_fixtures(fixtures: list[dict], seed: int = 42) -> int:
    """Simulate results for remaining pending fixtures using a reproducible seed.

    Rules:
    - Only pending fixtures are simulated.
    - Already completed matches are never overwritten.
    - Uses an explicit seed to ensure reproducible, deterministic results.
    - Returns the count of fixtures simulated.
    """
    rng = random.Random(seed)
    pending = [f for f in fixtures if f.get("status") == STATUS_PENDING]
    simulated_count = 0

    for fix in pending:
        # Realistic score generation: 0-4 goals
        home_score = rng.randint(0, 4)
        away_score = rng.randint(0, 4)
        record_result(fixtures, fix["id"], home_score, away_score)
        simulated_count += 1

    return simulated_count
