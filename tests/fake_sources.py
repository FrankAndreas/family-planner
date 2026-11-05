"""Fake calendar servers for the tests: answers by URL, through httpx.MockTransport (no network)."""

import httpx


class FakeWeb:
    def __init__(self):
        # url -> (status, body) or an exception class to raise
        self.routes: dict[str, object] = {}
        self.requests: list[httpx.Request] = []

    def set(self, url: str, body: str = "", status: int = 200) -> None:
        self.routes[url] = (status, body)

    def fail(self, url: str, error=httpx.ConnectError) -> None:
        self.routes[url] = error

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes.get(str(request.url))
        if route is None:
            return httpx.Response(404, text="not found")
        if isinstance(route, type) and issubclass(route, Exception):
            # httpx puts the URL into its messages: exactly what must never reach a log or the database
            raise route(f"cannot connect to {request.url}", request=request)
        status, body = route
        return httpx.Response(status, text=body)
