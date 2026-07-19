"""Simple in-memory rate limiter for API endpoints."""

import time
from collections import defaultdict
from functools import wraps
from fastapi import Request, HTTPException


class RateLimiter:
    """Token bucket rate limiter per IP address."""

    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if a request is allowed under the rate limit."""
        now = time.time()
        cutoff = now - window_seconds
        
        # Clean old entries
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]
        
        if len(self._buckets[key]) >= max_requests:
            return False
        
        self._buckets[key].append(now)
        return True

    def remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests in the current window."""
        now = time.time()
        cutoff = now - window_seconds
        recent = [t for t in self._buckets[key] if t > cutoff]
        return max(0, max_requests - len(recent))


# Global instance
_limiter = RateLimiter()


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Decorator for rate-limiting FastAPI endpoints.
    
    Usage:
        @router.post("/api/chat")
        @rate_limit(max_requests=10, window_seconds=60)
        async def chat(request: Request, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            key = f"{func.__module__}:{func.__name__}:{client_ip}"
            
            if not _limiter.is_allowed(key, max_requests, window_seconds):
                remaining = _limiter.remaining(key, max_requests, window_seconds)
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {window_seconds}s.",
                    headers={
                        "Retry-After": str(window_seconds),
                        "X-RateLimit-Remaining": str(remaining),
                    }
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
