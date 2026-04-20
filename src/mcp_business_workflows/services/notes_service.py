import uuid
from datetime import UTC, datetime

from mcp_business_workflows.adapters.memory_store import NoteStore
from mcp_business_workflows.logging import get_logger, new_event_id
from mcp_business_workflows.schemas.notes import (
    CreateTaskInput,
    CreateTaskOutput,
    Note,
    NoteTag,
    RecommendNextActionInput,
    RecommendNextActionOutput,
    SearchNotesInput,
    SearchNotesOutput,
    WorkflowSignal,
)

log = get_logger(__name__)


class NotesService:
    def __init__(self, store: NoteStore) -> None:
        self._store = store

    def search(self, inp: SearchNotesInput) -> SearchNotesOutput:
        event_id = new_event_id()
        results = self._store.search(inp.query, [t.value for t in inp.tags])
        results = results[: inp.limit]

        log.info("notes.search", event_id=event_id, query=inp.query, hits=len(results))

        has_incidents = any(NoteTag.incident in n.tags for n in results)
        confidence = min(1.0, len(results) / 3) if results else 0.0

        return SearchNotesOutput(
            results=results,
            total=len(results),
            recommended_action="review_results" if results else "create_note",
            confidence=round(confidence, 2),
            requires_human_review=has_incidents,
            next_step=(
                f"Review the {len(results)} matching note(s) and decide next action."
                if results
                else f"No notes found for '{inp.query}'. Consider creating one."
            ),
            context_summary=(
                f"Found {len(results)} note(s) matching '{inp.query}'."
                + (
                    " Contains incident-tagged notes — human review advised."
                    if has_incidents
                    else ""
                )
            ),
            event_id=event_id,
        )

    def create_task(self, inp: CreateTaskInput) -> CreateTaskOutput:
        event_id = new_event_id()
        now = datetime.now(UTC)
        note = Note(
            id=uuid.uuid4().hex,
            title=inp.title,
            content=inp.content,
            tags=inp.tags,
            created_at=now,
            updated_at=now,
        )
        self._store.insert(note)

        log.info("notes.create_task", event_id=event_id, note_id=note.id, tags=inp.tags)

        has_incident = NoteTag.incident in inp.tags

        return CreateTaskOutput(
            note=note,
            recommended_action="notify_team" if has_incident else "continue_workflow",
            confidence=0.9,
            requires_human_review=has_incident,
            next_step=(
                "Notify the ops team — this note is tagged as an incident."
                if has_incident
                else f"Note '{note.title}' created. Proceed with the next workflow step."
            ),
            context_summary=(
                f"Created note '{note.title}' with tags: {[t.value for t in inp.tags] or ['none']}."
            ),
            event_id=event_id,
        )

    def recommend_next_action(self, inp: RecommendNextActionInput) -> RecommendNextActionOutput:
        event_id = new_event_id()
        ctx = inp.context.lower()
        signals = set(inp.signals)

        # Detect signals from free-text context
        if any(w in ctx for w in ("incident", "down", "outage", "critical", "error")):
            signals.add(WorkflowSignal.incident)
        if any(w in ctx for w in ("degraded", "slow", "timeout", "latency")):
            signals.add(WorkflowSignal.degraded)
        if any(w in ctx for w in ("issue", "bug", "pr ", "pull request")):
            signals.add(WorkflowSignal.issues)
        if any(w in ctx for w in ("webhook", "dispatch", "notify", "trigger")):
            signals.add(WorkflowSignal.webhook)
        if any(w in ctx for w in ("review", "approve", "sign off", "validate")):
            signals.add(WorkflowSignal.review)

        if WorkflowSignal.incident in signals:
            action = "escalate_to_oncall"
            rationale = "Context contains incident-level signals. Immediate escalation required."
            confidence = 0.92
            requires_review = True
            next_step = (
                "Page the on-call engineer and open an incident note"
                " with create_task (tag: incident)."
            )
        elif WorkflowSignal.degraded in signals:
            action = "investigate_degradation"
            rationale = (
                "Degraded performance detected."
                " Needs investigation before triggering further workflows."
            )
            confidence = 0.85
            requires_review = True
            next_step = (
                "Run get_system_status to identify which connector is degraded,"
                " then decide on remediation."
            )
        elif WorkflowSignal.issues in signals:
            action = "triage_issues"
            rationale = "Open issues or bugs detected. Triage recommended before proceeding."
            confidence = 0.80
            requires_review = False
            next_step = (
                "Run list_open_issues to get the current backlog, then prioritize with the team."
            )
        elif WorkflowSignal.webhook in signals:
            action = "dispatch_notification"
            rationale = (
                "Webhook/notification signal detected. An external system should be informed."
            )
            confidence = 0.88
            requires_review = False
            next_step = (
                "Use dispatch_webhook to notify the downstream system about this workflow event."
            )
        elif WorkflowSignal.review in signals:
            action = "request_human_review"
            rationale = (
                "Approval or sign-off needed. Automation should pause until a human validates."
            )
            confidence = 0.90
            requires_review = True
            next_step = (
                "Halt automation and route to the appropriate reviewer."
                " Document context with create_task."
            )
        else:
            action = "continue_workflow"
            rationale = (
                "No high-priority signal detected. Standard workflow progression is appropriate."
            )
            confidence = 0.70
            requires_review = False
            next_step = "Proceed with the next planned workflow step. Monitor for new signals."

        log.info(
            "decision.recommend_next_action",
            event_id=event_id,
            action=action,
            signals=[s.value for s in signals],
            confidence=confidence,
        )

        return RecommendNextActionOutput(
            recommended_action=action,
            rationale=rationale,
            confidence=confidence,
            requires_human_review=requires_review,
            next_step=next_step,
            context_summary=(
                f"Analyzed context. Detected signals: {[s.value for s in signals] or ['none']}."
            ),
            event_id=event_id,
        )
