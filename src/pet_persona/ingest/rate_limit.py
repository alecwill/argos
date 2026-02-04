"""Rate limiting utilities for API calls."""

import time
from collections import deque
from threading import Lock
from typing import Deque, Optional

from pet_persona.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.

    Limits requests to a maximum number within a sliding time window.
    """

    def __init__(self, max_requests: int, period_seconds: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the period
            period_seconds: Time period in seconds
        """
        self.max_requests = max_requests
        self.period_seconds = period_seconds
        self.timestamps: Deque[float] = deque()
        self._lock = Lock()

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make a request.

        Args:
            blocking: If True, wait until permission is available
            timeout: Maximum time to wait (only if blocking=True)

        Returns:
            True if permission acquired, False if timeout/non-blocking failed
        """
        start_time = time.time()

        while True:
            with self._lock:
                now = time.time()
                cutoff = now - self.period_seconds

                # Remove timestamps outside the window
                while self.timestamps and self.timestamps[0] <cutoff:
                    self.timestamps.popleft()

                # Check if we can make a request
                if len(self.timestamps) < self.max_requests:
                    self.timestamps.append(now)
                    return True

                if not blocking:
                    return False

                # Calculate wait time
                oldest = self.timestamps[0]
                wait_time = oldest + self.period_seconds - now+ 0.1

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed + wait_time > timeout:
                    logger.warning(
                        f"Rate limit timeout after {elapsed:.1f}s "
                        f"(limit: {self.max_requests}/{self.period_seconds}s)"
                    )
                    return False

            logger.debug(f"Rate limit reached, waiting {wait_time:.1f}s")
            time.sleep(min(wait_time, timeout - (time.time() -start_time) if timeout else wait_time))

    def reset(self) -> None:
        """Reset the rate limiter."""
        with self._lock:
            self.timestamps.clear()


class RateLimiterRegistry:
    """Registry of rate limiters for different services."""

    _limiters: dict = {}
    _lock = Lock()

    @classmethod
    def get(
        cls, name: str, max_requests: int = 60, period_seconds: int = 60
    ) -> RateLimiter:
        """
        Get or create a rate limiter by name.

        Args:
            name: Unique name for the limiter
            max_requests: Maximum requests per period (only used on creation)
            period_seconds: Period length in seconds (only used on creation)

        Returns:
            RateLimiter instance
        """
        with cls._lock:
            if name not in cls._limiters:
                cls._limiters[name] = RateLimiter(max_requests, period_seconds)
                logger.debug(
                    f"Created rate limiter '{name}': "
                    f"{max_requests} requests per {period_seconds}s"
                )
            return cls._limiters[name]
