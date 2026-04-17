import mcp.server.stdio
from mcp.server import Server

from mcp_business_workflows.config import settings
from mcp_business_workflows.logging import configure_logging, get_logger

configure_logging(settings.log_level)
log = get_logger(__name__)

app = Server("mcp-business-workflows")


def main() -> None:
    import asyncio

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
