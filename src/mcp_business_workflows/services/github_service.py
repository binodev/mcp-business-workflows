from mcp_business_workflows.adapters.github_client import GitHubClient
from mcp_business_workflows.logging import get_logger, new_event_id
from mcp_business_workflows.schemas.github import ListOpenIssuesInput, ListOpenIssuesOutput

log = get_logger(__name__)

CRITICAL_LABELS = {"critical", "P0", "incident", "security"}


class GitHubService:
    def __init__(self, client: GitHubClient, default_repo: str = "") -> None:
        self._client = client
        self._default_repo = default_repo

    def list_open_issues(self, inp: ListOpenIssuesInput) -> ListOpenIssuesOutput:
        event_id = new_event_id()
        repo = inp.repo or self._default_repo

        issues = self._client.list_issues(repo, inp.state, inp.labels or None, inp.limit)

        critical = [i for i in issues if CRITICAL_LABELS & set(i.labels)]
        has_critical = len(critical) > 0
        confidence = 0.95 if issues else 0.5

        log.info(
            "github.list_open_issues",
            event_id=event_id,
            repo=repo,
            total=len(issues),
            critical=len(critical),
        )

        return ListOpenIssuesOutput(
            issues=issues,
            total=len(issues),
            repo=repo,
            recommended_action="triage_critical" if has_critical else "review_backlog",
            confidence=confidence,
            requires_human_review=has_critical,
            next_step=(
                f"{len(critical)} critical issue(s) require immediate triage."
                if has_critical
                else f"{len(issues)} open issue(s) — review and prioritize backlog."
                if issues
                else "No open issues found. Repository is clear."
            ),
            context_summary=(
                f"{len(issues)} open issue(s) in {repo}."
                + (f" {len(critical)} flagged as critical." if has_critical else "")
            ),
            event_id=event_id,
        )
