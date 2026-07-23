"""Command-line interface for the data importer.

This module is the composition root: it parses arguments, configures logging,
wires the concrete :class:`~data_importer.parser.CsvParser`,
:class:`~data_importer.validation.UserValidator`, and
:class:`~data_importer.repository.JsonUserRepository` into an
:class:`~data_importer.importer.ImportService`, runs the import, and maps the
outcome to a process exit code.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from data_importer.exceptions import ImporterError
from data_importer.importer import ImportReport, ImportService
from data_importer.logging_config import setup_logging
from data_importer.parser import CsvParser
from data_importer.repository import JsonUserRepository
from data_importer.validation import UserValidator

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_SKIPPED = 1
EXIT_FATAL = 2

_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the importer as a command-line program.

    Args:
        argv: Command-line arguments, excluding the program name. Defaults to
            ``sys.argv`` when ``None``.

    Returns:
        ``0`` if every row imported, ``1`` if some rows were skipped, ``2`` if
        the run failed fatally.
    """
    args = _parse_args(argv)
    setup_logging(args.log_level)

    try:
        repository = JsonUserRepository(args.db)
        service = ImportService(CsvParser(), UserValidator(), repository)
        report = service.run(args.source)
    except ImporterError as error:
        logger.error("Import failed: %s", error)
        return EXIT_FATAL

    _print_report(report)
    return EXIT_SKIPPED if report.skipped else EXIT_OK


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Arguments to parse, excluding the program name.

    Returns:
        The parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="data-importer",
        description="Import users from a CSV file into a JSON database.",
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to the source CSV file.",
    )
    parser.add_argument(
        "--db",
        required=True,
        type=Path,
        help="Path to the JSON database file (created if absent).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=_LOG_LEVELS,
        help="Logging verbosity (default: INFO).",
    )
    return parser.parse_args(argv)


def _print_report(report: ImportReport) -> None:
    """Print a human-readable summary of the import.

    Args:
        report: The outcome of the import run.
    """
    print(
        f"Import finished: {report.imported} imported, "
        f"{report.skipped} skipped, {report.total} row(s) processed."
    )
