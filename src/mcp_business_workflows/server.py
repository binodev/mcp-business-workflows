import mcp.server.stdio
from mcp.server import Server
from mcp.types import TextContent, Tool

from mcp_business_workflows.config import settings
from mcp_business_workflows.errors import dispatch
from mcp_business_workflows.logging import configure_logging, get_logger
from mcp_business_workflows.tools import github, notes, status, webhooks

configure_logging(settings.log_level)
log = get_logger(__name__)

_MODULES = [notes, github, webhooks, status]

app = Server("mcp-business-workflows")


@app.list_tools()
async def list_tools() -> list[Tool]:
    tools = []
    for mod in _MODULES:
        tools.extend(mod.TOOLS)
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
    return await dispatch(name, arguments, _MODULES)


def main() -> None:
    import asyncio

    if not settings.api_token:
        log.error("server.startup_failed", reason="MCP_API_TOKEN not configured")
        raise SystemExit(1)

    log.info("server.starting", host=settings.host, port=settings.port)

    async def run() -> None:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
