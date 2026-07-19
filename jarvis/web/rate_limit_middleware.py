"""Rate limiting middleware for all API endpoints."""

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiter middleware.

    Limits per IP:
    - POST/PUT/PATCH: 30 per 60s (stricter for expensive endpoints)
    - GET: no limit (read-only, safe)
    """

    def __init__(self, app, max_post: int = 30, window: int = 60):
        super().__init__(app)
        self.max_post = max_post
        self.window = window
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            client_ip = request.client.host if request.client else "unknown"
            path = request.url.path
            key = f"{client_ip}:{path}"
            now = time.time()
            cutoff = now - self.window

            self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]

            if len(self._buckets[key]) >= self.max_post:
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Rate limit exceeded for {path}. Try again shortly."},
                    headers={"Retry-After": str(self.window)},
                )
            self._buckets[key].append(now)

        return await call_next(request)
