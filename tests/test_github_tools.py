import pytest
from pytest_httpx import HTTPXMock

from mcp_business_workflows.adapters.github_client import (
    GitHubAuthError,
    GitHubClient,
    GitHubNotFoundError,
)
from mcp_business_workflows.schemas.github import ListOpenIssuesInput
from mcp_business_workflows.services.github_service import GitHubService

REPO = "acme/backend"
BASE_URL = "https://api.github.com"

ISSUE_FIXTURE = {
    "number": 42,
    "title": "Login fails on Safari",
    "state": "open",
    "html_url": f"https://github.com/{REPO}/issues/42",
    "labels": [{"name": "bug"}],
    "created_at": "2026-04-01T10:00:00Z",
    "updated_at": "2026-04-10T12:00:00Z",
    "user": {"login": "alice"},
}

CRITICAL_ISSUE_FIXTURE = {**ISSUE_FIXTURE, "number": 43, "labels": [{"name": "critical"}]}


@pytest.fixture()
def client() -> GitHubClient:
    return GitHubClient(token="test-token")


@pytest.fixture()
def service(client: GitHubClient) -> GitHubService:
    return GitHubService(client, default_repo=REPO)


class TestGitHubClient:
    def test_lists_issues(self, client: GitHubClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=[ISSUE_FIXTURE])
        issues = client.list_issues(REPO)
        assert len(issues) == 1
        assert issues[0].number == 42
        assert issues[0].author == "alice"

    def test_excludes_pull_requests(self, client: GitHubClient, httpx_mock: HTTPXMock) -> None:
        pr = {**ISSUE_FIXTURE, "pull_request": {"url": "..."}}
        httpx_mock.add_response(json=[ISSUE_FIXTURE, pr])
        issues = client.list_issues(REPO)
        assert len(issues) == 1

    def test_raises_auth_error_on_401(self, client: GitHubClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401)
        with pytest.raises(GitHubAuthError):
            client.list_issues(REPO)

    def test_raises_not_found_on_404(self, client: GitHubClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404)
        with pytest.raises(GitHubNotFoundError):
            client.list_issues(REPO)


class TestGitHubService:
    def test_returns_structured_output(self, service: GitHubService, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=[ISSUE_FIXTURE])
        out = service.list_open_issues(ListOpenIssuesInput())
        assert out.total == 1
        assert out.repo == REPO
        assert 0.0 <= out.confidence <= 1.0
        assert out.event_id

    def test_critical_labels_trigger_human_review(
        self, service: GitHubService, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(json=[CRITICAL_ISSUE_FIXTURE])
        out = service.list_open_issues(ListOpenIssuesInput())
        assert out.requires_human_review is True
        assert out.recommended_action == "triage_critical"

    def test_no_critical_issues(self, service: GitHubService, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=[ISSUE_FIXTURE])
        out = service.list_open_issues(ListOpenIssuesInput())
        assert out.requires_human_review is False
        assert out.recommended_action == "review_backlog"

    def test_empty_repo(self, service: GitHubService, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=[])
        out = service.list_open_issues(ListOpenIssuesInput())
        assert out.total == 0
        assert "clear" in out.next_step.lower()

    def test_uses_provided_repo_over_default(
        self, service: GitHubService, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(json=[])
        out = service.list_open_issues(ListOpenIssuesInput(repo="other/repo"))
        assert out.repo == "other/repo"
