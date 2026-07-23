"""Storage layer for the data importer.

:class:`UserRepository` is the abstraction the import service depends on, so the
service can be unit-tested against an in-memory or mock repository. The concrete
:class:`JsonUserRepository` persists users to a JSON file, enforcing uniqueness
and writing atomically (temp file then :func:`os.replace`) so an interrupted
write can never corrupt the existing database.
"""

from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from data_importer.exceptions import DuplicateUserError, RepositoryError
from data_importer.models import User, UserId

_UserRow = dict[str, str]


class UserRepository(ABC):
    """Abstract store of :class:`User` records."""

    @abstractmethod
    def exists(self, user_id: UserId) -> bool:
        """Return whether a user with ``user_id`` is already stored."""

    @abstractmethod
    def add(self, user: User) -> None:
        """Add ``user`` to the store.

        Raises:
            DuplicateUserError: If a user with the same id already exists.
        """

    @abstractmethod
    def save(self) -> None:
        """Persist all added users durably.

        Raises:
            RepositoryError: If the store cannot be written.
        """


class JsonUserRepository(UserRepository):
    """A :class:`UserRepository` backed by a JSON array on disk."""

    def __init__(self, path: Path) -> None:
        """Open the repository, loading any existing users from ``path``.

        Args:
            path: Location of the JSON database file. It need not exist yet.

        Raises:
            RepositoryError: If the file exists but cannot be read or does not
                contain a JSON array of user objects.
        """
        self._path = path
        self._users: dict[str, _UserRow] = self._load()

    def exists(self, user_id: UserId) -> bool:
        """Return whether ``user_id`` is already stored."""
        return user_id.value in self._users

    def add(self, user: User) -> None:
        """Add ``user`` in memory, rejecting a duplicate id.

        Raises:
            DuplicateUserError: If the user's id is already present.
        """
        key = user.user_id.value
        if key in self._users:
            raise DuplicateUserError(key)
        self._users[key] = {
            "user_id": user.user_id.value,
            "name": user.name,
            "email": user.email.value,
        }

    def save(self) -> None:
        """Persist the users to disk atomically.

        Writes to a temporary file in the same directory and then atomically
        replaces the target, so a failure never leaves a partial database.

        Raises:
            RepositoryError: If the file cannot be written.
        """
        payload = list(self._users.values())
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
                suffix=".tmp",
                delete=False,
                encoding="utf-8",
            ) as handle:
                temp_name = handle.name
                json.dump(payload, handle, indent=2)
                handle.write("\n")
            os.replace(temp_name, self._path)
            temp_name = None
        except OSError as error:
            raise RepositoryError(f"Failed to save database to {self._path}") from error
        finally:
            if temp_name is not None and os.path.exists(temp_name):
                os.unlink(temp_name)

    def _load(self) -> dict[str, _UserRow]:
        """Read and validate the existing database file.

        Returns:
            A mapping of user id to its stored row, empty if the file is absent.

        Raises:
            RepositoryError: If the file is unreadable or malformed.
        """
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RepositoryError(f"Cannot read database file: {self._path}") from error
        if not isinstance(raw, list):
            raise RepositoryError(
                f"Database file must contain a JSON array: {self._path}"
            )
        users: dict[str, _UserRow] = {}
        for entry in raw:
            if not isinstance(entry, dict) or "user_id" not in entry:
                raise RepositoryError(
                    f"Malformed user entry in database file: {self._path}"
                )
            users[str(entry["user_id"])] = {
                "user_id": str(entry.get("user_id", "")),
                "name": str(entry.get("name", "")),
                "email": str(entry.get("email", "")),
            }
        return users
