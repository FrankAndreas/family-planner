"""The one HTTP client for calendar sources. Tests replace `transport` with a fake (tests/fake_sources.py)."""

import httpx

TIMEOUT_SECONDS = 20
transport: httpx.BaseTransport | None = None


def client(**options) -> httpx.Client:
    return httpx.Client(
        transport=transport,
        timeout=TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={"User-Agent": "family-planner"},
        **options,
    )
