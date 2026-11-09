from __future__ import annotations

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"


def initialize_database(database_path: Path) -> None:
    """Create the local DuckDB database and its version-one tables."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with duckdb.connect(str(database_path)) as connection:
        connection.execute(schema)
