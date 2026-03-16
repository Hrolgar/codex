"""Provider-agnostic API rate limiter with request queue."""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class ProviderRateLimiter:
    """Rate limiter for external API providers using minimum-interval enforcement."""

    def __init__(
        self,
        name: str,
        min_interval_seconds: float = 1.0,
    ) -> None:
        self.name = name
        self.min_interval_seconds = min_interval_seconds
        self._last_request_time: float = 0.0
        self._lock: asyncio.Lock | None = None

    async def acquire(self) -> None:
        """Block until a request slot is available, enforcing min interval."""
        if self._lock is None:
            self._lock = asyncio.Lock()
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


def _register(name: str, interval: float) -> None:
    _limiters[name] = ProviderRateLimiter(name, min_interval_seconds=interval)


# Pre-register known providers
_register("hardcover", interval=1.0)
_register("openlibrary", interval=0.5)
_register("google_books", interval=0.5)
