"""
Simple Rate Limiter for API Calls
Prevents hitting OpenRouter/Gemini rate limits
"""

import time
from threading import Lock
from collections import deque
from datetime import datetime, timedelta

class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds (default 60s = 1 minute)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()

    def acquire(self):
        """
        Wait if necessary to acquire permission for API call
        Blocks until request is allowed
        """
        with self.lock:
            now = datetime.now()

            # Remove old requests outside time window
            cutoff = now - timedelta(seconds=self.time_window)
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            # If at capacity, wait
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest = self.requests[0]
                wait_until = oldest + timedelta(seconds=self.time_window)
                wait_seconds = (wait_until - now).total_seconds()

                if wait_seconds > 0:
                    print(f"⏳ Rate limit: waiting {wait_seconds:.1f}s...")
                    time.sleep(wait_seconds + 0.1)  # Add small buffer

                    # Clean up again after waiting
                    now = datetime.now()
                    cutoff = now - timedelta(seconds=self.time_window)
                    while self.requests and self.requests[0] < cutoff:
                        self.requests.popleft()

            # Record this request
            self.requests.append(now)

    def can_make_request(self) -> bool:
        """Check if request can be made without blocking"""
        with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.time_window)

            # Remove old requests
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            return len(self.requests) < self.max_requests


# Global rate limiter instances
openrouter_limiter = RateLimiter(max_requests=8, time_window=60)  # 8 req/min (safe buffer)
gemini_limiter = RateLimiter(max_requests=12, time_window=60)      # 12 req/min (safe buffer)
