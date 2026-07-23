"""Custom exception hierarchy for the data importer.

All errors raised by the importer derive from :class:`ImporterError`, so callers
can catch the importer's failures distinctly from unexpected bugs. The hierarchy
splits *fatal* problems that abort a run (:class:`SourceFileError`,
:class:`RepositoryError`) from per-row problems that let the import continue by
skipping the offending row (:class:`RecordError`).
"""

from __future__ import annotations


class ImporterError(Exception):
    """Base class for every error raised by the importer."""


class SourceFileError(ImporterError):
    """A problem with the source CSV file that aborts the import."""


class SourceFileNotFoundError(SourceFileError):
    """The source CSV file does not exist or cannot be opened."""


class FileFormatError(SourceFileError):
    """The source CSV is structurally invalid (e.g. a missing header)."""


class RecordError(ImporterError):
    """A problem with a single record that lets the import skip and continue.

    Args:
        message: Human-readable description of the problem.
        row_number: 1-based row the problem relates to, when known. Left as
            ``None`` when raised in a context without row information (for
            example while constructing a value object).
    """

    def __init__(self, message: str, *, row_number: int | None = None) -> None:
        super().__init__(message)
        self.row_number = row_number


class ValidationError(RecordError):
    """A record failed validation (e.g. an invalid email or empty name)."""


class DuplicateUserError(RecordError):
    """A record's user id already exists in the repository.

    Args:
        user_id: The colliding user id.
        row_number: 1-based row the duplicate appeared on, when known.
    """

    def __init__(self, user_id: str, *, row_number: int | None = None) -> None:
        super().__init__(f"Duplicate user id: {user_id!r}", row_number=row_number)
        self.user_id = user_id


class RepositoryError(ImporterError):
    """The storage layer failed to read or persist data."""
