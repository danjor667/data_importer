"""Tests for the record validator."""

import pytest

from data_importer.exceptions import ValidationError
from data_importer.models import Email, User, UserId
from data_importer.parser import RawRecord
from data_importer.validation import UserValidator


def build_record(
    *,
    row_number: int = 2,
    user_id: str = "u-1",
    name: str = "Ada Lovelace",
    email: str = "ada@example.com",
) -> RawRecord:
    return RawRecord(
        row_number=row_number,
        values={"user_id": user_id, "name": name, "email": email},
    )


class TestValidRecords:
    def test_builds_a_user_from_a_valid_record(self) -> None:
        user = UserValidator().to_user(build_record())
        assert user == User(UserId("u-1"), "Ada Lovelace", Email("ada@example.com"))

    def test_normalises_whitespace_via_value_objects(self) -> None:
        record = build_record(user_id="  u-1 ", name="  Ada  ", email=" ada@x.io ")
        user = UserValidator().to_user(record)
        assert user.user_id == UserId("u-1")
        assert user.name == "Ada"
        assert user.email == Email("ada@x.io")


class TestInvalidRecords:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("user_id", ""),
            ("user_id", "   "),
            ("name", ""),
            ("name", "  "),
            ("email", ""),
            ("email", "not-an-email"),
            ("email", "missing-domain@"),
        ],
    )
    def test_invalid_field_raises_validation_error(
        self, field: str, value: str
    ) -> None:
        values = {"user_id": "u-1", "name": "Ada Lovelace", "email": "ada@x.io"}
        values[field] = value
        record = RawRecord(row_number=2, values=values)
        with pytest.raises(ValidationError):
            UserValidator().to_user(record)

    def test_error_carries_the_records_row_number(self) -> None:
        record = build_record(row_number=9, email="not-an-email")
        with pytest.raises(ValidationError) as exc_info:
            UserValidator().to_user(record)
        assert exc_info.value.row_number == 9

    def test_missing_column_is_treated_as_a_validation_error(self) -> None:
        record = RawRecord(row_number=4, values={"user_id": "u-1", "name": "Ada"})
        with pytest.raises(ValidationError) as exc_info:
            UserValidator().to_user(record)
        assert exc_info.value.row_number == 4
