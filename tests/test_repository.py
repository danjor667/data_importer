"""Tests for the JSON-backed user repository."""

import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from data_importer.exceptions import DuplicateUserError, RepositoryError
from data_importer.models import Email, User, UserId
from data_importer.repository import JsonUserRepository, UserRepository


def build_user(user_id: str = "u-1", name: str = "Ada", email: str = "a@b.io") -> User:
    return User(UserId(user_id), name, Email(email))


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


class TestAbstractContract:
    def test_user_repository_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            UserRepository()  # type: ignore[abstract]

    def test_json_repository_is_a_user_repository(self, tmp_path: Path) -> None:
        assert isinstance(JsonUserRepository(tmp_path / "db.json"), UserRepository)


class TestFreshDatabase:
    def test_missing_file_starts_empty(self, tmp_path: Path) -> None:
        repo = JsonUserRepository(tmp_path / "db.json")
        assert repo.exists(UserId("u-1")) is False

    def test_add_then_save_writes_the_user(self, tmp_path: Path) -> None:
        path = tmp_path / "db.json"
        repo = JsonUserRepository(path)
        repo.add(build_user())
        repo.save()
        assert read_json(path) == [{"user_id": "u-1", "name": "Ada", "email": "a@b.io"}]

    def test_save_does_not_leave_temporary_files(self, tmp_path: Path) -> None:
        repo = JsonUserRepository(tmp_path / "db.json")
        repo.add(build_user())
        repo.save()
        assert [p.name for p in tmp_path.iterdir()] == ["db.json"]


class TestExistingDatabase:
    def _seed(self, tmp_path: Path) -> Path:
        path = tmp_path / "db.json"
        path.write_text(
            json.dumps([{"user_id": "u-1", "name": "Ada", "email": "a@b.io"}]),
            encoding="utf-8",
        )
        return path

    def test_loads_existing_users(self, tmp_path: Path) -> None:
        repo = JsonUserRepository(self._seed(tmp_path))
        assert repo.exists(UserId("u-1")) is True

    def test_round_trips_through_a_new_instance(self, tmp_path: Path) -> None:
        path = tmp_path / "db.json"
        first = JsonUserRepository(path)
        first.add(build_user("u-9", "Grace", "g@h.io"))
        first.save()
        reloaded = JsonUserRepository(path)
        assert reloaded.exists(UserId("u-9")) is True


class TestDuplicates:
    def test_adding_an_existing_id_raises_duplicate(self, tmp_path: Path) -> None:
        repo = JsonUserRepository(tmp_path / "db.json")
        repo.add(build_user("u-1"))
        with pytest.raises(DuplicateUserError) as exc_info:
            repo.add(build_user("u-1", name="Other"))
        assert exc_info.value.user_id == "u-1"

    def test_duplicate_against_a_loaded_user(self, tmp_path: Path) -> None:
        path = tmp_path / "db.json"
        path.write_text(
            json.dumps([{"user_id": "u-1", "name": "Ada", "email": "a@b.io"}]),
            encoding="utf-8",
        )
        repo = JsonUserRepository(path)
        with pytest.raises(DuplicateUserError):
            repo.add(build_user("u-1"))


class TestCorruptDatabase:
    def test_invalid_json_raises_repository_error(self, tmp_path: Path) -> None:
        path = tmp_path / "db.json"
        path.write_text("{ not json", encoding="utf-8")
        with pytest.raises(RepositoryError):
            JsonUserRepository(path)

    def test_non_array_json_raises_repository_error(self, tmp_path: Path) -> None:
        path = tmp_path / "db.json"
        path.write_text(json.dumps({"user_id": "u-1"}), encoding="utf-8")
        with pytest.raises(RepositoryError):
            JsonUserRepository(path)

    def test_malformed_entry_raises_repository_error(self, tmp_path: Path) -> None:
        path = tmp_path / "db.json"
        path.write_text(json.dumps(["not-an-object"]), encoding="utf-8")
        with pytest.raises(RepositoryError):
            JsonUserRepository(path)


class TestAtomicWriteFailure:
    def test_replace_failure_raises_repository_error_and_cleans_up(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        repo = JsonUserRepository(tmp_path / "db.json")
        repo.add(build_user())
        mocker.patch(
            "data_importer.repository.os.replace", side_effect=OSError("disk full")
        )
        with pytest.raises(RepositoryError):
            repo.save()
        # the failed write must not leave a stray temp file behind
        assert list(tmp_path.iterdir()) == []
