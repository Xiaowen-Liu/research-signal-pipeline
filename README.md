# Research Signal Pipeline

A small, reproducible data pipeline that turns public product feedback into structured research signals.

This is a 10-day learning experiment in data quality, provenance, and product-facing analysis. It is **not** a production analytics platform and does not use company data, private data, or credentials.

## Run locally

Requires Python 3.11 or newer. From a source checkout:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m research_signal_pipeline.run --repository open-webui/open-webui --limit 200
pytest -q
```

To replay an existing extraction without fetching again:

```bash
python -m research_signal_pipeline.load data/raw/open-webui__open-webui/<run-id>
```

The loader validates titles, source identity, timezone-aware dates, counts and provenance
before writing. It deduplicates issue IDs, normalizes labels, and updates issue snapshots
and labels in one transaction. Older snapshots cannot overwrite newer data. Raw runs
remain on disk; stored raw paths point to the local preserved JSON. Keep each run's
`manifest.json` and `issues/` folder together when moving or replaying it.

The database is a latest-known snapshot, not an event history. A sampled run does not
delete issues absent from that run. API errors stop extraction; retry the command after
resolving network or GitHub rate-limit errors. No credentials are required.

## Three analysis queries

Run the three statements in [`sql/analysis.sql`](sql/analysis.sql) against
`data/processed/signals.duckdb`, for example using DuckDB's Python client:

```python
from pathlib import Path
import duckdb

with duckdb.connect('data/processed/signals.duckdb', read_only=True) as connection:
    for query in Path('sql/analysis.sql').read_text().split(';'):
        if query.strip():
            print(connection.execute(query).fetchall())
```

They report label frequency, oldest currently open sampled issues, and label counts by
creation month. Labels are maintainer taxonomy rather than validated pain-point themes;
open age is not severity. Since extraction selects recently updated issues, monthly counts
are biased by sampling and cannot establish population trends. Missing labels stay missing.

## Research question

For a public AI product's GitHub issues, what user pain points appear most often, which are persistent, and which have become more common recently?

## Scope

The first dataset will use public GitHub issues from a single product repository. The pipeline will:

1. Extract public issue metadata and text from the GitHub API.
2. Preserve the raw API response for traceability.
3. Normalize fields, labels, and timestamps; filter pull requests; and deduplicate records.
4. Load cleaned records into DuckDB.
5. Run data-quality checks and a small set of analytical SQL queries.

## Non-goals for v1

- No company or private data.
- No RAG, LLM-based classification, dashboard, or deployment.
- No claim that issue volume represents all users.
- No automated decisions about users or contributors.

## Definition of done

- A repeatable command pulls a bounded public dataset.
- Raw data and cleaned data are traceable by source URL and run timestamp.
- DuckDB contains `issues` and `issue_labels` tables.
- Tests catch missing titles, duplicate source URLs, invalid dates, and missing provenance.
- The README shows three queries and explains their limitations.

## Planned schema

### `issues`

| Field | Purpose |
| --- | --- |
| `issue_id` | GitHub issue identifier |
| `repository` | Source repository in `owner/name` form |
| `title` | User-provided issue title |
| `body` | Public issue body |
| `state` | `open` or `closed` |
| `created_at` / `updated_at` | Source timestamps |
| `source_url` | Canonical public source URL |
| `author_association` | Relationship to the repository, if supplied |
| `comments_count` | Public discussion count |
| `ingested_at` | Pipeline run timestamp |
| `raw_json_path` | Path to the preserved API record |

### `issue_labels`

| Field | Purpose |
| --- | --- |
| `issue_id` | Links to `issues` |
| `label` | Normalized label text |

## Repository layout

```text
src/research_signal_pipeline/  Pipeline code
data/raw/                      GitHub API records (not committed)
data/processed/                Cleaned local data (not committed)
sql/                           DuckDB schema and analysis queries
tests/                         Data-quality checks
```

## Data limitations

GitHub issues are a contributor-facing feedback channel, not a representative user survey. Results will describe the public issue corpus only. Labels, author association, and issue state reflect GitHub metadata rather than verified user demographics or product impact.

