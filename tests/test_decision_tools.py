import os
import tempfile

import pytest

from mcp_business_workflows.adapters.memory_store import NoteStore
from mcp_business_workflows.schemas.notes import RecommendNextActionInput, WorkflowSignal
from mcp_business_workflows.services.notes_service import NotesService


@pytest.fixture()
def service() -> NotesService:
    with tempfile.TemporaryDirectory() as d:
        store = NoteStore(os.path.join(d, "notes.json"))
        yield NotesService(store)


class TestRecommendNextAction:
    def test_incident_signal_from_text(self, service: NotesService) -> None:
        out = service.recommend_next_action(
            RecommendNextActionInput(context="Production is down, critical outage")
        )
        assert out.recommended_action == "escalate_to_oncall"
        assert out.requires_human_review is True
        assert out.confidence >= 0.9

    def test_degraded_signal_from_text(self, service: NotesService) -> None:
        out = service.recommend_next_action(
            RecommendNextActionInput(context="API is slow, high latency observed")
        )
        assert out.recommended_action == "investigate_degradation"
        assert out.requires_human_review is True

    def test_issues_signal_from_text(self, service: NotesService) -> None:
        out = service.recommend_next_action(
            RecommendNextActionInput(context="Several open bugs reported on this PR")
        )
        assert out.recommended_action == "triage_issues"
        assert out.requires_human_review is False

    def test_webhook_signal_from_text(self, service: NotesService) -> None:
        out = service.recommend_next_action(
            RecommendNextActionInput(context="Need to dispatch webhook and trigger the pipeline")
        )
        assert out.recommended_action == "dispatch_notification"

    def test_review_signal_from_text(self, service: NotesService) -> None:
        out = service.recommend_next_action(
            RecommendNextActionInput(context="Needs sign off from the team lead")
        )
        assert out.recommended_action == "request_human_review"
        assert out.requires_human_review is True

    def test_no_signal_defaults_to_continue(self, service: NotesService) -> None:
        out = service.recommend_next_action(
            RecommendNextActionInput(context="Everything looks normal, proceeding")
        )
        assert out.recommended_action == "continue_workflow"
        assert out.requires_human_review is False

    def test_explicit_signal_overrides_text(self, service: NotesService) -> None:
        out = service.recommend_next_action(
            RecommendNextActionInput(context="things look okay", signals=[WorkflowSignal.incident])
        )
        assert out.recommended_action == "escalate_to_oncall"

    def test_returns_structured_output(self, service: NotesService) -> None:
        out = service.recommend_next_action(
            RecommendNextActionInput(context="deploy completed successfully")
        )
        assert out.event_id
        assert out.next_step
        assert out.context_summary
        assert out.rationale
        assert 0.0 <= out.confidence <= 1.0
