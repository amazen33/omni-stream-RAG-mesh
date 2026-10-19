"""ASGI HTTP instrumentation; the registry itself remains standard-library only."""
from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .metrics import http_in_flight, observe_http_request


class HTTPMetricsMiddleware:
    """Observe the entire response without buffering or changing HTTP behavior."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = perf_counter()
        status = 500
        http_in_flight(1)

        async def observe_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, observe_send)
        finally:
            # Routing populates this after entry; never fall back to the raw path.
            route = getattr(scope.get("route"), "path", None) or "unmatched"
            observe_http_request(route, scope["method"], status, perf_counter() - started)
            http_in_flight(-1)
