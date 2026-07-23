"""Tests for the domain model: UserId, Email, and User value objects."""

import dataclasses

import pytest

from data_importer.exceptions import ValidationError
from data_importer.models import Email, User, UserId


class TestUserId:
    def test_wraps_a_non_empty_value(self) -> None:
        assert UserId("u-1").value == "u-1"

    def test_strips_surrounding_whitespace(self) -> None:
        assert UserId("  u-1  ").value == "u-1"

    @pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
    def test_rejects_blank_values(self, raw: str) -> None:
        with pytest.raises(ValidationError):
            UserId(raw)

    def test_is_immutable(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            UserId("u-1").value = "u-2"  # type: ignore[misc]


class TestEmail:
    @pytest.mark.parametrize(
        "raw",
        [
            "user@example.com",
            "first.last+tag@sub.example.co",
            "a@b.io",
        ],
    )
    def test_accepts_valid_addresses(self, raw: str) -> None:
        assert Email(raw).value == raw

    def test_strips_surrounding_whitespace(self) -> None:
        assert Email("  user@example.com  ").value == "user@example.com"

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "no-at-sign",
            "@no-local.com",
            "no-domain@",
            "no-tld@example",
            "spaces in@example.com",
            "double@@example.com",
        ],
    )
    def test_rejects_invalid_addresses(self, raw: str) -> None:
        with pytest.raises(ValidationError):
            Email(raw)

    def test_is_immutable(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            Email("user@example.com").value = "other@example.com"  # type: ignore[misc]


class TestUser:
    def _build(self, name: str = "Ada Lovelace") -> User:
        return User(UserId("u-1"), name, Email("ada@example.com"))

    def test_bundles_identity_name_and_email(self) -> None:
        user = self._build()
        assert user.user_id == UserId("u-1")
        assert user.name == "Ada Lovelace"
        assert user.email == Email("ada@example.com")

    def test_strips_surrounding_whitespace_from_name(self) -> None:
        assert self._build(name="  Ada  ").name == "Ada"

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_rejects_blank_name(self, blank: str) -> None:
        with pytest.raises(ValidationError):
            self._build(name=blank)

    def test_equal_users_are_equal_and_hashable(self) -> None:
        assert self._build() == self._build()
        assert len({self._build(), self._build()}) == 1

    def test_is_immutable(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            self._build().name = "Grace"  # type: ignore[misc]
