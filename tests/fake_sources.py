"""Fake calendar servers for the tests: answers by URL, through httpx.MockTransport (no network)."""

import httpx


class FakeWeb:
    def __init__(self):
        # url -> (status, body) or an exception class to raise
        self.routes: dict[str, object] = {}
        self.requests: list[httpx.Request] = []
        self.dav = FakeCalDAV()

    def set(self, url: str, body: str = "", status: int = 200) -> None:
        self.routes[url] = (status, body)

    def fail(self, url: str, error=httpx.ConnectError) -> None:
        self.routes[url] = error

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host.endswith("caldav.icloud.com"):
            return self.dav.handler(request)
        route = self.routes.get(str(request.url))
        if route is None:
            return httpx.Response(404, text="not found")
        if isinstance(route, type) and issubclass(route, Exception):
            # httpx puts the URL into its messages: exactly what must never reach a log or the database
            raise route(f"cannot connect to {request.url}", request=request)
        status, body = route
        return httpx.Response(status, text=body)


PRINCIPAL = "https://caldav.icloud.com/123456/principal/"
HOME = "https://p42-caldav.icloud.com/123456/calendars/"


class FakeCalDAV:
    """iCloud's CalDAV as far as the planner uses it: discovery on caldav.icloud.com leads to the shard host p42."""

    def __init__(self, apple_id="familie@example.com", password="abcd-efgh-ijkl-mnop"):
        self.apple_id, self.password = apple_id, password
        # href -> {"name", "ctag", "component", "events": {event href: ics text}}
        self.calendars: dict[str, dict] = {}
        self.reports: list[str] = []

    def calendar(self, slug: str, name: str, events: dict[str, str] | None = None, component="VEVENT") -> str:
        href = f"{HOME}{slug}/"
        self.calendars[href] = {"name": name, "ctag": "1", "component": component, "events": events or {}}
        return href

    def change(self, href: str, events: dict[str, str]) -> None:
        self.calendars[href]["events"] = events
        self.calendars[href]["ctag"] = str(int(self.calendars[href]["ctag"]) + 1)

    @staticmethod
    def _multistatus(*responses: str) -> httpx.Response:
        body = ('<?xml version="1.0"?><d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" '
                'xmlns:cs="http://calendarserver.org/ns/">' + "".join(responses) + "</d:multistatus>")
        return httpx.Response(207, text=body, headers={"Content-Type": "application/xml"})

    @staticmethod
    def _response(href: str, props: str) -> str:
        return f"<d:response><d:href>{href}</d:href><d:propstat><d:prop>{props}</d:prop>" \
               "<d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>"

    def handler(self, request: httpx.Request) -> httpx.Response:
        import base64

        expected = "Basic " + base64.b64encode(f"{self.apple_id}:{self.password}".encode()).decode()
        if request.headers.get("Authorization") != expected:
            return httpx.Response(401)
        url, method, body = str(request.url), request.method, request.content.decode()
        if method == "PROPFIND" and url == "https://caldav.icloud.com/":
            # A relative href, as iCloud answers
            return self._multistatus(self._response(
                "/", "<d:current-user-principal><d:href>/123456/principal/</d:href></d:current-user-principal>"))
        if method == "PROPFIND" and url == PRINCIPAL:
            return self._multistatus(self._response(
                "/123456/principal/", f"<c:calendar-home-set><d:href>{HOME}</d:href></c:calendar-home-set>"))
        if method == "PROPFIND" and url == HOME and request.headers.get("Depth") == "1":
            items = [self._response("/123456/calendars/", "<d:resourcetype><d:collection/></d:resourcetype>")]
            for href, cal in self.calendars.items():
                items.append(self._response(
                    href.removeprefix("https://p42-caldav.icloud.com"),
                    f"<d:displayname>{cal['name']}</d:displayname>"
                    "<d:resourcetype><d:collection/><c:calendar/></d:resourcetype>"
                    f"<cs:getctag>{cal['ctag']}</cs:getctag>"
                    f"<c:supported-calendar-component-set><c:comp name=\"{cal['component']}\"/>"
                    "</c:supported-calendar-component-set>"))
            return self._multistatus(*items)
        if method == "REPORT" and url in self.calendars:
            assert "time-range" in body
            self.reports.append(url)
            items = []
            for href, text in self.calendars[url]["events"].items():
                escaped = text.replace("&", "&amp;").replace("<", "&lt;")
                items.append(self._response(href.removeprefix("https://p42-caldav.icloud.com"),
                                            f"<d:getetag>\"e-{len(text)}\"</d:getetag>"
                                            f"<c:calendar-data>{escaped}</c:calendar-data>"))
            return self._multistatus(*items)
        return httpx.Response(404)
