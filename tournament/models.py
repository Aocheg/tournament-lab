"""Domain constants, types, and validation helpers for TournamentLab."""

from typing import Any

# Domain constants
MIN_TEAMS: int = 4
MAX_TEAMS: int = 8
MIN_TEAM_NAME_LEN: int = 2
MAX_TEAM_NAME_LEN: int = 30

STATUS_PENDING: str = "pending"
STATUS_PLAYED: str = "played"
VALID_STATUSES: set[str] = {STATUS_PENDING, STATUS_PLAYED}

POINTS_WIN: int = 3
POINTS_DRAW: int = 1
POINTS_LOSS: int = 0

SCHEMA_VERSION: int = 1


def is_strict_non_negative_int(val: Any) -> bool:
    """Strictly verify if a value is a non-negative integer.

    In Python, bool is a subclass of int (isinstance(True, int) == True).
    This function explicitly rejects booleans, floats, strings, None, and negative numbers.
    """
    if isinstance(val, bool):
        return False
    if type(val) is not int:
        return False
    return val >= 0
