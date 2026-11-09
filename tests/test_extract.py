from pathlib import Path

from research_signal_pipeline.extract import issue_records, save_raw_records


def test_issue_records_excludes_pull_requests() -> None:
    payload = [
        {"id": 1, "number": 11, "html_url": "https://example.test/issues/11"},
        {
            "id": 2,
            "number": 12,
            "html_url": "https://example.test/pull/12",
            "pull_request": {"url": "https://example.test/pulls/12"},
        },
    ]

    assert issue_records(payload) == [payload[0]]


def test_save_raw_records_writes_records_and_manifest(tmp_path: Path) -> None:
    records = [{"id": 1, "number": 11, "html_url": "https://example.test/issues/11"}]

    run_dir = save_raw_records(records, "owner/repository", tmp_path)

    assert (run_dir / "issues" / "11.json").exists()
    manifest = (run_dir / "manifest.json").read_text(encoding="utf-8")
    assert '"record_count": 1' in manifest
    assert "https://example.test/issues/11" in manifest
