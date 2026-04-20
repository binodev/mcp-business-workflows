import httpx

from mcp_business_workflows.config import settings
from mcp_business_workflows.logging import get_logger, new_event_id
from mcp_business_workflows.schemas.status import (
    ConnectorHealth,
    ConnectorStatus,
    GetSystemStatusInput,
    GetSystemStatusOutput,
)

log = get_logger(__name__)

ALL_CONNECTORS = ["github", "webhook"]


def _check_github(token: str) -> ConnectorHealth:
    if not token:
        return ConnectorHealth(
            name="github", status=ConnectorStatus.unconfigured, detail="GITHUB_TOKEN not set"
        )
    try:
        r = httpx.get(
            "https://api.github.com/rate_limit",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if r.status_code == 200:
            remaining = r.json().get("rate", {}).get("remaining", "?")
            return ConnectorHealth(
                name="github",
                status=ConnectorStatus.healthy,
                detail=f"Authenticated. Rate limit remaining: {remaining}",
            )
        return ConnectorHealth(
            name="github",
            status=ConnectorStatus.degraded,
            detail=f"Unexpected status {r.status_code}",
        )
    except httpx.TimeoutException:
        return ConnectorHealth(
            name="github", status=ConnectorStatus.unreachable, detail="Request timed out"
        )
    except httpx.RequestError as exc:
        return ConnectorHealth(name="github", status=ConnectorStatus.unreachable, detail=str(exc))


def _check_webhook(default_url: str) -> ConnectorHealth:
    if not default_url:
        return ConnectorHealth(
            name="webhook",
            status=ConnectorStatus.unconfigured,
            detail="WEBHOOK_DEFAULT_URL not set",
        )
    return ConnectorHealth(
        name="webhook", status=ConnectorStatus.healthy, detail=f"Configured → {default_url}"
    )


_CHECKERS = {
    "github": lambda: _check_github(settings.github_token),
    "webhook": lambda: _check_webhook(settings.webhook_default_url),
}


class StatusService:
    def get_status(self, inp: GetSystemStatusInput) -> GetSystemStatusOutput:
        event_id = new_event_id()
        names = [n for n in inp.connectors if n in _CHECKERS] or ALL_CONNECTORS
        results = [_CHECKERS[name]() for name in names]

        unhealthy = [
            r
            for r in results
            if r.status in (ConnectorStatus.unreachable, ConnectorStatus.degraded)
        ]
        unconfigured = [r for r in results if r.status == ConnectorStatus.unconfigured]

        if unhealthy:
            overall = ConnectorStatus.degraded
        elif unconfigured and len(unconfigured) == len(results):
            overall = ConnectorStatus.unconfigured
        else:
            overall = ConnectorStatus.healthy

        requires_review = len(unhealthy) > 0
        log.info("status.checked", event_id=event_id, overall=overall, unhealthy=len(unhealthy))

        return GetSystemStatusOutput(
            connectors=results,
            overall=overall,
            recommended_action="investigate_connectors" if unhealthy else "system_operational",
            confidence=0.95,
            requires_human_review=requires_review,
            next_step=(
                f"{len(unhealthy)} connector(s) unreachable"
                " — investigate before triggering workflows."
                if unhealthy
                else "All connectors operational. Safe to proceed."
            ),
            context_summary=(
                f"System status: {overall}. " + ", ".join(f"{r.name}={r.status}" for r in results)
            ),
            event_id=event_id,
        )
