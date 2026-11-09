"""Extract public GitHub issues while preserving their source records."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import argparse
import json

import httpx

GITHUB_API_URL = "https://api.github.com"
DEFAULT_REPOSITORY = "open-webui/open-webui"
DEFAULT_LIMIT = 200


def issue_records(payload: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep issue payloads and exclude pull requests returned by GitHub's issues API."""
    return [record for record in payload if "pull_request" not in record]


def fetch_issues(repository: str, limit: int, client: httpx.Client) -> list[dict[str, Any]]:
    """Fetch at most the requested number of public GitHub issues."""
    records: list[dict[str, Any]] = []
    page = 1

    while len(records) < limit:
        response = client.get(
            f"{GITHUB_API_URL}/repos/{repository}/issues",
            params={
                "state": "all",
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            },
        )
        response.raise_for_status()
        payload = response.json()
        records.extend(issue_records(payload))

        if not payload or len(records) >= limit:
            break
        page += 1

    return records[:limit]


def save_raw_records(records: Iterable[dict[str, Any]], repository: str, output_dir: Path) -> Path:
    """Write each API record and a manifest beneath a timestamped run directory."""
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / repository.replace("/", "__") / run_id
    issues_dir = run_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=False)

    manifest: list[dict[str, Any]] = []
    for record in records:
        issue_number = record["number"]
        record_path = issues_dir / f"{issue_number}.json"
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        manifest.append(
            {
                "issue_id": record["id"],
                "issue_number": issue_number,
                "source_url": record["html_url"],
                "raw_json_path": str(record_path),
            }
        )

    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "repository": repository,
                "ingested_at": datetime.now(UTC).isoformat(),
                "record_count": len(manifest),
                "records": manifest,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract public GitHub issues into raw JSON files.")
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1")

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "research-signal-pipeline"}
    with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
        records = fetch_issues(args.repository, args.limit, client)

    run_dir = save_raw_records(records, args.repository, args.output_dir)
    print(f"Saved {len(records)} issue records to {run_dir}")


if __name__ == "__main__":
    main()
