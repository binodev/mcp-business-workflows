import json

from mcp.types import TextContent, Tool

from mcp_business_workflows.adapters.webhook_client import WebhookClient
from mcp_business_workflows.config import settings
from mcp_business_workflows.schemas.webhooks import DispatchWebhookInput
from mcp_business_workflows.services.webhook_service import WebhookService

_client = WebhookClient()
_service = WebhookService(_client, default_url=settings.webhook_default_url)

TOOLS = [
    Tool(
        name="dispatch_webhook",
        description=(
            "Send a structured event payload to a webhook endpoint. "
            "Sensitive event types (deploy, rollback, incident, alert) "
            "automatically trigger human review in the output."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target webhook URL. Falls back to WEBHOOK_DEFAULT_URL.",
                },
                "event_type": {
                    "type": "string",
                    "description": "Event name (e.g. 'deploy.triggered', 'incident.opened')",
                },
                "payload": {
                    "type": "object",
                    "description": "Arbitrary JSON payload to include in the webhook body",
                },
            },
            "required": ["event_type"],
        },
    ),
]


async def handle(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
    if name == "dispatch_webhook":
        out = _service.dispatch(DispatchWebhookInput.model_validate(arguments))
        return [TextContent(type="text", text=json.dumps(out.model_dump(mode="json"), indent=2))]
    raise ValueError(f"Unknown tool: {name}")
