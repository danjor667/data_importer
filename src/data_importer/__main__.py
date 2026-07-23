"""Enable ``python -m data_importer`` as an entry point."""

from data_importer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
