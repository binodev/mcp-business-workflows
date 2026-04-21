"""
Real agent test — LLM-agnostic.

Connects any supported LLM to mcp-business-workflows via stdio.
The agent autonomously decides which tools to call and when to stop.

Supported backends (LLM_PROVIDER env var):
    google     → Google AI Studio  (GOOGLE_API_KEY)
    anthropic  → Anthropic API     (ANTHROPIC_API_KEY)

Requirements:
    MCP_API_TOKEN=any-string

Run:
    LLM_PROVIDER=google    GOOGLE_API_KEY=...    uv run python examples/agent_test.py
    LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... uv run python examples/agent_test.py
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(Path(__file__).parent.parent / ".env")


# ---------------------------------------------------------------------------
# Provider-agnostic data structures
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class ToolResult:
    call_id: str
    name: str
    data: dict


# ---------------------------------------------------------------------------
# Backend interface
# ---------------------------------------------------------------------------

class Backend(ABC):
    def setup(self, tools: Any) -> None:
        """Called once after format_tools(), before first send()."""

    @abstractmethod
    def format_tools(self, mcp_tools: list) -> Any:
        """Convert MCP tool list to provider-specific format."""

    @abstractmethod
    def send(self, content: "str | list[ToolResult]") -> tuple[str, list[ToolCall]]:
        """Send a prompt or tool results; return (text, tool_calls)."""


# ---------------------------------------------------------------------------
# Google backend
# ---------------------------------------------------------------------------

class GoogleBackend(Backend):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        from google import genai
        from google.genai import types
        self._types = types
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._chat: Any = None

    def _schema(self, s: dict) -> Any:
        TYPE = {"string": "STRING", "integer": "INTEGER", "number": "NUMBER",
                "boolean": "BOOLEAN", "array": "ARRAY", "object": "OBJECT"}
        kw: dict = {"type": TYPE.get(s.get("type", "object"), "STRING")}
        if "description" in s:
            kw["description"] = s["description"]
        if "enum" in s:
            kw["enum"] = [str(e) for e in s["enum"]]
        if "properties" in s:
            kw["properties"] = {k: self._schema(v) for k, v in s["properties"].items()}
        if "required" in s:
            kw["required"] = s["required"]
        if "items" in s:
            kw["items"] = self._schema(s["items"])
        return self._types.Schema(**kw)

    def format_tools(self, mcp_tools: list) -> Any:
        return [self._types.Tool(function_declarations=[
            self._types.FunctionDeclaration(
                name=t.name,
                description=t.description or "",
                parameters=self._schema(t.inputSchema),
            )
            for t in mcp_tools
        ])]

    def setup(self, tools: Any) -> None:
        self._chat = self._client.chats.create(
            model=self._model,
            config=self._types.GenerateContentConfig(tools=tools),
        )

    def send(self, content: "str | list[ToolResult]") -> tuple[str, list[ToolCall]]:
        if isinstance(content, str):
            response = self._chat.send_message(content)
        else:
            parts = [
                self._types.Part.from_function_response(
                    name=r.name, response={"result": r.data}
                )
                for r in content
            ]
            response = self._chat.send_message(parts)

        text = " ".join(
            p.text for p in response.candidates[0].content.parts
            if hasattr(p, "text") and p.text
        )
        calls = [
            ToolCall(id=fc.name, name=fc.name, args=dict(fc.args) if fc.args else {})
            for fc in (response.function_calls or [])
        ]
        return text, calls


# ---------------------------------------------------------------------------
# Anthropic backend
# ---------------------------------------------------------------------------

class AnthropicBackend(Backend):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._tools: Any = None
        self._messages: list = []

    def format_tools(self, mcp_tools: list) -> Any:
        return [
            {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
            for t in mcp_tools
        ]

    def setup(self, tools: Any) -> None:
        self._tools = tools

    def send(self, content: "str | list[ToolResult]") -> tuple[str, list[ToolCall]]:
        if isinstance(content, str):
            self._messages.append({"role": "user", "content": content})
        else:
            self._messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": r.call_id, "content": json.dumps(r.data)}
                for r in content
            ]})

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            tools=self._tools,
            messages=self._messages,
        )
        self._messages.append({"role": "assistant", "content": response.content})

        text = " ".join(b.text for b in response.content if hasattr(b, "text") and b.text)
        calls = [
            ToolCall(id=b.id, name=b.name, args=b.input)
            for b in response.content if b.type == "tool_use"
        ]
        return text, calls


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_backend() -> Backend:
    provider = os.environ.get("LLM_PROVIDER", "google").lower()
    if provider == "google":
        key = os.environ.get("GOOGLE_API_KEY") or raise_missing("GOOGLE_API_KEY")
        return GoogleBackend(key)
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY") or raise_missing("ANTHROPIC_API_KEY")
        return AnthropicBackend(key)
    raise SystemExit(f"Unknown LLM_PROVIDER '{provider}'. Supported: google, anthropic")


def raise_missing(var: str) -> None:
    raise SystemExit(f"{var} not set")


# ---------------------------------------------------------------------------
# MCP server + scenario
# ---------------------------------------------------------------------------

SERVER_PARAMS = StdioServerParameters(
    command="uv",
    args=["run", "mcp-business-workflows"],
    env={**os.environ, "MCP_API_TOKEN": os.environ.get("MCP_API_TOKEN", "test-token")},
)

SCENARIO = """
You are an ops agent using the mcp-business-workflows tools.

Your task:
1. Check system health first.
2. Create an operational note about a deployment you are about to trigger.
3. Search for any existing notes that might be relevant.
4. If a GitHub repo is configured, check for open critical issues before proceeding.
5. Based on everything you found, call recommend_next_action with a summary.

Be concise. Use tools. Stop when you have a clear recommendation.
"""


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

async def run_agent() -> None:
    provider = os.environ.get("LLM_PROVIDER", "google")
    print(f"\n=== mcp-business-workflows — agent test [{provider}] ===\n")

    backend = make_backend()

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = await session.list_tools()
            tools = backend.format_tools(mcp_tools.tools)
            backend.setup(tools)
            print(f"Tools loaded: {[t.name for t in mcp_tools.tools]}\n")

            text, tool_calls = backend.send(SCENARIO)
            if text:
                print(f"[agent] {text}")

            while tool_calls:
                results = []
                for tc in tool_calls:
                    print(f"\n[tool call] {tc.name}")
                    print(f"  input: {json.dumps(tc.args, indent=2)}")

                    mcp_result = await session.call_tool(tc.name, tc.args)
                    data = json.loads(mcp_result.content[0].text)

                    print(f"  → recommended_action : {data.get('recommended_action', '—')}")
                    print(f"  → confidence         : {data.get('confidence', '—')}")
                    print(f"  → requires_review    : {data.get('requires_human_review', '—')}")
                    print(f"  → next_step          : {data.get('next_step', '—')}")

                    results.append(ToolResult(call_id=tc.id, name=tc.name, data=data))

                text, tool_calls = backend.send(results)
                if text:
                    print(f"\n[agent] {text}")

            print("\n=== Agent finished ===\n")


if __name__ == "__main__":
    asyncio.run(run_agent())
