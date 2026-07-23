"""Structured logging configuration for the data importer."""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(level: str | int = "INFO") -> None:
    """Configure root logging with a single structured stream handler.

    Safe to call more than once; each call reconfigures the handlers.

    Args:
        level: Logging level, as a name (e.g. ``"INFO"``) or numeric value.
    """
    logging.basicConfig(
        level=level,
        format=_LOG_FORMAT,
        datefmt=_DATE_FORMAT,
        force=True,
    )
