"""Validation for the data importer.

:class:`UserValidator` turns an un-validated :class:`~data_importer.parser.RawRecord`
into a :class:`~data_importer.models.User`, delegating the actual rules to the
self-validating value objects. Its own contribution is to attach the record's
row number to any :class:`~data_importer.exceptions.ValidationError`, so callers
can report exactly which row was rejected. It performs no I/O.
"""

from __future__ import annotations

from data_importer.exceptions import ValidationError
from data_importer.models import Email, User, UserId
from data_importer.parser import RawRecord

USER_ID_FIELD = "user_id"
NAME_FIELD = "name"
EMAIL_FIELD = "email"


class UserValidator:
    """Builds validated :class:`User` objects from raw records."""

    def to_user(self, record: RawRecord) -> User:
        """Convert a raw record into a validated :class:`User`.

        Args:
            record: The raw, un-validated CSV row.

        Returns:
            A fully validated :class:`User`.

        Raises:
            ValidationError: If any field is missing or invalid. The error's
                ``row_number`` is set to the record's row number.
        """
        try:
            return User(
                UserId(record.values.get(USER_ID_FIELD, "")),
                record.values.get(NAME_FIELD, ""),
                Email(record.values.get(EMAIL_FIELD, "")),
            )
        except ValidationError as error:
            error.row_number = record.row_number
            raise
