CREATE TABLE IF NOT EXISTS issues (
    issue_id BIGINT PRIMARY KEY,
    repository VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    body VARCHAR,
    state VARCHAR NOT NULL CHECK (state IN ('open', 'closed')),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    source_url VARCHAR NOT NULL UNIQUE,
    author_association VARCHAR,
    comments_count INTEGER NOT NULL DEFAULT 0,
    ingested_at TIMESTAMP NOT NULL,
    raw_json_path VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS issue_labels (
    issue_id BIGINT NOT NULL REFERENCES issues(issue_id),
    label VARCHAR NOT NULL,
    PRIMARY KEY (issue_id, label)
);
