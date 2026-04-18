"""
Demo client for mcp-business-workflows.

Simulates an agent executing a business workflow:
  1. Check system health before doing anything
  2. Create an operational note
  3. Search for relevant notes
  4. List open GitHub issues
  5. Dispatch a webhook if no blockers

Run:
    MCP_API_TOKEN=your-token uv run python examples/client_example.py
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER_PARAMS = StdioServerParameters(
    command="uv",
    args=["run", "mcp-business-workflows"],
    env={**os.environ, "MCP_API_TOKEN": os.environ.get("MCP_API_TOKEN", "demo-token")},
)


def print_result(title: str, result: dict) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")
    print(f"  recommended_action : {result.get('recommended_action', '—')}")
    print(f"  confidence         : {result.get('confidence', '—')}")
    print(f"  requires_review    : {result.get('requires_human_review', '—')}")
    print(f"  next_step          : {result.get('next_step', '—')}")
    print(f"  context_summary    : {result.get('context_summary', '—')}")
    print(f"  event_id           : {result.get('event_id', '—')}")


async def run_demo() -> None:
    print("\nmcp-business-workflows — agent workflow demo\n")

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}\n")

            # 1. Check system health
            resp = await session.call_tool("get_system_status", {})
            result = json.loads(resp.content[0].text)
            print_result("get_system_status", result)

            if result.get("requires_human_review"):
                print("\n  ⚠ Connectors degraded — aborting workflow.")
                sys.exit(1)

            # 2. Create an operational note
            resp = await session.call_tool("create_task", {
                "title": "Deploy v2.1 to production",
                "content": "Triggered by CI pipeline after green tests on main branch.",
                "tags": ["ops"],
            })
            result = json.loads(resp.content[0].text)
            print_result("create_task", result)

            # 3. Search for related notes
            resp = await session.call_tool("search_notes", {"query": "Deploy", "limit": 5})
            result = json.loads(resp.content[0].text)
            print_result(f"search_notes → {result['total']} result(s)", result)

            # 4. List open GitHub issues (uses GITHUB_DEFAULT_REPO if set)
            repo = os.environ.get("GITHUB_DEFAULT_REPO", "")
            if repo:
                resp = await session.call_tool("list_open_issues", {"repo": repo, "limit": 5})
                result = json.loads(resp.content[0].text)
                print_result(f"list_open_issues ({repo})", result)

                if result.get("requires_human_review"):
                    print("\n  ⚠ Critical issues detected — halting webhook dispatch.")
                    sys.exit(1)

            # 5. Dispatch a webhook
            resp = await session.call_tool("dispatch_webhook", {
                "url": os.environ.get("WEBHOOK_DEFAULT_URL", "https://httpbin.org/post"),
                "event_type": "deploy.triggered",
                "payload": {"version": "2.1", "env": "production"},
            })
            result = json.loads(resp.content[0].text)
            print_result("dispatch_webhook", result)

    print(f"\n{'─' * 60}")
    print("  Workflow complete.")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
