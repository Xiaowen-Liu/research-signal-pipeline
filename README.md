# Research Signal Pipeline

A small, reproducible data pipeline that turns public product feedback into structured research signals.

This is a 10-day learning experiment in data quality, provenance, and product-facing analysis. It is **not** a production analytics platform and does not use company data, private data, or credentials.

## Question

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
