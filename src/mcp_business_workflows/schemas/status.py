from enum import StrEnum

from pydantic import BaseModel, Field


class ConnectorStatus(StrEnum):
    healthy = "healthy"
    degraded = "degraded"
    unreachable = "unreachable"
    unconfigured = "unconfigured"


class ConnectorHealth(BaseModel):
    name: str
    status: ConnectorStatus
    detail: str


class GetSystemStatusInput(BaseModel):
    connectors: list[str] = Field(
        default=[],
        description="Connector names to check: 'github', 'webhook'. Empty = check all.",
    )


class GetSystemStatusOutput(BaseModel):
    connectors: list[ConnectorHealth]
    overall: ConnectorStatus
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    next_step: str
    context_summary: str
    event_id: str
