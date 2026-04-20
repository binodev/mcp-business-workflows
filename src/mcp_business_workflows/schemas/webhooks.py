from pydantic import BaseModel, Field


class DispatchWebhookInput(BaseModel):
    url: str = Field(
        "", description="Webhook target URL — falls back to WEBHOOK_DEFAULT_URL if empty"
    )
    event_type: str = Field(..., description="Event name (e.g. 'deployment.triggered')")
    payload: dict = Field(default_factory=dict, description="Arbitrary JSON payload")  # type: ignore[type-arg]


class DispatchWebhookOutput(BaseModel):
    url: str
    event_type: str
    status_code: int
    success: bool
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    next_step: str
    context_summary: str
    event_id: str
