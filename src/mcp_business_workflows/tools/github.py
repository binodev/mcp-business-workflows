import json

from mcp.server import Server
from mcp.types import TextContent, Tool

from mcp_business_workflows.adapters.github_client import GitHubClient
from mcp_business_workflows.config import settings
from mcp_business_workflows.schemas.github import ListOpenIssuesInput
from mcp_business_workflows.services.github_service import GitHubService

_client = GitHubClient(token=settings.github_token)
_service = GitHubService(_client, default_repo=settings.github_default_repo)

LIST_OPEN_ISSUES = Tool(
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
                "description": "GitHub repository in owner/repo format. Falls back to GITHUB_DEFAULT_REPO.",
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
)


def register(server: Server) -> None:
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [LIST_OPEN_ISSUES]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
        if name == "list_open_issues":
            inp = ListOpenIssuesInput.model_validate(arguments)
            out = _service.list_open_issues(inp)
            return [TextContent(type="text", text=json.dumps(out.model_dump(mode="json"), indent=2))]
        raise ValueError(f"Unknown tool: {name}")
