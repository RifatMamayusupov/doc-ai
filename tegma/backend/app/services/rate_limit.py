"""Rate limiting middleware and utilities."""

from datetime import datetime
from typing import Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.services.redis import redis_client


class RateLimiter:
    """
    Rate limiter middleware using Redis.
    
    Applies different limits based on:
    - Anonymous vs authenticated users
    - Endpoint type (API vs WebSocket)
    """

    # Default limits
    DEFAULT_LIMITS = {
        'anonymous': {'requests': 30, 'window': 60},      # 30/min
        'authenticated': {'requests': 100, 'window': 60}, # 100/min
        'websocket': {'requests': 500, 'window': 60},     # 500/min for WS
        'upload': {'requests': 10, 'window': 60},         # 10 uploads/min
        'agent': {'requests': 20, 'window': 60},          # 20 agent calls/min
    }

    def __init__(
        self,
        limit_type: str = 'authenticated',
        custom_limit: int | None = None,
        custom_window: int | None = None,
    ) -> None:
        """
        Initialize rate limiter.
        
        Args:
            limit_type: Type of rate limit to apply
            custom_limit: Override max requests
            custom_window: Override window in seconds
        """
        limits = self.DEFAULT_LIMITS.get(limit_type, self.DEFAULT_LIMITS['authenticated'])
        self.max_requests = custom_limit or limits['requests']
        self.window_seconds = custom_window or limits['window']
        self.limit_type = limit_type

    async def __call__(
        self,
        request: Request,
    ) -> None:
        """FastAPI dependency to check rate limit."""
        # Get identifier (user_id or IP)
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            identifier = f"user:{user_id}"
        else:
            identifier = f"ip:{request.client.host}"

        key = f"rate:{self.limit_type}:{identifier}"

        try:
            allowed, remaining = await redis_client.check_rate_limit(
                key,
                self.max_requests,
                self.window_seconds,
            )

            # Add rate limit headers
            request.state.rate_limit_remaining = remaining
            request.state.rate_limit_limit = self.max_requests
            request.state.rate_limit_reset = self.window_seconds

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": self.max_requests,
                        "window": self.window_seconds,
                        "retry_after": self.window_seconds,
                    },
                )

        except Exception as e:
            # If Redis is down, allow request but log
            print(f"Rate limit check failed: {e}")


class RateLimitMiddleware:
    """Middleware to add rate limit headers to all responses."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))

                # Add rate limit headers if available
                if hasattr(scope.get("state", {}), "rate_limit_remaining"):
                    state = scope["state"]
                    headers[b"x-ratelimit-limit"] = str(state.rate_limit_limit).encode()
                    headers[b"x-ratelimit-remaining"] = str(state.rate_limit_remaining).encode()
                    headers[b"x-ratelimit-reset"] = str(state.rate_limit_reset).encode()

                message["headers"] = list(headers.items())

            await send(message)

        await self.app(scope, receive, send_wrapper)


# Pre-configured limiters
rate_limit_api = RateLimiter('authenticated')
rate_limit_anonymous = RateLimiter('anonymous')
rate_limit_upload = RateLimiter('upload')
rate_limit_agent = RateLimiter('agent')
rate_limit_websocket = RateLimiter('websocket')


def create_rate_limiter(
    requests: int,
    window: int = 60,
) -> RateLimiter:
    """Create a custom rate limiter."""
    return RateLimiter(
        limit_type='custom',
        custom_limit=requests,
        custom_window=window,
    )
