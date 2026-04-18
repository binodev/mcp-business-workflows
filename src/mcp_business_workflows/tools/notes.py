import json

from mcp.types import TextContent, Tool

from mcp_business_workflows.adapters.memory_store import NoteStore
from mcp_business_workflows.config import settings
from mcp_business_workflows.schemas.notes import CreateTaskInput, SearchNotesInput
from mcp_business_workflows.services.notes_service import NotesService

_store = NoteStore(settings.notes_store_path)
_service = NotesService(_store)

TOOLS = [
    Tool(
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
    ),
    Tool(
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
    ),
]


async def handle(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
    if name == "search_notes":
        out = _service.search(SearchNotesInput.model_validate(arguments))
    elif name == "create_task":
        out = _service.create_task(CreateTaskInput.model_validate(arguments))
    else:
        raise ValueError(f"Unknown tool: {name}")
    return [TextContent(type="text", text=json.dumps(out.model_dump(mode="json"), indent=2))]
