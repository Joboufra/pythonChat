import time
from collections import defaultdict
from fastapi import Request, HTTPException, status


class RateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(self, identifier: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds

        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > cutoff
        ]

        if len(self.requests[identifier]) >= self.max_requests:
            return True

        self.requests[identifier].append(now)
        return False


auth_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)
message_rate_limiter = RateLimiter(max_requests=30, window_seconds=10)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
