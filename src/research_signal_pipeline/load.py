"""Validate a preserved extraction run and atomically load its normalized snapshot."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import duckdb

from research_signal_pipeline.database import initialize_database


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(UTC).replace(tzinfo=None)


def normalize_run(run_dir: Path) -> tuple[list[tuple], list[tuple]]:
    manifest = json.loads((run_dir / "manifest.json").read_text())
    repository = manifest["repository"]
    ingested_at = timestamp(manifest["ingested_at"])
    entries = manifest["records"]
    if manifest["record_count"] != len(entries):
        raise ValueError("Manifest record count mismatch")
    by_id: dict[int, tuple] = {}
    labels_by_id: dict[int, set[str]] = {}
    urls: dict[str, int] = {}
    for entry in entries:
        path = run_dir / "issues" / f'{entry["issue_number"]}.json'
        record = json.loads(path.read_text())
        if "pull_request" in record:
            continue
        issue_id = record["id"]
        title = record["title"].strip()
        url = record["html_url"]
        expected = f'https://github.com/{repository}/issues/{entry["issue_number"]}'
        if (not title or url != expected or urlparse(url).scheme != "https"
                or entry["source_url"] != url or entry["issue_id"] != issue_id
                or record["number"] != entry["issue_number"] or not entry["raw_json_path"]):
            raise ValueError("Invalid title, identity or source provenance")
        created = timestamp(record["created_at"])
        updated = timestamp(record["updated_at"])
        comments = record["comments"]
        if updated < created or comments < 0 or record["state"] not in {"open", "closed"}:
            raise ValueError("Invalid dates, state or comment count")
        if url in urls and urls[url] != issue_id:
            raise ValueError("Source URL belongs to multiple issue IDs")
        urls[url] = issue_id
        row = (issue_id, repository, title, record.get("body"), record["state"], created,
               updated, url, record.get("author_association"), comments, ingested_at,
               str(path.resolve()))
        if issue_id in by_id:
            previous = by_id[issue_id]
            if previous[7] != url:
                raise ValueError("Issue ID belongs to multiple source URLs")
            if previous[6] > updated:
                continue
        by_id[issue_id] = row
        labels_by_id[issue_id] = {
            label["name"].strip().lower() for label in record.get("labels", [])
            if label["name"].strip()
        }
    return list(by_id.values()), [
        (issue_id, label) for issue_id, labels in labels_by_id.items() for label in sorted(labels)
    ]


def load_run(run_dir: Path, database_path: Path) -> int:
    rows, labels = normalize_run(run_dir)
    initialize_database(database_path)
    with duckdb.connect(str(database_path)) as connection:
        connection.execute("BEGIN TRANSACTION")
        try:
            for row in rows:
                existing = connection.execute(
                    "SELECT updated_at, ingested_at, repository, source_url, created_at "
                    "FROM issues WHERE issue_id = ?", [row[0]]
                ).fetchone()
                if existing and existing[2:] != (row[1], row[7], row[5]):
                    raise ValueError("Issue identity conflicts with stored provenance")
                if existing and existing[:2] > (row[6], row[10]):
                    continue
                connection.execute("DELETE FROM issue_labels WHERE issue_id = ?", [row[0]])
                connection.execute(
                    "INSERT INTO issues VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT (issue_id) DO UPDATE SET "
                    "title=excluded.title, body=excluded.body, state=excluded.state, "
                    "updated_at=excluded.updated_at, author_association=excluded.author_association, "
                    "comments_count=excluded.comments_count, ingested_at=excluded.ingested_at, "
                    "raw_json_path=excluded.raw_json_path", row
                )
                issue_labels = [label for label in labels if label[0] == row[0]]
                if issue_labels:
                    connection.executemany("INSERT INTO issue_labels VALUES (?, ?)", issue_labels)
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--database", type=Path, default=Path("data/processed/signals.duckdb"))
    args = parser.parse_args()
    count = load_run(args.run_dir, args.database)
    print(f"Validated {count} unique issues; loaded snapshot into {args.database}")


if __name__ == "__main__":
    main()
