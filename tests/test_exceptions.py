"""Tests for the custom exception hierarchy."""

import pytest

from data_importer.exceptions import (
    DuplicateUserError,
    FileFormatError,
    ImporterError,
    RecordError,
    RepositoryError,
    SourceFileError,
    SourceFileNotFoundError,
    ValidationError,
)


class TestHierarchy:
    """Every custom exception must derive from ImporterError."""

    @pytest.mark.parametrize(
        "error_type",
        [
            SourceFileError,
            SourceFileNotFoundError,
            FileFormatError,
            RecordError,
            ValidationError,
            DuplicateUserError,
            RepositoryError,
        ],
    )
    def test_all_errors_derive_from_importer_error(
        self, error_type: type[ImporterError]
    ) -> None:
        assert issubclass(error_type, ImporterError)

    def test_source_file_errors_group_under_source_file_error(self) -> None:
        assert issubclass(SourceFileNotFoundError, SourceFileError)
        assert issubclass(FileFormatError, SourceFileError)

    def test_record_errors_group_under_record_error(self) -> None:
        assert issubclass(ValidationError, RecordError)
        assert issubclass(DuplicateUserError, RecordError)

    def test_catching_importer_error_catches_a_subclass(self) -> None:
        with pytest.raises(ImporterError):
            raise ValidationError("bad row")


class TestRecordError:
    """RecordError carries the row it relates to, so callers can report it."""

    def test_row_number_defaults_to_none(self) -> None:
        error = RecordError("something went wrong")
        assert error.row_number is None

    def test_row_number_is_retained_when_provided(self) -> None:
        error = ValidationError("invalid email", row_number=7)
        assert error.row_number == 7

    def test_message_is_accessible_via_str(self) -> None:
        assert str(RecordError("boom")) == "boom"


class TestDuplicateUserError:
    """DuplicateUserError records which user id collided."""

    def test_retains_user_id(self) -> None:
        error = DuplicateUserError("u-123", row_number=3)
        assert error.user_id == "u-123"
        assert error.row_number == 3

    def test_message_mentions_the_user_id(self) -> None:
        assert "u-123" in str(DuplicateUserError("u-123"))
