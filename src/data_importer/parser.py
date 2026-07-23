"""CSV parsing for the data importer.

:class:`CsvParser` reads a CSV file and yields one :class:`RawRecord` per data
row, lazily. It is responsible only for *structure*: it opens the file safely,
checks that the header contains the required columns, and hands each row on as
strings. Deciding whether a row's *content* is valid is left to the validation
layer, so a single malformed row can be skipped rather than aborting the import.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from data_importer.exceptions import FileFormatError, SourceFileNotFoundError

DEFAULT_COLUMNS: tuple[str, ...] = ("user_id", "name", "email")


@dataclass(frozen=True)
class RawRecord:
    """An un-validated CSV data row paired with its 1-based row number.

    The header counts as row 1, so the first data row is row 2. ``values`` maps
    each declared column to its raw string value (missing fields become "").
    """

    row_number: int
    values: dict[str, str]


class CsvParser:
    """Reads user rows from a CSV file, yielding them lazily."""

    def __init__(self, required_columns: Sequence[str] = DEFAULT_COLUMNS) -> None:
        """Create a parser.

        Args:
            required_columns: Column names that must be present in the header.
        """
        self._required_columns = tuple(required_columns)

    def parse(self, path: Path) -> Iterator[RawRecord]:
        """Yield each data row of the CSV file as a :class:`RawRecord`.

        Parsing is lazy: the file is opened and the header validated only once
        iteration begins, and the file stays open until the iterator is
        exhausted.

        Args:
            path: Path to the CSV file to read.

        Yields:
            One :class:`RawRecord` per data row, in file order.

        Raises:
            SourceFileNotFoundError: If the file does not exist.
            FileFormatError: If the file has no header row or is missing a
                required column.
        """
        try:
            handle = path.open(newline="", encoding="utf-8")
        except FileNotFoundError as error:
            raise SourceFileNotFoundError(f"Source file not found: {path}") from error

        with handle:
            reader = csv.DictReader(handle)
            self._validate_header(reader.fieldnames, path)
            columns = reader.fieldnames or []
            for row_number, row in enumerate(reader, start=2):
                values = {column: (row.get(column) or "") for column in columns}
                yield RawRecord(row_number=row_number, values=values)

    def _validate_header(self, fieldnames: Sequence[str] | None, path: Path) -> None:
        """Ensure the header exists and contains every required column.

        Args:
            fieldnames: Column names read from the header, or ``None`` if empty.
            path: Path of the file, used for error messages.

        Raises:
            FileFormatError: If the header is missing or lacks a required column.
        """
        if not fieldnames:
            raise FileFormatError(f"Source file has no header row: {path}")
        missing = [
            column for column in self._required_columns if column not in fieldnames
        ]
        if missing:
            raise FileFormatError(
                f"Source file is missing required column(s): {', '.join(missing)}"
            )
