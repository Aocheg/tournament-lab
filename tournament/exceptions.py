"""Custom exceptions for TournamentLab.

Provides a clean hierarchy for domain-specific errors.
"""


class TournamentError(Exception):
    """Base exception for all TournamentLab errors."""
    pass


class ValidationError(TournamentError):
    """Raised when an entity, parameter, or score fails validation."""
    pass


class DuplicateError(ValidationError):
    """Raised when attempting to add duplicate teams, fixtures, or results."""
    pass


class NotFoundError(TournamentError):
    """Raised when an entity (team or fixture) cannot be found."""
    pass


class StorageError(TournamentError):
    """Raised when saving or loading tournament persistence data fails."""
    pass
