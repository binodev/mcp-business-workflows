from dataclasses import dataclass

import httpx

from mcp_business_workflows.schemas.github import GitHubIssue, IssueState


class GitHubClientError(Exception):
    pass


class GitHubAuthError(GitHubClientError):
    pass


class GitHubNotFoundError(GitHubClientError):
    pass


@dataclass
class GitHubClient:
    token: str
    base_url: str = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def list_issues(
        self,
        repo: str,
        state: IssueState = IssueState.open,
        labels: list[str] | None = None,
        limit: int = 20,
    ) -> list[GitHubIssue]:
        params: dict[str, str | int] = {"state": state.value, "per_page": min(limit, 100)}
        if labels:
            params["labels"] = ",".join(labels)

        with httpx.Client(base_url=self.base_url, headers=self._headers(), timeout=10) as client:
            response = client.get(f"/repos/{repo}/issues", params=params)

        if response.status_code == 401:
            raise GitHubAuthError("Invalid or missing GitHub token")
        if response.status_code == 404:
            raise GitHubNotFoundError(f"Repository '{repo}' not found")
        response.raise_for_status()

        return [
            GitHubIssue(
                number=item["number"],
                title=item["title"],
                state=item["state"],
                url=item["html_url"],
                labels=[label["name"] for label in item.get("labels", [])],
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                author=item["user"]["login"],
            )
            for item in response.json()
            if "pull_request" not in item  # exclude PRs from issues endpoint
        ][:limit]
