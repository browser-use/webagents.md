"""Discover webagents.md manifests from web pages."""

from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx

from webagent.parser import parse
from webagent.types import Manifest

_META_PATTERN = re.compile(
    r"<meta\s+[^>]*name=[\"']webagents-md[\"'][^>]*content=[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

_META_PATTERN_REVERSED = re.compile(
    r"<meta\s+[^>]*content=[\"']([^\"']+)[\"'][^>]*name=[\"']webagents-md[\"']",
    re.IGNORECASE,
)


async def discover_manifest_url(page_url: str, *, client: httpx.AsyncClient | None = None) -> str | None:
    """Fetch a page and extract the webagents.md URL from its ``<meta>`` tag."""
    should_close = client is None
    client = client or httpx.AsyncClient(follow_redirects=True)
    try:
        resp = await client.get(page_url)
        resp.raise_for_status()
        html = resp.text

        match = _META_PATTERN.search(html) or _META_PATTERN_REVERSED.search(html)
        if not match:
            return None

        relative_url = match.group(1)
        return urljoin(page_url, relative_url)
    finally:
        if should_close:
            await client.aclose()


async def fetch_manifest(manifest_url: str, *, client: httpx.AsyncClient | None = None) -> Manifest:
    """Fetch and parse a webagents.md file from a URL."""
    should_close = client is None
    client = client or httpx.AsyncClient(follow_redirects=True)
    try:
        resp = await client.get(manifest_url)
        resp.raise_for_status()
        return parse(resp.text)
    finally:
        if should_close:
            await client.aclose()


async def discover(page_url: str, *, client: httpx.AsyncClient | None = None) -> Manifest | None:
    """Discover and parse a webagents.md manifest from a web page.

    Combines :func:`discover_manifest_url` and :func:`fetch_manifest`.
    """
    should_close = client is None
    client = client or httpx.AsyncClient(follow_redirects=True)
    try:
        url = await discover_manifest_url(page_url, client=client)
        if url is None:
            return None
        return await fetch_manifest(url, client=client)
    finally:
        if should_close:
            await client.aclose()
