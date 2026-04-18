import pytest
from pytest_httpx import HTTPXMock

from mcp_business_workflows.adapters.webhook_client import WebhookClient, WebhookDeliveryError
from mcp_business_workflows.schemas.webhooks import DispatchWebhookInput
from mcp_business_workflows.services.webhook_service import WebhookService

URL = "https://hooks.example.com/events"


@pytest.fixture()
def client() -> WebhookClient:
    return WebhookClient()


@pytest.fixture()
def service(client: WebhookClient) -> WebhookService:
    return WebhookService(client, default_url=URL)


class TestWebhookClient:
    def test_dispatches_successfully(self, client: WebhookClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=200)
        status = client.dispatch(URL, "task.created", {"id": "123"})
        assert status == 200

    def test_raises_on_5xx(self, client: WebhookClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=503)
        with pytest.raises(WebhookDeliveryError) as exc_info:
            client.dispatch(URL, "task.created", {})
        assert exc_info.value.status_code == 503

    def test_4xx_does_not_raise(self, client: WebhookClient, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400)
        status = client.dispatch(URL, "task.created", {})
        assert status == 400


class TestWebhookService:
    def test_successful_dispatch_returns_structured_output(
        self, service: WebhookService, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(status_code=200)
        out = service.dispatch(DispatchWebhookInput(event_type="task.created", payload={"id": "1"}))
        assert out.success is True
        assert out.status_code == 200
        assert out.event_id
        assert 0.0 <= out.confidence <= 1.0

    def test_sensitive_event_requires_human_review(
        self, service: WebhookService, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(status_code=200)
        out = service.dispatch(DispatchWebhookInput(event_type="deploy.triggered"))
        assert out.requires_human_review is True
        assert out.recommended_action == "confirm_downstream"

    def test_non_sensitive_event_no_review(
        self, service: WebhookService, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(status_code=200)
        out = service.dispatch(DispatchWebhookInput(event_type="task.created"))
        assert out.requires_human_review is False
        assert out.recommended_action == "continue_workflow"

    def test_failed_delivery_requires_human_review(
        self, service: WebhookService, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(status_code=503)
        out = service.dispatch(DispatchWebhookInput(event_type="task.created"))
        assert out.success is False
        assert out.requires_human_review is True
        assert out.recommended_action == "retry_or_escalate"
        assert out.confidence == 0.0

    def test_uses_default_url_when_not_provided(
        self, service: WebhookService, httpx_mock: HTTPXMock
    ) -> None:
        httpx_mock.add_response(status_code=200)
        out = service.dispatch(DispatchWebhookInput(event_type="ping"))
        assert out.url == URL
