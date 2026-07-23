"""Tests for the import service (the coordinator)."""

import logging
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from data_importer.exceptions import (
    DuplicateUserError,
    RepositoryError,
    SourceFileNotFoundError,
)
from data_importer.importer import ImportReport, ImportService
from data_importer.parser import RawRecord
from data_importer.repository import UserRepository
from data_importer.validation import UserValidator


class FakeParser:
    """A parser stand-in that yields fixed records or raises on iteration."""

    def __init__(
        self,
        records: list[RawRecord] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._records = records or []
        self._error = error

    def parse(self, source: Path) -> Iterator[RawRecord]:
        if self._error is not None:
            raise self._error
        yield from self._records


def record(row_number: int, user_id: str, email: str = "a@b.io") -> RawRecord:
    return RawRecord(
        row_number=row_number,
        values={"user_id": user_id, "name": "Ada", "email": email},
    )


def make_service(
    mocker: MockerFixture,
    parser: FakeParser,
) -> tuple[ImportService, MagicMock]:
    repository = mocker.Mock(spec=UserRepository)
    service = ImportService(parser, UserValidator(), repository)
    return service, repository


class TestImportReport:
    def test_total_is_imported_plus_skipped(self) -> None:
        assert ImportReport(imported=3, skipped=2).total == 5


class TestHappyPath:
    def test_imports_every_valid_row(self, mocker: MockerFixture) -> None:
        parser = FakeParser([record(2, "u-1"), record(3, "u-2")])
        service, repository = make_service(mocker, parser)

        report = service.run(Path("users.csv"))

        assert report == ImportReport(imported=2, skipped=0)
        assert repository.add.call_count == 2
        repository.save.assert_called_once()


class TestSkipsBadRows:
    def test_skips_invalid_rows_but_imports_the_rest(
        self, mocker: MockerFixture
    ) -> None:
        parser = FakeParser([record(2, "u-1"), record(3, "u-2", email="not-an-email")])
        service, repository = make_service(mocker, parser)

        report = service.run(Path("users.csv"))

        assert report == ImportReport(imported=1, skipped=1)
        assert repository.add.call_count == 1
        repository.save.assert_called_once()

    def test_skips_duplicate_rows(self, mocker: MockerFixture) -> None:
        parser = FakeParser([record(2, "u-1"), record(3, "u-1")])
        service, repository = make_service(mocker, parser)
        repository.add.side_effect = [None, DuplicateUserError("u-1")]

        report = service.run(Path("users.csv"))

        assert report == ImportReport(imported=1, skipped=1)
        repository.save.assert_called_once()

    def test_logs_a_warning_naming_the_skipped_row(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        parser = FakeParser([record(7, "u-1", email="bad")])
        service, _ = make_service(mocker, parser)

        with caplog.at_level(logging.WARNING):
            service.run(Path("users.csv"))

        assert any("7" in message for message in caplog.messages)


class TestFatalErrorsPropagate:
    def test_source_error_propagates_and_skips_save(
        self, mocker: MockerFixture
    ) -> None:
        parser = FakeParser(error=SourceFileNotFoundError("missing"))
        service, repository = make_service(mocker, parser)

        with pytest.raises(SourceFileNotFoundError):
            service.run(Path("missing.csv"))

        repository.save.assert_not_called()

    def test_repository_save_error_propagates(self, mocker: MockerFixture) -> None:
        parser = FakeParser([record(2, "u-1")])
        service, repository = make_service(mocker, parser)
        repository.save.side_effect = RepositoryError("disk full")

        with pytest.raises(RepositoryError):
            service.run(Path("users.csv"))
