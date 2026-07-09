from typing import Protocol


class SocialPublishPayload(dict):
    pass


class SocialPublisher(Protocol):
    async def publish(self, payload: SocialPublishPayload) -> dict: ...
