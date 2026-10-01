"""Shared HTTP client for outside services: timeouts, retries and one failure type."""

import asyncio

import httpx

from uavert.config import get_settings


class SourceUnavailable(Exception):
    """An outside service could not be reached or returned an unusable response."""


def make_client() -> httpx.AsyncClient:
    s = get_settings()
    return httpx.AsyncClient(
        timeout=s.http_timeout_s, headers={"User-Agent": s.user_agent}, follow_redirects=True
    )


async def get(client: httpx.AsyncClient, url: str, params: dict | None = None) -> httpx.Response:
    """GET with retries and backoff on network errors, 429 and 5xx. Raises SourceUnavailable."""
    retries = get_settings().http_retries
    for attempt in range(retries + 1):
        try:
            r = await client.get(url, params=params)
            if r.status_code == 429 or r.status_code >= 500:
                raise httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
            r.raise_for_status()
            return r
        except httpx.HTTPError as e:
            if attempt == retries:
                raise SourceUnavailable(f"{url}: {e}") from e
            await asyncio.sleep(2**attempt)
    raise AssertionError("unreachable")


async def get_json(client: httpx.AsyncClient, url: str, params: dict | None = None):
    r = await get(client, url, params)
    try:
        return r.json()
    except ValueError as e:
        raise SourceUnavailable(f"{url}: response was not JSON") from e
