from datetime import datetime

import duckdb
import pytest

from research_signal_pipeline.database import initialize_database
from research_signal_pipeline.report import build_report


def test_report_scopes_repository_and_uses_snapshot_time(tmp_path):
    database = tmp_path / "signals.duckdb"
    initialize_database(database)
    with duckdb.connect(str(database)) as connection:
        for issue_id, repo in [(1, "example/product"), (2, "other/product")]:
            connection.execute(
                "INSERT INTO issues VALUES (?, ?, ?, NULL, 'open', ?, ?, ?, NULL, 0, ?, ?)",
                [issue_id, repo, "A | title", datetime(2026, 1, 1), datetime(2026, 1, 2),
                 f"https://github.com/{repo}/issues/1", datetime(2026, 1, 11), "raw.json"],
            )
        connection.execute("INSERT INTO issue_labels VALUES (1, 'bug'), (2, 'other')")
    report = build_report(database, "example/product")
    assert report == build_report(database, "example/product")
    assert report["coverage"]["issue_count"] == 1
    assert report["coverage"]["unlabeled_issue_count"] == 0
    assert report["label_frequency"] == [
        {"label": "bug", "issue_count": 1, "share_of_corpus": 1.0}]
    assert report["oldest_open_evidence"][0]["age_days_at_snapshot"] == 10
    assert report["oldest_open_evidence"][0]["source_url"].startswith(
        "https://github.com/example/product/")
    with pytest.raises(ValueError, match="No stored issues"):
        build_report(database, "missing/product")


def test_empty_database_is_not_reported_as_zero_user_problems(tmp_path):
    database = tmp_path / "signals.duckdb"
    initialize_database(database)
    with pytest.raises(ValueError, match="No stored issues"):
        build_report(database, "example/product")
