"""
Attaches the regulatory disclaimer to every API response as a header.

Payload-level disclaimers only reach endpoints that remember to include
them. The header covers everything, including error responses.
"""
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.disclaimer import DISCLAIMER_SHORT


class DisclaimerHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Disclaimer"] = DISCLAIMER_SHORT
        return response
