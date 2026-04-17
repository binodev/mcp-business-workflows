from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class NoteTag(StrEnum):
    ops = "ops"
    incident = "incident"
    review = "review"
    followup = "followup"
    general = "general"


class Note(BaseModel):
    id: str
    title: str
    content: str
    tags: list[NoteTag] = []
    created_at: datetime
    updated_at: datetime


class SearchNotesInput(BaseModel):
    query: str = Field(..., description="Keyword or phrase to search in title and content")
    tags: list[NoteTag] = Field(default=[], description="Filter by tags (optional)")
    limit: int = Field(default=10, ge=1, le=50)


class SearchNotesOutput(BaseModel):
    results: list[Note]
    total: int
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    next_step: str
    context_summary: str
    event_id: str


class CreateTaskInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    tags: list[NoteTag] = Field(default=[])


class CreateTaskOutput(BaseModel):
    note: Note
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    next_step: str
    context_summary: str
    event_id: str
