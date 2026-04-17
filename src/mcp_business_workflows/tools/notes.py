import json

from mcp.server import Server
from mcp.types import TextContent, Tool

from mcp_business_workflows.adapters.memory_store import NoteStore
from mcp_business_workflows.config import settings
from mcp_business_workflows.schemas.notes import CreateTaskInput, SearchNotesInput
from mcp_business_workflows.services.notes_service import NotesService

_store = NoteStore(settings.notes_store_path)
_service = NotesService(_store)

SEARCH_NOTES = Tool(
    name="search_notes",
    description=(
        "Search operational notes by keyword and/or tag. "
        "Returns matched notes with a recommended action, confidence score, "
        "and a flag indicating whether human review is required."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keyword or phrase to search"},
            "tags": {
                "type": "array",
                "items": {"type": "string", "enum": ["ops", "incident", "review", "followup", "general"]},
                "description": "Filter by tags (optional)",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
        },
        "required": ["query"],
    },
)

CREATE_TASK = Tool(
    name="create_task",
    description=(
        "Create an operational note or task in the local store. "
        "Returns the created note with a recommended next action and human-review flag."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Note title"},
            "content": {"type": "string", "description": "Note body"},
            "tags": {
                "type": "array",
                "items": {"type": "string", "enum": ["ops", "incident", "review", "followup", "general"]},
                "description": "Tags to categorize the note",
            },
        },
        "required": ["title", "content"],
    },
)


def register(server: Server) -> None:
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [SEARCH_NOTES, CREATE_TASK]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
        if name == "search_notes":
            inp = SearchNotesInput.model_validate(arguments)
            out = _service.search(inp)
        elif name == "create_task":
            inp = CreateTaskInput.model_validate(arguments)
            out = _service.create_task(inp)
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(out.model_dump(mode="json"), indent=2))]
