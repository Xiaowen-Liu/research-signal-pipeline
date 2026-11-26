from pathlib import Path

import httpx
import pytest

from research_signal_pipeline.extract import fetch_issues, issue_records, save_raw_records


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


def test_pagination_excludes_prs_and_counts_unique_issues():
    pages = []

    def handler(request):
        page = int(request.url.params["page"])
        pages.append(page)
        if page == 1:
            return httpx.Response(200, json=[{"id": 1}, {"id": 9, "pull_request": {}}],
                                  headers={"Link": '<https://api.github.com/x?page=2>; rel="next"'})
        return httpx.Response(200, json=[{"id": 1}, {"id": 2}, {"id": 3}])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert fetch_issues("owner/repo", 2, client) == [{"id": 1}, {"id": 2}]
    assert pages == [1, 2]


@pytest.mark.parametrize("status", [403, 429, 500])
def test_api_errors_propagate_without_returning_partial_data(status):
    def handler(request):
        if request.url.params["page"] == "1":
            return httpx.Response(200, json=[{"id": 1}],
                                  headers={"Link": '<https://api.github.com/x?page=2>; rel="next"'})
        return httpx.Response(status, json={"message": "API failure"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client, pytest.raises(
        httpx.HTTPStatusError
    ):
        fetch_issues("owner/repo", 2, client)


@pytest.mark.parametrize("payload", [{"message": "unexpected"}, [None], [{"id": "bad"}]])
def test_malformed_api_payload_is_rejected(payload):
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=payload)
    )) as client, pytest.raises(ValueError, match="invalid issue list"):
        fetch_issues("owner/repo", 2, client)


def test_repeated_pages_have_a_request_budget():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, json=[{"id": 1}],
        headers={"Link": '<https://api.github.com/x?page=2>; rel="next"'},
    ))) as client, pytest.raises(ValueError, match="budget exceeded"):
        fetch_issues("owner/repo", 2, client, max_pages=2)


def test_empty_repository_returns_empty_list():
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json=[])
    )) as client:
        assert fetch_issues("owner/repo", 2, client) == []


@pytest.mark.parametrize("repository, limit", [("../bad", 2), ("owner/repo", 0)])
def test_bad_arguments_fail_before_network(repository, limit):
    def handler(request):
        pytest.fail("Invalid arguments must not send a request")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client, pytest.raises(ValueError):
        fetch_issues(repository, limit, client)

