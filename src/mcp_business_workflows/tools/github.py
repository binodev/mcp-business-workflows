import json

from mcp.types import TextContent, Tool

from mcp_business_workflows.adapters.github_client import GitHubClient
from mcp_business_workflows.config import settings
from mcp_business_workflows.schemas.github import ListOpenIssuesInput
from mcp_business_workflows.services.github_service import GitHubService

_client = GitHubClient(token=settings.github_token)
_service = GitHubService(_client, default_repo=settings.github_default_repo)

TOOLS = [
    Tool(
        name="list_open_issues",
        description=(
            "List open issues from a GitHub repository. "
            "Returns issues with triage recommendation, confidence score, "
            "and a critical-issue flag that triggers human review."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": (
                        "GitHub repository in owner/repo format. Falls back to GITHUB_DEFAULT_REPO."
                    ),
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "default": "open",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by label names",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
        },
    ),
]


async def handle(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
    if name == "list_open_issues":
        out = _service.list_open_issues(ListOpenIssuesInput.model_validate(arguments))
        return [TextContent(type="text", text=json.dumps(out.model_dump(mode="json"), indent=2))]
    raise ValueError(f"Unknown tool: {name}")
