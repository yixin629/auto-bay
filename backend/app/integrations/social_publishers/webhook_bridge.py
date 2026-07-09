import httpx

from app.integrations.social_publishers.base import SocialPublishPayload


class WebhookBridgePublisher:
    def __init__(self, config: dict):
        self.config = config or {}

    async def publish(self, payload: SocialPublishPayload) -> dict:
        endpoint = self.config.get("endpoint")
        if not endpoint:
            raise ValueError("webhook_bridge endpoint is required")

        headers = {"Content-Type": "application/json"}
        token = self.config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        timeout = float(self.config.get("timeout_seconds") or 20)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, json=dict(payload), headers=headers)
            response.raise_for_status()
            data = response.json() if response.content else {}

        return data if isinstance(data, dict) else {"raw": data}
