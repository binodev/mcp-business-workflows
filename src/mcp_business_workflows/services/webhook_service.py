from mcp_business_workflows.adapters.webhook_client import WebhookClient, WebhookDeliveryError
from mcp_business_workflows.logging import get_logger, new_event_id
from mcp_business_workflows.schemas.webhooks import DispatchWebhookInput, DispatchWebhookOutput

log = get_logger(__name__)

SENSITIVE_EVENT_PREFIXES = ("deploy.", "rollback.", "incident.", "alert.")


class WebhookService:
    def __init__(self, client: WebhookClient, default_url: str = "") -> None:
        self._client = client
        self._default_url = default_url

    def dispatch(self, inp: DispatchWebhookInput) -> DispatchWebhookOutput:
        event_id = new_event_id()
        url = inp.url or self._default_url
        is_sensitive = inp.event_type.startswith(SENSITIVE_EVENT_PREFIXES)

        try:
            status_code = self._client.dispatch(url, inp.event_type, inp.payload)
            success = 200 <= status_code < 300

            log.info(
                "webhook.dispatched",
                event_id=event_id,
                url=url,
                event_type=inp.event_type,
                status_code=status_code,
                success=success,
            )

            return DispatchWebhookOutput(
                url=url,
                event_type=inp.event_type,
                status_code=status_code,
                success=success,
                recommended_action="confirm_downstream" if is_sensitive else "continue_workflow",
                confidence=0.95 if success else 0.4,
                requires_human_review=is_sensitive,
                next_step=(
                    f"Event '{inp.event_type}' delivered (HTTP {status_code}). "
                    + ("Verify downstream systems received it." if is_sensitive else "No further action needed.")
                ),
                context_summary=f"Webhook '{inp.event_type}' → {url} — HTTP {status_code}.",
                event_id=event_id,
            )

        except WebhookDeliveryError as exc:
            log.error(
                "webhook.failed",
                event_id=event_id,
                url=url,
                event_type=inp.event_type,
                status_code=exc.status_code,
            )
            return DispatchWebhookOutput(
                url=url,
                event_type=inp.event_type,
                status_code=exc.status_code,
                success=False,
                recommended_action="retry_or_escalate",
                confidence=0.0,
                requires_human_review=True,
                next_step=f"Webhook delivery failed (HTTP {exc.status_code}). Investigate target endpoint and retry.",
                context_summary=f"Webhook '{inp.event_type}' → {url} — FAILED with HTTP {exc.status_code}.",
                event_id=event_id,
            )
