"""Shared pytest fixtures for the data_importer test suite.

Feature-specific fixtures (temporary CSV files, in-memory repositories, mock
storage) are added alongside their features. This module is the common home for
fixtures reused across multiple test modules.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

CsvFactory = Callable[[str], Path]


@pytest.fixture
def make_csv(tmp_path: Path) -> CsvFactory:
    """Return a factory that writes CSV content to a temporary file.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        A callable that takes CSV text and returns the path it was written to.
    """

    def _write(content: str) -> Path:
        path = tmp_path / "users.csv"
        path.write_text(content, encoding="utf-8")
        return path

    return _write
