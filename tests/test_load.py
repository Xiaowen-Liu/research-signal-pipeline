import json
from pathlib import Path

import duckdb
import pytest

from research_signal_pipeline.extract import save_raw_records
from research_signal_pipeline.load import load_run


def make_run(tmp_path: Path) -> Path:
    return save_raw_records([{
        "id": 1, "number": 1, "title": "  Cannot sign in  ", "body": None,
        "html_url": "https://github.com/example/product/issues/1", "state": "open",
        "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-02-01T00:00:00Z",
        "comments": 2, "labels": [{"name": " Bug "}, {"name": "bug"}],
    }], "example/product", tmp_path / "raw")


def test_replay_and_update_replace_labels_without_duplicates(tmp_path):
    run = make_run(tmp_path)
    database = tmp_path / "signals.duckdb"
    load_run(run, database)
    load_run(run, database)
    path = run / "issues/1.json"
    record = json.loads(path.read_text())
    record.update(state="closed", labels=[{"name": "resolved"}],
                  updated_at="2026-03-01T00:00:00Z")
    path.write_text(json.dumps(record))
    load_run(run, database)
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("SELECT title, state FROM issues").fetchall() == [
            ("Cannot sign in", "closed")]
        assert connection.execute("SELECT * FROM issue_labels").fetchall() == [(1, "resolved")]


@pytest.mark.parametrize("change", [
    {"title": " "}, {"updated_at": "invalid"},
    {"updated_at": "2025-01-01T00:00:00Z"},
    {"html_url": "https://github.com/other/repo/issues/1"},
])
def test_invalid_data_cannot_change_database(tmp_path, change):
    run = make_run(tmp_path)
    database = tmp_path / "signals.duckdb"
    load_run(run, database)
    path = run / "issues/1.json"
    record = json.loads(path.read_text())
    record.update(change)
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        load_run(run, database)
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("SELECT count(*) FROM issues").fetchone() == (1,)


def test_duplicate_manifest_entries_are_deduplicated(tmp_path):
    run = make_run(tmp_path)
    path = run / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["records"] *= 2
    manifest["record_count"] = 2
    path.write_text(json.dumps(manifest))
    assert load_run(run, tmp_path / "signals.duckdb") == 1


def test_older_snapshot_does_not_restore_old_labels(tmp_path):
    old_run = make_run(tmp_path)
    new_run = make_run(tmp_path)
    path = new_run / "issues/1.json"
    record = json.loads(path.read_text())
    record.update(state="closed", updated_at="2026-03-01T00:00:00Z",
                  labels=[{"name": "resolved"}])
    path.write_text(json.dumps(record))
    database = tmp_path / "signals.duckdb"
    load_run(new_run, database)
    load_run(old_run, database)
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("SELECT state FROM issues").fetchall() == [("closed",)]
        assert connection.execute("SELECT label FROM issue_labels").fetchall() == [("resolved",)]


def test_identity_conflict_rolls_back_entire_batch(tmp_path):
    run = make_run(tmp_path)
    database = tmp_path / "signals.duckdb"
    load_run(run, database)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    record_path = run / "issues/1.json"
    record = json.loads(record_path.read_text())
    new_record = dict(record, id=2, number=2,
                      html_url="https://github.com/example/product/issues/2")
    (run / "issues/2.json").write_text(json.dumps(new_record))
    manifest["records"].insert(0, {
        "issue_id": 2, "issue_number": 2, "source_url": new_record["html_url"],
        "raw_json_path": str(run / "issues/2.json"),
    })
    manifest["record_count"] = 2
    manifest_path.write_text(json.dumps(manifest))
    record["created_at"] = "2026-01-02T00:00:00Z"
    record_path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="identity conflicts"):
        load_run(run, database)
    with duckdb.connect(str(database)) as connection:
        assert connection.execute("SELECT issue_id FROM issues").fetchall() == [(1,)]
