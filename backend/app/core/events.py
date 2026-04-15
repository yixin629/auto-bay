"""Simple in-process domain event bus."""

from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

EventHandler = Callable[..., Coroutine[Any, Any, None]]

_handlers: dict[str, list[EventHandler]] = defaultdict(list)


def subscribe(event_name: str, handler: EventHandler) -> None:
    _handlers[event_name].append(handler)


async def publish(event_name: str, **kwargs: Any) -> None:
    for handler in _handlers.get(event_name, []):
        await handler(**kwargs)
