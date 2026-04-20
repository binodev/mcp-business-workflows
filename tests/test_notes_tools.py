import os
import tempfile

import pytest

from mcp_business_workflows.adapters.memory_store import NoteStore
from mcp_business_workflows.schemas.notes import CreateTaskInput, NoteTag, SearchNotesInput
from mcp_business_workflows.services.notes_service import NotesService


@pytest.fixture()
def service() -> NotesService:
    with tempfile.TemporaryDirectory() as d:
        store = NoteStore(os.path.join(d, "notes.json"))
        yield NotesService(store)


class TestCreateTask:
    def test_creates_note_with_correct_fields(self, service: NotesService) -> None:
        out = service.create_task(
            CreateTaskInput(title="Deploy v2", content="Deploy notes", tags=[NoteTag.ops])
        )
        assert out.note.title == "Deploy v2"
        assert NoteTag.ops in out.note.tags
        assert out.note.id

    def test_returns_structured_output(self, service: NotesService) -> None:
        out = service.create_task(CreateTaskInput(title="Task", content="Body"))
        assert 0.0 <= out.confidence <= 1.0
        assert out.recommended_action
        assert out.next_step
        assert out.event_id

    def test_incident_tag_requires_human_review(self, service: NotesService) -> None:
        out = service.create_task(
            CreateTaskInput(title="P0", content="Critical", tags=[NoteTag.incident])
        )
        assert out.requires_human_review is True
        assert out.recommended_action == "notify_team"

    def test_non_incident_does_not_require_review(self, service: NotesService) -> None:
        out = service.create_task(
            CreateTaskInput(title="Routine", content="Routine task", tags=[NoteTag.ops])
        )
        assert out.requires_human_review is False


class TestSearchNotes:
    def test_finds_note_by_keyword_in_title(self, service: NotesService) -> None:
        service.create_task(CreateTaskInput(title="Deploy frontend", content="Deploy steps"))
        out = service.search(SearchNotesInput(query="Deploy"))
        assert out.total == 1
        assert out.results[0].title == "Deploy frontend"

    def test_finds_note_by_keyword_in_content(self, service: NotesService) -> None:
        service.create_task(CreateTaskInput(title="Release", content="Rolling deployment strategy"))
        out = service.search(SearchNotesInput(query="deployment"))
        assert out.total == 1

    def test_returns_empty_for_no_match(self, service: NotesService) -> None:
        service.create_task(CreateTaskInput(title="Note A", content="Content A"))
        out = service.search(SearchNotesInput(query="zzznomatch"))
        assert out.total == 0
        assert out.recommended_action == "create_note"

    def test_filters_by_tag(self, service: NotesService) -> None:
        service.create_task(
            CreateTaskInput(title="Incident note", content="Body", tags=[NoteTag.incident])
        )
        service.create_task(CreateTaskInput(title="Ops note", content="Body", tags=[NoteTag.ops]))
        out = service.search(SearchNotesInput(query="note", tags=[NoteTag.incident]))
        assert out.total == 1
        assert out.results[0].title == "Incident note"

    def test_incident_results_require_human_review(self, service: NotesService) -> None:
        service.create_task(
            CreateTaskInput(title="P0 incident", content="Critical", tags=[NoteTag.incident])
        )
        out = service.search(SearchNotesInput(query="incident"))
        assert out.requires_human_review is True

    def test_respects_limit(self, service: NotesService) -> None:
        for i in range(5):
            service.create_task(CreateTaskInput(title=f"Note {i}", content="body"))
        out = service.search(SearchNotesInput(query="Note", limit=3))
        assert len(out.results) <= 3
