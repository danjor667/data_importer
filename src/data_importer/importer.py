"""The import service: the coordinator that ties the pipeline together.

:class:`ImportService` streams rows from a parser, validates each into a
:class:`~data_importer.models.User`, and adds it to a repository. Its defining
job is *resilience*: a per-row :class:`~data_importer.exceptions.RecordError`
(an invalid or duplicate row) is logged and skipped so the import continues,
while fatal errors (a missing source file, a failed write) propagate to abort
the run. It depends only on abstractions, so it can be tested in isolation.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from data_importer.exceptions import RecordError
from data_importer.models import User
from data_importer.parser import RawRecord
from data_importer.repository import UserRepository

logger = logging.getLogger(__name__)


class RecordSource(Protocol):
    """Anything that can stream raw records from a source path."""

    def parse(self, source: Path) -> Iterator[RawRecord]:
        """Yield each raw record read from ``source``."""
        ...


class RecordValidator(Protocol):
    """Anything that can turn a raw record into a validated user."""

    def to_user(self, record: RawRecord) -> User:
        """Return the validated :class:`User` for ``record``."""
        ...


@dataclass(frozen=True)
class ImportReport:
    """The outcome of an import run."""

    imported: int
    skipped: int

    @property
    def total(self) -> int:
        """Total number of data rows processed."""
        return self.imported + self.skipped


class ImportService:
    """Coordinates parsing, validation, and storage of user records."""

    def __init__(
        self,
        parser: RecordSource,
        validator: RecordValidator,
        repository: UserRepository,
    ) -> None:
        """Wire the service to its collaborators.

        Args:
            parser: Source of raw records.
            validator: Turns raw records into validated users.
            repository: Store the validated users are added to.
        """
        self._parser = parser
        self._validator = validator
        self._repository = repository

    def run(self, source: Path) -> ImportReport:
        """Import every user row from ``source`` into the repository.

        Invalid or duplicate rows are logged and skipped; the repository is
        saved once all rows have been processed successfully.

        Args:
            source: Path to the CSV file to import.

        Returns:
            An :class:`ImportReport` summarising the run.

        Raises:
            SourceFileError: If the source file is missing or malformed.
            RepositoryError: If persisting the repository fails.
        """
        imported = 0
        skipped = 0
        for record in self._parser.parse(source):
            try:
                user = self._validator.to_user(record)
                self._repository.add(user)
            except RecordError as error:
                self._log_skip(record, error)
                skipped += 1
            else:
                imported += 1
        self._repository.save()
        logger.info("Import complete: %d imported, %d skipped.", imported, skipped)
        return ImportReport(imported=imported, skipped=skipped)

    def _log_skip(self, record: RawRecord, error: RecordError) -> None:
        """Log a skipped row, ensuring the error carries its row number.

        Args:
            record: The raw record that could not be imported.
            error: The reason the record was rejected.
        """
        if error.row_number is None:
            error.row_number = record.row_number
        logger.warning("Skipping row %d: %s", record.row_number, error)
