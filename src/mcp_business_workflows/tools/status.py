import json

from mcp.server import Server
from mcp.types import TextContent, Tool

from mcp_business_workflows.schemas.status import GetSystemStatusInput
from mcp_business_workflows.services.status_service import StatusService

_service = StatusService()

GET_SYSTEM_STATUS = Tool(
    name="get_system_status",
    description=(
        "Check the health of configured connectors (GitHub, webhook). "
        "Returns per-connector status with an overall health assessment "
        "and a human-review flag when any connector is unreachable."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "connectors": {
                "type": "array",
                "items": {"type": "string", "enum": ["github", "webhook"]},
                "description": "Connectors to check. Empty checks all.",
            }
        },
    },
)


def register(server: Server) -> None:
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [GET_SYSTEM_STATUS]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
        if name == "get_system_status":
            inp = GetSystemStatusInput.model_validate(arguments)
            out = _service.get_status(inp)
            return [TextContent(type="text", text=json.dumps(out.model_dump(mode="json"), indent=2))]
        raise ValueError(f"Unknown tool: {name}")
