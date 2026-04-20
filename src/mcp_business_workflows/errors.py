import json

from mcp.types import TextContent
from pydantic import ValidationError

from mcp_business_workflows.adapters.github_client import GitHubAuthError, GitHubNotFoundError
from mcp_business_workflows.logging import get_logger, new_event_id

log = get_logger(__name__)


def error_response(code: str, message: str, event_id: str) -> list[TextContent]:
    return [
        TextContent(
            type="text",
            text=json.dumps(
                {
                    "error": {"code": code, "message": message},
                    "recommended_action": "fix_input_and_retry"
                    if code == "validation_error"
                    else "escalate",
                    "confidence": 0.0,
                    "requires_human_review": code != "validation_error",
                    "next_step": message,
                    "event_id": event_id,
                },
                indent=2,
            ),
        )
    ]


async def dispatch(name: str, arguments: dict, modules: list) -> list[TextContent]:  # type: ignore[type-arg]
    event_id = new_event_id()
    for mod in modules:
        if any(t.name == name for t in mod.TOOLS):
            try:
                return await mod.handle(name, arguments)
            except ValidationError as exc:
                log.warning("tool.validation_error", tool=name, event_id=event_id, error=str(exc))
                return error_response(
                    "validation_error", f"Invalid input: {exc.error_count()} error(s)", event_id
                )
            except GitHubAuthError as exc:
                log.error("tool.github_auth_error", tool=name, event_id=event_id)
                return error_response("github_auth_error", str(exc), event_id)
            except GitHubNotFoundError as exc:
                log.error("tool.github_not_found", tool=name, event_id=event_id)
                return error_response("github_not_found", str(exc), event_id)
            except Exception as exc:
                log.error("tool.unexpected_error", tool=name, event_id=event_id, error=str(exc))
                return error_response("internal_error", "An unexpected error occurred.", event_id)
    log.warning("tool.unknown", tool=name, event_id=event_id)
    return error_response("unknown_tool", f"Tool '{name}' not found.", event_id)
