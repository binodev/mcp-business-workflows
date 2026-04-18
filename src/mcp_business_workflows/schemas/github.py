from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class IssueState(StrEnum):
    open = "open"
    closed = "closed"
    all = "all"


class GitHubIssue(BaseModel):
    number: int
    title: str
    state: str
    url: str
    labels: list[str]
    created_at: datetime
    updated_at: datetime
    author: str


class ListOpenIssuesInput(BaseModel):
    repo: str = Field("", description="owner/repo — falls back to GITHUB_DEFAULT_REPO if empty")
    state: IssueState = Field(IssueState.open, description="Issue state filter")
    labels: list[str] = Field(default=[], description="Filter by label names")
    limit: int = Field(default=20, ge=1, le=100)


class ListOpenIssuesOutput(BaseModel):
    issues: list[GitHubIssue]
    total: int
    repo: str
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    next_step: str
    context_summary: str
    event_id: str
