# Resilient Data Importer CLI

A command-line tool that reliably imports user records from a CSV file into a
JSON-backed store. It is resilient to missing files, malformed rows, and
duplicate users: bad rows are logged and skipped so a single error never aborts
the whole import.

> **Status:** scaffolding in progress. See [`DESIGN.md`](DESIGN.md) for the full
> architecture and module breakdown.

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

> CLI is implemented in a later feature branch. Planned interface:

```bash
data-importer --source users.csv --db database.json
# or
python -m data_importer --source users.csv --db database.json
```

## Development

```bash
pytest                 # run the test suite
pytest --cov           # run with coverage
black . && ruff check . && mypy .
```

## Project layout

See [`DESIGN.md`](DESIGN.md) for the module breakdown, exception hierarchy, and
testing strategy.
