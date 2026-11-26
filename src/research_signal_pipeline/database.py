from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import duckdb


def initialize_database(database_path: Path) -> None:
    """Create the local DuckDB database and its version-one tables."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema = files("research_signal_pipeline").joinpath("schema.sql").read_text(encoding="utf-8")

    with duckdb.connect(str(database_path)) as connection:
        connection.execute(schema)

