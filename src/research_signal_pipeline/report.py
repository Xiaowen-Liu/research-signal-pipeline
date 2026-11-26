"""Export a repository-scoped, evidence-linked description of the stored issue corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def build_report(database: Path, repository: str) -> dict:
    with duckdb.connect(str(database), read_only=True) as connection:
        connection.execute(
            "CREATE TEMP VIEW corpus AS SELECT * FROM issues WHERE repository = "
            "'" + repository.replace("'", "''") + "'"
        )
        total, opened, first, last = connection.execute(
            "SELECT count(*), count(*) FILTER (WHERE state = 'open'), "
            "min(ingested_at), max(ingested_at) FROM corpus"
        ).fetchone()
        if not total:
            raise ValueError(f"No stored issues for {repository}")
        labeled = connection.execute(
            "SELECT count(DISTINCT issue_id) FROM corpus JOIN issue_labels USING (issue_id)"
        ).fetchone()[0]
        labels = [
            {"label": label, "issue_count": count, "share_of_corpus": count / total}
            for label, count in connection.execute(
                "SELECT label, count(*) AS n FROM corpus JOIN issue_labels USING (issue_id) "
                "GROUP BY label ORDER BY n DESC, label"
            ).fetchall()
        ]
        evidence = [
            {"issue_id": issue_id, "title": title, "source_url": url,
             "created_at": created.isoformat(), "updated_at": updated.isoformat(),
             "age_days_at_snapshot": age}
            for issue_id, title, url, created, updated, age in connection.execute(
                "SELECT issue_id, title, source_url, created_at, updated_at, "
                "date_diff('day', created_at, CAST(? AS TIMESTAMP)) AS age "
                "FROM corpus WHERE state = 'open' ORDER BY created_at, issue_id LIMIT 10",
                [last],
            ).fetchall()
        ]
        months = [
            {"created_month": month.date().isoformat(), "issue_count": count}
            for month, count in connection.execute(
                "SELECT date_trunc('month', created_at) AS month, count(*) "
                "FROM corpus GROUP BY month ORDER BY month"
            ).fetchall()
        ]
    return {
        "report_version": 1,
        "repository": repository,
        "coverage": {
            "issue_count": total, "open_count": opened, "closed_count": total - opened,
            "labeled_issue_count": labeled, "unlabeled_issue_count": total - labeled,
            "earliest_ingested_at_utc": first.isoformat() + "Z",
            "latest_ingested_at_utc": last.isoformat() + "Z",
            "cohort": "All latest-known stored issues for this repository; runs may accumulate.",
        },
        "label_frequency": labels,
        "oldest_open_evidence": evidence,
        "creation_month_counts": months,
        "interpretation": {
            "frequency": "Label frequency describes maintainer taxonomy, not pain-point prevalence.",
            "persistence": "Open age is a review lead, not proof of continuous impact or severity.",
            "growth": "Cannot determine: updated-order sampling and no event history bias trends.",
        },
        "limitations": [
            "Public GitHub contributors are not representative of all product users.",
            "Labels can overlap; their shares need not sum to one.",
            "Missing labels are unknown, not evidence that no pain point exists.",
            "Issue states are latest-known observations, not guaranteed current states.",
            "Ages use latest ingestion time, so replaying this database is deterministic.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/processed/signals.duckdb"))
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/processed/report.json"))
    args = parser.parse_args()
    report = build_report(args.database, args.repository)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {report['coverage']['issue_count']}-issue report to {args.output}")


if __name__ == "__main__":
    main()
