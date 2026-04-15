"""Resilience utilities for external API calls — retry + circuit breaker patterns."""

import logging
from collections.abc import Callable
from functools import wraps

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def _log_retry(retry_state: RetryCallState) -> None:
    logger.warning(
        "Retrying %s (attempt %d): %s",
        retry_state.fn.__name__ if retry_state.fn else "unknown",
        retry_state.attempt_number,
        retry_state.outcome.exception() if retry_state.outcome else "unknown",
    )


def marketplace_retry(max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 30.0):
    """Decorator for marketplace API calls with exponential backoff."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        before_sleep=_log_retry,
        reraise=True,
    )


class CircuitBreaker:
    """Simple circuit breaker. Opens after `threshold` consecutive failures,
    stays open for `recovery_timeout` seconds."""

    def __init__(self, threshold: int = 5, recovery_timeout: float = 60.0):
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._open_since: float | None = None

    @property
    def is_open(self) -> bool:
        if self._open_since is None:
            return False
        import time
        elapsed = time.monotonic() - self._open_since
        if elapsed >= self.recovery_timeout:
            self._half_open()
            return False
        return True

    def record_success(self) -> None:
        self._failure_count = 0
        self._open_since = None

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self.threshold:
            import time
            self._open_since = time.monotonic()

    def _half_open(self) -> None:
        self._failure_count = 0
        self._open_since = None

    def __call__(self, fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            if self.is_open:
                from app.core.exceptions import PlatformAPIError
                raise PlatformAPIError("unknown", "Circuit breaker is open")
            try:
                result = await fn(*args, **kwargs)
                self.record_success()
                return result
            except Exception:
                self.record_failure()
                raise
        return wrapper
