"""Sitemap fetching and URL extraction."""
from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

_TIMEOUT = 15

# Sub-sitemap name patterns → page_type
_PAGE_PATTERNS = re.compile(r"page[s]?[-_]sitemap|sitemap[-_]page[s]?", re.IGNORECASE)
_POST_PATTERNS = re.compile(r"post[s]?[-_]sitemap|sitemap[-_]post[s]?", re.IGNORECASE)
# Skip non-content sub-sitemaps
_SKIP_PATTERNS = re.compile(
    r"category|categories|tag[s]?|author[s]?|product[s]?|attachment|taxonomy",
    re.IGNORECASE,
)


def _normalize_slug(url: str) -> str:
    return urlparse(url).path.strip("/").lower()


def _parse_locs(xml: str) -> list[str]:
    return re.findall(r"<loc>\s*(https?://[^\s<]+)\s*</loc>", xml, re.IGNORECASE)


def _page_type_from_sitemap_url(sitemap_url: str) -> str:
    """Infer page_type from sub-sitemap URL name."""
    if _PAGE_PATTERNS.search(sitemap_url):
        return "page"
    if _POST_PATTERNS.search(sitemap_url):
        return "post"
    return "unknown"


def _refine_page_type(url: str, current_type: str) -> str:
    """
    Single-segment root URLs (e.g. /terms-and-condition/) are always pages,
    even when WordPress puts them in a post-sitemap. Real posts have a parent
    path segment (e.g. /blog/post-title/ or /2024/01/title/).
    """
    if current_type == "page":
        return "page"
    path = urlparse(url).path.strip("/")
    if "/" not in path:
        return "page"
    return current_type


def fetch_sitemap_urls(website: str) -> list[dict]:
    """
    Try sitemap_index.xml → sitemap.xml → robots.txt Sitemap: directive.
    Returns list of {url, slug, page_type} dicts for pages/posts only.
    """
    base = website.rstrip("/")
    candidates = [
        f"{base}/sitemap_index.xml",
        f"{base}/sitemap.xml",
        f"{base}/sitemap",
    ]

    raw_xml: str | None = None
    source_url: str = ""
    for candidate in candidates:
        try:
            r = httpx.get(candidate, timeout=_TIMEOUT, follow_redirects=True)
            if r.status_code == 200 and "<loc>" in r.text:
                raw_xml = r.text
                source_url = candidate
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
                            source_url = sitemap_url
                            break
        except Exception:
            pass

    if not raw_xml:
        return []

    domain = urlparse(base).netloc
    seen: set[str] = set()
    results: list[dict] = []

    def _add_locs(locs: list[str], page_type: str) -> None:
        for url in locs:
            url = url.strip()
            if url in seen:
                continue
            if urlparse(url).netloc != domain:
                continue
            slug = _normalize_slug(url)
            if not slug:
                continue
            seen.add(url)
            results.append({"url": url, "slug": slug, "page_type": _refine_page_type(url, page_type)})

    if "<sitemapindex" in raw_xml:
        sub_urls = _parse_locs(raw_xml)
        for sub_url in sub_urls[:15]:
            # Skip non-content sitemaps (categories, tags, authors, products)
            if _SKIP_PATTERNS.search(sub_url):
                continue
            pt = _page_type_from_sitemap_url(sub_url)
            try:
                r = httpx.get(sub_url, timeout=_TIMEOUT, follow_redirects=True)
                if r.status_code == 200:
                    _add_locs(_parse_locs(r.text), pt)
            except Exception:
                continue
    else:
        # Single sitemap — can't determine type from URL, use "unknown"
        pt = _page_type_from_sitemap_url(source_url)
        _add_locs(_parse_locs(raw_xml), pt)

    return results
