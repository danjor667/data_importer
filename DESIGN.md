# Resilient Data Importer CLI — Design

> Design-first blueprint. No production code yet. Covers the module layout,
> exception hierarchy, and testing strategy (SOLID, error handling, Git Flow).

## 1. Package & directory layout

```
data_importer/
├── src/
│   └── data_importer/
│       ├── __init__.py
│       ├── __main__.py          # enables `python -m data_importer`
│       ├── cli.py               # Controller: argparse + composition root
│       ├── models.py            # User dataclass + Email/UserId value objects
│       ├── exceptions.py        # custom exception hierarchy
│       ├── parser.py            # CsvParser (Service Provider)
│       ├── validation.py        # UserValidator (Service Provider)
│       ├── repository.py        # UserRepository (ABC) + JsonUserRepository
│       ├── importer.py          # ImportService (Coordinator) + ImportReport
│       └── logging_config.py    # setup_logging()
├── tests/
│   ├── conftest.py              # shared fixtures (tmp CSV, mock repo)
│   ├── test_models.py
│   ├── test_parser.py
│   ├── test_validation.py
│   ├── test_repository.py
│   ├── test_importer.py
│   └── test_cli.py
├── pyproject.toml               # Black, ruff, mypy, pytest, coverage config
├── requirements.txt
├── requirements-dev.txt
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

**Why `src/` layout:** tests run against the *installed* package, catching packaging
mistakes — the professional default for a testing-focused assessment.

## 2. Domain model (`models.py`)

Wrap primitives to avoid primitive obsession (`email`/`user_id` as bare strings).

| Type     | Kind                        | Responsibility            | Invariant on construction              |
|----------|-----------------------------|---------------------------|----------------------------------------|
| `UserId` | Value object (frozen)       | Identity                  | non-empty, stripped                    |
| `Email`  | Value object (frozen)       | Contact                   | matches email regex → else `ValidationError` |
| `User`   | Entity (frozen dataclass)   | Bundles id, name, email   | name non-empty                         |

Frozen dataclasses give immutability, `__eq__`, `__hash__` for free — trivial
duplicate detection and test assertions.

## 3. Exception hierarchy (`exceptions.py`)

```
ImporterError                     # base — catch all "our" errors distinctly
├── SourceFileError               # source CSV problems (abort run)
│   ├── SourceFileNotFoundError   # missing file
│   └── FileFormatError           # bad header / unreadable structure
├── RecordError                   # per-row problems (carry row_number → skip row)
│   ├── ValidationError           # bad email, empty name/id
│   └── DuplicateUserError        # user_id already in repository
└── RepositoryError               # storage/JSON persistence failure (abort run)
```

- Single root so the CLI catches *our* errors distinctly from unexpected bugs.
- `RecordError` carries `row_number` → log which row failed and **skip it**,
  continuing the import (resilience) instead of aborting.
- "Abort" errors (`SourceFileError`, `RepositoryError`) vs "skip row" errors
  (`RecordError`) — this split drives the importer's control flow.

## 4. Component responsibilities (SRP + DIP)

```
   CSV file ─▶ CsvParser          yields RawRecord (row_number + dict)
                  │
               UserValidator      RawRecord ──▶ User (builds value objects)
                  │
   JSON file ◀─ JsonUserRepository   add(User) / exists(id) / save()   [ABC: UserRepository]
                  ▲
               ImportService      orchestrates → ImportReport          (Coordinator)
                  ▲
               cli.py             argparse, wiring, exit code          (Controller)
```

- **CsvParser** — context-managed file read, validates header, yields
  `(row_number, dict)` lazily. Raises `SourceFileNotFoundError` / `FileFormatError`.
  Knows nothing about users or storage.
- **UserValidator** — pure `RawRecord → User`; value objects self-validate.
  Raises `ValidationError`. No I/O → unit-testable with no mocks.
- **UserRepository (ABC)** — `exists(user_id) -> bool`, `add(user) -> None`,
  `save() -> None`. Abstraction lives here (DIP) so tests inject a mock/in-memory repo.
- **JsonUserRepository** — loads JSON into memory, enforces uniqueness
  (`DuplicateUserError`), writes atomically via context manager (temp file →
  `os.replace`) so a crash never corrupts the DB. Raises `RepositoryError`.
- **ImportService** — the `try/except/else/finally` heart. Per row: validate →
  duplicate check → add; catches `RecordError` to log + skip + count; lets fatal
  errors propagate; `finally` commits the repo. Returns `ImportReport`.
- **cli.py** — parses `--source`, `--db`, `--log-level`; builds concretes; runs the
  service; prints report; sets exit code (0 clean, 1 some skipped, 2 fatal).

## 5. Cross-cutting: logging & context managers

- `logging_config.setup_logging(level)` — one structured formatter; each module uses
  `logging.getLogger(__name__)`. INFO = success/summary, WARNING = skipped rows,
  ERROR = fatal.
- Context managers appear exactly where I/O happens: `CsvParser` (read) and
  `JsonUserRepository` (atomic write) — the right tool, not decoration.

## 6. Testing strategy (>90% coverage)

| Test file            | Isolates              | Technique                                             |
|----------------------|-----------------------|------------------------------------------------------|
| `test_models.py`     | value-object invariants | `parametrize` valid/invalid emails, ids, names     |
| `test_parser.py`     | `CsvParser`           | `tmp_path` real CSVs; `parametrize` malformed rows   |
| `test_validation.py` | `UserValidator`       | pure, no mocks — `parametrize` good/bad records      |
| `test_repository.py` | `JsonUserRepository`  | `tmp_path` JSON file; assert `DuplicateUserError`    |
| `test_importer.py`   | `ImportService`       | inject **mock repo** + fake parser (`pytest-mock`)   |
| `test_cli.py`        | `cli.main`            | integration: temp CSV → temp JSON, exit codes/report |

The `UserRepository` ABC makes `test_importer.py` a fast pure unit test — the payoff
of the DIP decision.

## 7. Git Flow plan

`main` ← `develop` ← feature branches, merged via PR:
`feature/project-scaffold` → `feature/exceptions-and-models` →
`feature/csv-parser` → `feature/validation` → `feature/repository` →
`feature/import-service` → `feature/cli` → `feature/docs-and-coverage`.
Pre-commit runs Black + ruff + mypy on every commit.