"""Run public issue extraction, validation and loading with one command."""

import argparse
from pathlib import Path

import httpx

from research_signal_pipeline.extract import DEFAULT_REPOSITORY, fetch_issues, save_raw_records
from research_signal_pipeline.load import load_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--database", type=Path, default=Path("data/processed/signals.duckdb"))
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    with httpx.Client(headers={"Accept": "application/vnd.github+json",
                               "User-Agent": "research-signal-pipeline"}, timeout=30) as client:
        records = fetch_issues(args.repository, args.limit, client)
    run_dir = save_raw_records(records, args.repository, args.raw_dir)
    count = load_run(run_dir, args.database)
    print(f"Loaded {count} unique issues into {args.database}; raw run: {run_dir}")


if __name__ == "__main__":
    main()
