"""
config/rate_limit.py — Simple in-memory rate limiter.

Design Pattern: Decorator / Middleware
Limits repeated requests from the same IP to prevent brute force.
No external dependencies (no Redis).
"""

import time
from collections import defaultdict
from fastapi import HTTPException, Request

# Store: { ip: [timestamp, timestamp, ...] }
_requests: dict[str, list[float]] = defaultdict(list)

# Default: 5 requests per 60 seconds
DEFAULT_LIMIT = 5
DEFAULT_WINDOW = 60  # seconds


def check_rate_limit(
    request: Request,
    limit: int = DEFAULT_LIMIT,
    window: int = DEFAULT_WINDOW
):
    """
    Call at the start of any endpoint to enforce rate limiting.
    Raises HTTP 429 if the client exceeds the limit.
    """
    ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Clean old entries outside the window
    _requests[ip] = [t for t in _requests[ip] if now - t < window]

    if len(_requests[ip]) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )

    _requests[ip].append(now)
