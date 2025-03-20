"""
API Rate Limiter for arXiv API.

This module provides a rate limiting class to prevent excessive requests to the arXiv API.
"""

import threading
import time
import collections
from typing import Dict, Any, Deque
from .logger import setup_logging

logger = setup_logging()


class RateLimiter:
    """Rate limiter to prevent excessive requests to the arXiv API."""

    def __init__(self, max_calls_per_minute: int = 30, max_calls_per_day: int = 2000, min_interval_seconds: float = 1.0):
        """Initialize rate limiter with limits.

        Args:
            max_calls_per_minute: Maximum number of API calls allowed per minute
            max_calls_per_day: Maximum number of API calls allowed per day
            min_interval_seconds: Minimum interval between consecutive API calls in seconds
        """
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_day = max_calls_per_day
        self.min_interval_seconds = min_interval_seconds

        # Thread safe collections for tracking API calls
        self.minute_calls: Deque[float] = collections.deque(maxlen=max_calls_per_minute)
        self.day_calls: Deque[float] = collections.deque(maxlen=max_calls_per_day)

        # Lock for thread safety
        self.lock = threading.RLock()

        # Metrics
        self.total_calls = 0
        self.total_wait_time = 0.0
        self.last_call_time = 0.0

        logger.info(f"Rate limiter initialized: {max_calls_per_minute} calls/minute, " f"{max_calls_per_day} calls/day, min interval: {min_interval_seconds}s")

    def wait_if_needed(self) -> None:
        """Check current rate and wait if limits would be exceeded."""
        with self.lock:
            now = time.time()
            minute_ago = now - 60
            day_ago = now - 86400  # 24 hours in seconds

            # Check minimum interval between API calls
            if self.last_call_time > 0 and self.min_interval_seconds > 0:
                time_since_last_call = now - self.last_call_time
                if time_since_last_call < self.min_interval_seconds:
                    # Need to wait to meet minimum interval
                    wait_time = self.min_interval_seconds - time_since_last_call
                    logger.info(f"Rate limit: Enforcing minimum interval, waiting {wait_time:.2f}s between API calls")
                    time.sleep(wait_time)
                    self.total_wait_time += wait_time
                    # Update current time after waiting
                    now = time.time()

            # Clean up old timestamps
            while self.minute_calls and self.minute_calls[0] < minute_ago:
                self.minute_calls.popleft()
            while self.day_calls and self.day_calls[0] < day_ago:
                self.day_calls.popleft()

            # Check minute limit
            if len(self.minute_calls) >= self.max_calls_per_minute:
                # Calculate wait time
                wait_time = 60 - (now - self.minute_calls[0])
                if wait_time > 0:
                    logger.info(f"Rate limit: Reached minute limit ({len(self.minute_calls)}/{self.max_calls_per_minute}), " f"waiting {wait_time:.2f} seconds")
                    time.sleep(wait_time)
                    self.total_wait_time += wait_time
                    # Recalculate time after waiting
                    now = time.time()

            # Check day limit
            if len(self.day_calls) >= self.max_calls_per_day:
                # Calculate wait time
                wait_time = 86400 - (now - self.day_calls[0])
                if wait_time > 0:
                    logger.info(f"Rate limit: Reached daily limit ({len(self.day_calls)}/{self.max_calls_per_day}), " f"waiting {wait_time:.2f} seconds")
                    time.sleep(wait_time)
                    self.total_wait_time += wait_time
                    # Recalculate time after waiting
                    now = time.time()

            # Record this call
            self.minute_calls.append(now)
            self.day_calls.append(now)
            self.total_calls += 1
            self.last_call_time = now

            if self.total_calls % 100 == 0:
                logger.info(f"Rate limiter stats: {self.total_calls} total calls, " f"{self.total_wait_time:.2f}s total wait time")

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self.lock:
            now = time.time()
            minute_ago = now - 60
            day_ago = now - 86400

            # Count recent calls without modifying the queues
            minute_count = sum(1 for ts in self.minute_calls if ts > minute_ago)
            day_count = sum(1 for ts in self.day_calls if ts > day_ago)

            return {
                "total_calls": self.total_calls,
                "total_wait_time": f"{self.total_wait_time:.2f}s",
                "calls_last_minute": minute_count,
                "calls_last_day": day_count,
                "minute_limit": self.max_calls_per_minute,
                "day_limit": self.max_calls_per_day,
                "min_interval": f"{self.min_interval_seconds:.2f}s",
            }
