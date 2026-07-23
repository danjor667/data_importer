"""End-to-end tests for the command-line interface."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from data_importer.cli import EXIT_FATAL, EXIT_OK, EXIT_SKIPPED, main
from tests.conftest import CsvFactory

VALID_CSV = (
    "user_id,name,email\n"
    "u-1,Ada Lovelace,ada@example.com\n"
    "u-2,Grace Hopper,grace@example.com\n"
)


def run_cli(source: Path, db: Path) -> int:
    return main(["--source", str(source), "--db", str(db)])


def load_db(db: Path) -> list[dict[str, str]]:
    data = json.loads(db.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


class TestSuccessfulImport:
    def test_returns_ok_and_persists_users(
        self, make_csv: CsvFactory, tmp_path: Path
    ) -> None:
        db = tmp_path / "db.json"
        code = run_cli(make_csv(VALID_CSV), db)
        assert code == EXIT_OK
        assert {row["user_id"] for row in load_db(db)} == {"u-1", "u-2"}

    def test_prints_a_summary(
        self, make_csv: CsvFactory, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        run_cli(make_csv(VALID_CSV), tmp_path / "db.json")
        out = capsys.readouterr().out
        assert "2" in out
        assert "import" in out.lower()


class TestPartialImport:
    def test_invalid_row_is_skipped_and_returns_skipped_code(
        self, make_csv: CsvFactory, tmp_path: Path
    ) -> None:
        content = (
            "user_id,name,email\n" "u-1,Ada,ada@example.com\n" "u-2,Bad,not-an-email\n"
        )
        db = tmp_path / "db.json"
        code = run_cli(make_csv(content), db)
        assert code == EXIT_SKIPPED
        assert {row["user_id"] for row in load_db(db)} == {"u-1"}

    def test_duplicate_row_is_skipped(
        self, make_csv: CsvFactory, tmp_path: Path
    ) -> None:
        content = (
            "user_id,name,email\n"
            "u-1,Ada,ada@example.com\n"
            "u-1,Ada Again,ada2@example.com\n"
        )
        db = tmp_path / "db.json"
        code = run_cli(make_csv(content), db)
        assert code == EXIT_SKIPPED
        assert len(load_db(db)) == 1


class TestFatalErrors:
    def test_missing_source_returns_fatal(self, tmp_path: Path) -> None:
        code = run_cli(tmp_path / "nope.csv", tmp_path / "db.json")
        assert code == EXIT_FATAL

    def test_missing_required_column_returns_fatal(
        self, make_csv: CsvFactory, tmp_path: Path
    ) -> None:
        code = run_cli(make_csv("name,email\nAda,a@b.io\n"), tmp_path / "db.json")
        assert code == EXIT_FATAL

    def test_corrupt_database_returns_fatal(
        self, make_csv: CsvFactory, tmp_path: Path
    ) -> None:
        db = tmp_path / "db.json"
        db.write_text("{ not json", encoding="utf-8")
        code = run_cli(make_csv(VALID_CSV), db)
        assert code == EXIT_FATAL


class TestArgumentParsing:
    @pytest.mark.parametrize("argv", [[], ["--source", "x.csv"], ["--db", "d.json"]])
    def test_missing_required_arguments_exits(self, argv: list[str]) -> None:
        with pytest.raises(SystemExit):
            main(argv)


class TestModuleEntryPoint:
    def test_python_m_data_importer_runs_end_to_end(
        self, make_csv: CsvFactory, tmp_path: Path
    ) -> None:
        db = tmp_path / "db.json"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "data_importer",
                "--source",
                str(make_csv(VALID_CSV)),
                "--db",
                str(db),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == EXIT_OK
        assert "Import finished" in result.stdout
        assert db.exists()
