"""Tests for logging configuration."""

import logging

from data_importer.logging_config import setup_logging


def test_sets_the_root_log_level() -> None:
    setup_logging("WARNING")
    assert logging.getLogger().level == logging.WARNING


def test_is_reconfigurable_across_calls() -> None:
    setup_logging("INFO")
    setup_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_installs_a_formatter_handler() -> None:
    setup_logging("INFO")
    handlers = logging.getLogger().handlers
    assert handlers
    assert handlers[0].formatter is not None
