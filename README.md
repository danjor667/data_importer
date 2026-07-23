# Resilient Data Importer CLI

A command-line tool that reliably imports user records from a CSV file into a
JSON-backed store. It is **resilient**: missing files and malformed headers abort
cleanly with a clear error, while individual bad rows (invalid data or duplicate
users) are logged and skipped so a single error never aborts the whole import.

## Features

- Imports `user_id, name, email` rows from a CSV into a JSON "database"
- Custom exception hierarchy and structured logging
- Skips invalid and duplicate rows (logged as warnings) and reports a summary
- **Atomic** writes — an interrupted save can never corrupt the existing database
- Meaningful process exit codes for scripting
- 100% test coverage (pytest), fully type-checked (mypy strict), formatted and
  linted (Black + ruff)

## Requirements

- Python 3.11+

## Setup

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install the package with development tooling
pip install -r requirements-dev.txt

# Enable git pre-commit hooks (Black, ruff, mypy)
pre-commit install
```

## Usage

```bash
data-importer --source users.csv --db database.json
# equivalently:
python -m data_importer --source users.csv --db database.json
```

### Arguments

| Argument      | Required | Default | Description                                   |
| ------------- | -------- | ------- | --------------------------------------------- |
| `--source`    | yes      | —       | Path to the source CSV file.                  |
| `--db`        | yes      | —       | Path to the JSON database (created if absent). |
| `--log-level` | no       | `INFO`  | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`.   |

### Input format

The CSV must have a header row containing at least `user_id`, `name`, and
`email`:

```csv
user_id,name,email
u-1,Ada Lovelace,ada@example.com
u-2,Grace Hopper,grace@example.com
```

### Example

Given a CSV with one valid row, one invalid email, one duplicate id, and another
valid row:

```console
$ data-importer --source users.csv --db database.json
2026-01-01T12:00:00 WARNING  data_importer.importer: Skipping row 3: Invalid email address: 'not-an-email'
2026-01-01T12:00:00 WARNING  data_importer.importer: Skipping row 4: Duplicate user id: 'u-1'
2026-01-01T12:00:00 INFO     data_importer.importer: Import complete: 2 imported, 2 skipped.
Import finished: 2 imported, 2 skipped, 4 row(s) processed.
$ echo $?
1
```

The resulting `database.json`:

```json
[
  { "user_id": "u-1", "name": "Ada Lovelace", "email": "ada@example.com" },
  { "user_id": "u-3", "name": "Grace Hopper", "email": "grace@example.com" }
]
```

### Exit codes

| Code | Meaning                                                            |
| ---- | ----------------------------------------------------------------- |
| `0`  | Every row imported successfully.                                  |
| `1`  | Import completed, but one or more rows were skipped.              |
| `2`  | Fatal error — missing/malformed source file or corrupt database. |

## Development

```bash
pytest                                   # run the test suite
pytest --cov --cov-report=term-missing   # run with coverage
black . && ruff check . && mypy          # format, lint, type-check
pre-commit run --all-files               # run every hook
```

A text coverage report is kept at [`coverage.txt`](coverage.txt); regenerate the
HTML report with `pytest --cov --cov-report=html` (written to `htmlcov/`).

## Project structure

```
src/data_importer/
├── models.py          # User + Email/UserId value objects (self-validating)
├── exceptions.py      # ImporterError hierarchy
├── parser.py          # CsvParser -> RawRecord (lazy, structural)
├── validation.py      # UserValidator: RawRecord -> User
├── repository.py      # UserRepository ABC + JsonUserRepository (atomic writes)
├── importer.py        # ImportService coordinator + ImportReport
├── logging_config.py  # setup_logging
├── cli.py             # argparse + composition root
└── __main__.py        # python -m data_importer
```

See [`DESIGN.md`](DESIGN.md) for the full architecture, exception hierarchy, and
testing strategy.

## Architecture at a glance

```
CSV file ─▶ CsvParser ─▶ UserValidator ─▶ JsonUserRepository ─▶ JSON file
                                 ▲
                          ImportService (coordinator)
                                 ▲
                               cli.py
```

Each component has a single responsibility, and `ImportService` depends only on
abstractions (parser/validator protocols and the `UserRepository` ABC), so the
pipeline is easy to test in isolation.