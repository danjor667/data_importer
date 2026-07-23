"""Tests for the CSV parser."""

from pathlib import Path

import pytest

from data_importer.exceptions import FileFormatError, SourceFileNotFoundError
from data_importer.parser import CsvParser, RawRecord
from tests.conftest import CsvFactory

VALID_CSV = (
    "user_id,name,email\n"
    "u-1,Ada Lovelace,ada@example.com\n"
    "u-2,Grace Hopper,grace@example.com\n"
)


class TestHappyPath:
    def test_yields_one_record_per_data_row(self, make_csv: CsvFactory) -> None:
        records = list(CsvParser().parse(make_csv(VALID_CSV)))
        assert len(records) == 2

    def test_maps_columns_to_values(self, make_csv: CsvFactory) -> None:
        first = next(iter(CsvParser().parse(make_csv(VALID_CSV))))
        assert first.values == {
            "user_id": "u-1",
            "name": "Ada Lovelace",
            "email": "ada@example.com",
        }

    def test_numbers_rows_from_two_since_header_is_row_one(
        self, make_csv: CsvFactory
    ) -> None:
        records = list(CsvParser().parse(make_csv(VALID_CSV)))
        assert [r.row_number for r in records] == [2, 3]

    def test_preserves_extra_columns_are_ignored_but_required_kept(
        self, make_csv: CsvFactory
    ) -> None:
        content = "user_id,name,email,age\nu-1,Ada,ada@example.com,36\n"
        record = next(iter(CsvParser().parse(make_csv(content))))
        assert record.values["user_id"] == "u-1"
        assert record.values["age"] == "36"


class TestLeniencyOnRaggedRows:
    """Structural reading is lenient; content validation happens downstream."""

    def test_missing_trailing_field_becomes_empty_string(
        self, make_csv: CsvFactory
    ) -> None:
        content = "user_id,name,email\nu-1,Ada\n"
        record = next(iter(CsvParser().parse(make_csv(content))))
        assert record.values["email"] == ""


class TestFileErrors:
    def test_missing_file_raises_source_file_not_found(self, tmp_path: Path) -> None:
        parser = CsvParser()
        with pytest.raises(SourceFileNotFoundError):
            list(parser.parse(tmp_path / "does-not-exist.csv"))

    def test_parse_is_lazy_and_defers_errors_until_iterated(
        self, tmp_path: Path
    ) -> None:
        # Building the iterator must not touch the filesystem yet.
        iterator = CsvParser().parse(tmp_path / "does-not-exist.csv")
        with pytest.raises(SourceFileNotFoundError):
            next(iter(iterator))

    def test_empty_file_raises_file_format_error(self, make_csv: CsvFactory) -> None:
        with pytest.raises(FileFormatError):
            list(CsvParser().parse(make_csv("")))

    @pytest.mark.parametrize(
        "header",
        [
            "name,email",  # no user_id
            "user_id,email",  # no name
            "user_id,name",  # no email
            "a,b,c",  # none of the required columns
        ],
    )
    def test_missing_required_column_raises_file_format_error(
        self, make_csv: CsvFactory, header: str
    ) -> None:
        with pytest.raises(FileFormatError):
            list(CsvParser().parse(make_csv(f"{header}\nx,y,z\n")))


class TestConfigurableColumns:
    def test_accepts_custom_required_columns(self, make_csv: CsvFactory) -> None:
        parser = CsvParser(required_columns=("id", "email"))
        records = list(parser.parse(make_csv("id,email\n1,a@b.io\n")))
        assert records == [
            RawRecord(row_number=2, values={"id": "1", "email": "a@b.io"})
        ]
