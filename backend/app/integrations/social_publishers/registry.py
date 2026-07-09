from app.integrations.social_publishers.base import SocialPublisher
from app.integrations.social_publishers.webhook_bridge import WebhookBridgePublisher


class SocialPublisherRegistry:
    _publishers = {
        "webhook_bridge": WebhookBridgePublisher,
    }

    @classmethod
    def get_publisher(cls, publisher_type: str, config: dict) -> SocialPublisher:
        publisher_cls = cls._publishers.get(publisher_type)
        if not publisher_cls:
            raise ValueError(f"Unsupported social publisher type: {publisher_type}")
        return publisher_cls(config)
