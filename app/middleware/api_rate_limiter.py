"""
API Rate Limiter Middleware — Per-IP, per-endpoint throttling.
Protects external API quotas and prevents abuse.
"""

import time
import logging
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Rate limits per endpoint prefix: (max_requests, window_seconds)
ENDPOINT_LIMITS = {
    "/api/news": (30, 60),
    "/api/market": (60, 60),
    "/api/alerts": (30, 60),
    "/api/intelligence": (20, 60),
    "/api/run-intelligence": (5, 60),
    "/api/portfolio": (30, 60),
    "/api/graph": (20, 60),
    "/api/relationships": (10, 60),
}

# Global limit per IP (across all endpoints)
GLOBAL_LIMIT = (120, 60)  # 120 requests per minute


class RateLimitState:
    """Track request timestamps per IP per endpoint."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check_and_record(self, key: str, max_requests: int, window: int) -> tuple[bool, int]:
        """
        Check if request is allowed and record it.
        Returns (allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window

        # Clean old entries
        timestamps = self._requests[key]
        self._requests[key] = [t for t in timestamps if t > cutoff]

        if len(self._requests[key]) >= max_requests:
            # Calculate retry-after from oldest request in window
            oldest = min(self._requests[key])
            retry_after = int(oldest + window - now) + 1
            return False, retry_after

        self._requests[key].append(now)
        return True, 0


_state = RateLimitState()


class APIRateLimiterMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for per-IP, per-endpoint rate limiting."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health check
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check global limit
        global_key = f"global:{client_ip}"
        allowed, retry_after = _state.check_and_record(
            global_key, GLOBAL_LIMIT[0], GLOBAL_LIMIT[1]
        )
        if not allowed:
            return self._rate_limit_response(retry_after)

        # Check endpoint-specific limit
        for prefix, (max_req, window) in ENDPOINT_LIMITS.items():
            if request.url.path.startswith(prefix):
                endpoint_key = f"{prefix}:{client_ip}"
                allowed, retry_after = _state.check_and_record(
                    endpoint_key, max_req, window
                )
                if not allowed:
                    return self._rate_limit_response(retry_after, prefix)
                break

        response = await call_next(request)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP from request headers."""
        # Check forwarded headers (reverse proxy)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    @staticmethod
    def _rate_limit_response(retry_after: int, endpoint: str = "") -> Response:
        detail = f"Rate limit exceeded{' for ' + endpoint if endpoint else ''}. "
        detail += f"Retry after {retry_after} seconds."

        return Response(
            content=f'{{"error": "rate_limited", "detail": "{detail}", "retry_after": {retry_after}}}',
            status_code=429,
            media_type="application/json",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Reset": str(int(time.time()) + retry_after),
            },
        )
