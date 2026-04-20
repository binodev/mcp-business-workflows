from unittest.mock import patch

import pytest

from mcp_business_workflows.schemas.status import (
    ConnectorHealth,
    ConnectorStatus,
    GetSystemStatusInput,
)
from mcp_business_workflows.services.status_service import (
    StatusService,
    _check_github,
    _check_webhook,
)


@pytest.fixture()
def service() -> StatusService:
    return StatusService()


def _healthy(name: str) -> ConnectorHealth:
    return ConnectorHealth(name=name, status=ConnectorStatus.healthy, detail="ok")


def _unreachable(name: str) -> ConnectorHealth:
    return ConnectorHealth(name=name, status=ConnectorStatus.unreachable, detail="timeout")


class TestCheckGithub:
    def test_healthy_when_token_set_and_api_responds(self) -> None:
        with patch("mcp_business_workflows.services.status_service.httpx.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"rate": {"remaining": 4999}}
            result = _check_github("valid-token")
        assert result.status == ConnectorStatus.healthy
        assert "4999" in result.detail

    def test_unconfigured_when_no_token(self) -> None:
        result = _check_github("")
        assert result.status == ConnectorStatus.unconfigured

    def test_unreachable_on_timeout(self) -> None:
        import httpx as httpx_lib

        with patch("mcp_business_workflows.services.status_service.httpx.get") as mock_get:
            mock_get.side_effect = httpx_lib.TimeoutException("timeout")
            result = _check_github("token")
        assert result.status == ConnectorStatus.unreachable

    def test_degraded_on_unexpected_status(self) -> None:
        with patch("mcp_business_workflows.services.status_service.httpx.get") as mock_get:
            mock_get.return_value.status_code = 403
            mock_get.return_value.json.return_value = {}
            result = _check_github("token")
        assert result.status == ConnectorStatus.degraded


class TestCheckWebhook:
    def test_healthy_when_url_configured(self) -> None:
        result = _check_webhook("https://hooks.example.com")
        assert result.status == ConnectorStatus.healthy

    def test_unconfigured_when_no_url(self) -> None:
        result = _check_webhook("")
        assert result.status == ConnectorStatus.unconfigured


class TestStatusService:
    def test_overall_healthy_when_all_connectors_ok(self, service: StatusService) -> None:
        with patch(
            "mcp_business_workflows.services.status_service._CHECKERS",
            {
                "github": lambda: _healthy("github"),
                "webhook": lambda: _healthy("webhook"),
            },
        ):
            out = service.get_status(GetSystemStatusInput())
        assert out.overall == ConnectorStatus.healthy
        assert out.requires_human_review is False
        assert out.recommended_action == "system_operational"

    def test_requires_human_review_when_connector_unreachable(self, service: StatusService) -> None:
        with patch(
            "mcp_business_workflows.services.status_service._CHECKERS",
            {
                "github": lambda: _unreachable("github"),
                "webhook": lambda: _healthy("webhook"),
            },
        ):
            out = service.get_status(GetSystemStatusInput())
        assert out.requires_human_review is True
        assert out.overall == ConnectorStatus.degraded
        assert out.recommended_action == "investigate_connectors"

    def test_returns_structured_output(self, service: StatusService) -> None:
        with patch(
            "mcp_business_workflows.services.status_service._CHECKERS",
            {
                "github": lambda: _healthy("github"),
                "webhook": lambda: _healthy("webhook"),
            },
        ):
            out = service.get_status(GetSystemStatusInput())
        assert out.event_id
        assert out.next_step
        assert out.context_summary
        assert 0.0 <= out.confidence <= 1.0
