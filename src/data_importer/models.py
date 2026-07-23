"""Domain model for the data importer.

Primitive user attributes are wrapped in small, immutable value objects
(:class:`UserId`, :class:`Email`) that validate themselves on construction, so
an invalid ``User`` cannot exist. Each value object raises
:class:`~data_importer.exceptions.ValidationError` when given a bad value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from data_importer.exceptions import ValidationError

# A pragmatic email check: a non-empty local part, a single "@", and a domain
# that contains a dot. Deliberately not RFC 5322 exhaustive.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class UserId:
    """A non-empty user identifier, stripped of surrounding whitespace."""

    value: str

    def __post_init__(self) -> None:
        """Validate and normalise the identifier.

        Raises:
            ValidationError: If the identifier is empty or whitespace-only.
        """
        stripped = self.value.strip()
        if not stripped:
            raise ValidationError("User id must not be empty.")
        object.__setattr__(self, "value", stripped)


@dataclass(frozen=True)
class Email:
    """A syntactically valid email address, stripped of whitespace."""

    value: str

    def __post_init__(self) -> None:
        """Validate and normalise the email address.

        Raises:
            ValidationError: If the address does not match the expected shape.
        """
        stripped = self.value.strip()
        if not _EMAIL_PATTERN.match(stripped):
            raise ValidationError(f"Invalid email address: {self.value!r}")
        object.__setattr__(self, "value", stripped)


@dataclass(frozen=True)
class User:
    """A user record: an identity, a non-empty name, and an email address."""

    user_id: UserId
    name: str
    email: Email

    def __post_init__(self) -> None:
        """Validate and normalise the user's name.

        Raises:
            ValidationError: If the name is empty or whitespace-only.
        """
        stripped = self.name.strip()
        if not stripped:
            raise ValidationError("User name must not be empty.")
        object.__setattr__(self, "name", stripped)
