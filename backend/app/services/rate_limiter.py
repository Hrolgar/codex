"""Provider-agnostic API rate limiter with request queue."""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class ProviderRateLimiter:
    """Rate limiter for external API providers using a token-bucket approach."""

    def __init__(
        self,
        name: str,
        max_requests_per_minute: int = 60,
        min_interval_seconds: float = 1.0,
    ) -> None:
        self.name = name
        self.max_requests_per_minute = max_requests_per_minute
        self.min_interval_seconds = min_interval_seconds
        self._semaphore = asyncio.Semaphore(max_requests_per_minute)
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a request slot is available, enforcing min interval."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self.min_interval_seconds:
                wait = self.min_interval_seconds - elapsed
                logger.debug(
                    "Rate limiter [%s]: throttling %.2fs", self.name, wait
                )
                await asyncio.sleep(wait)
            self._last_request_time = time.monotonic()


# ---------------------------------------------------------------------------
# Global registry of rate limiters
# ---------------------------------------------------------------------------

_limiters: dict[str, ProviderRateLimiter] = {}


def get_limiter(provider_name: str) -> ProviderRateLimiter:
    """Return the rate limiter for *provider_name*, creating a default if needed."""
    if provider_name not in _limiters:
        logger.warning(
            "No pre-registered rate limiter for '%s'; using defaults", provider_name
        )
        _limiters[provider_name] = ProviderRateLimiter(provider_name)
    return _limiters[provider_name]


def _register(name: str, rpm: int, interval: float) -> None:
    _limiters[name] = ProviderRateLimiter(name, max_requests_per_minute=rpm, min_interval_seconds=interval)


# Pre-register known providers
_register("hardcover", rpm=60, interval=1.0)
_register("openlibrary", rpm=100, interval=0.5)
_register("google_books", rpm=100, interval=0.5)
