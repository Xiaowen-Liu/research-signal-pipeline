from pathlib import Path

import duckdb

from research_signal_pipeline.database import initialize_database


def test_initialize_database_creates_version_one_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "signals.duckdb"

    initialize_database(database_path)

    with duckdb.connect(str(database_path), read_only=True) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }

    assert {"issues", "issue_labels"}.issubset(tables)
