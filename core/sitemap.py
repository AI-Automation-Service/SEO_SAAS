"""Sitemap fetching and URL extraction."""
from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

_TIMEOUT = 15


def _normalize_slug(url: str) -> str:
    return urlparse(url).path.strip("/").lower()


def _parse_locs(xml: str) -> list[str]:
    return re.findall(r"<loc>\s*(https?://[^\s<]+)\s*</loc>", xml, re.IGNORECASE)


def fetch_sitemap_urls(website: str) -> list[dict]:
    """
    Try sitemap_index.xml → sitemap.xml → robots.txt Sitemap: directive.
    Returns list of {url, slug} dicts, filtered to same domain, deduplicated.
    """
    base = website.rstrip("/")
    candidates = [
        f"{base}/sitemap_index.xml",
        f"{base}/sitemap.xml",
        f"{base}/sitemap",
    ]

    raw_xml: str | None = None
    for candidate in candidates:
        try:
            r = httpx.get(candidate, timeout=_TIMEOUT, follow_redirects=True)
            if r.status_code == 200 and "<loc>" in r.text:
                raw_xml = r.text
                break
        except Exception:
            continue

    if raw_xml is None:
        try:
            r = httpx.get(f"{base}/robots.txt", timeout=_TIMEOUT, follow_redirects=True)
            if r.status_code == 200:
                for line in r.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        sitemap_url = line.split(":", 1)[1].strip()
                        r2 = httpx.get(sitemap_url, timeout=_TIMEOUT, follow_redirects=True)
                        if r2.status_code == 200 and "<loc>" in r2.text:
                            raw_xml = r2.text
                            break
        except Exception:
            pass

    if not raw_xml:
        return []

    # Handle sitemap index → fetch sub-sitemaps
    all_locs: list[str] = []
    if "<sitemapindex" in raw_xml:
        sub_urls = _parse_locs(raw_xml)
        for sub_url in sub_urls[:10]:
            try:
                r = httpx.get(sub_url, timeout=_TIMEOUT, follow_redirects=True)
                if r.status_code == 200:
                    all_locs.extend(_parse_locs(r.text))
            except Exception:
                continue
    else:
        all_locs = _parse_locs(raw_xml)

    domain = urlparse(base).netloc
    seen: set[str] = set()
    results: list[dict] = []
    for url in all_locs:
        url = url.strip()
        if url in seen:
            continue
        if urlparse(url).netloc != domain:
            continue
        slug = _normalize_slug(url)
        if not slug:
            continue
        seen.add(url)
        results.append({"url": url, "slug": slug})

    return results
