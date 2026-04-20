from dataclasses import dataclass, field

import httpx


class WebhookDeliveryError(Exception):
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Webhook delivery failed with status {status_code}")


@dataclass
class WebhookClient:
    timeout: int = 10
    extra_headers: dict[str, str] = field(default_factory=dict)

    def dispatch(self, url: str, event_type: str, payload: dict) -> int:  # type: ignore[type-arg]
        headers = {
            "Content-Type": "application/json",
            "X-Event-Type": event_type,
            **self.extra_headers,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url, json={"event_type": event_type, "payload": payload}, headers=headers
            )

        if response.status_code >= 500:
            raise WebhookDeliveryError(response.status_code, response.text)

        return response.status_code
