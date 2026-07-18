import time
from collections import defaultdict
from fastapi import Request, HTTPException


class RateLimiter:
    """Simple in-memory rate limiter per IP address."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request) -> None:
        client_ip = self._get_client_ip(request)
        now = time.time()
        cutoff = now - self.window_seconds

        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > cutoff
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )

        self._requests[client_ip].append(now)


rate_limiter = RateLimiter(max_requests=15, window_seconds=60)
auth_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
