from urllib.parse import urlparse

import httpx

from integrations.base import (
    IntegrationAuthError,
    IntegrationConfigError,
    IntegrationConnectionError,
    IntegrationError,
    IntegrationRateLimitError,
)
from integrations.cms.base import CMSAdapter, PostDraft, PublishedPost


class WordPressAdapter(CMSAdapter):
    def __init__(self, url: str, username: str, password: str):
        if not url:
            raise IntegrationConfigError("WordPress URL is required.")
        if not username or not password:
            raise IntegrationConfigError("WordPress username and application password are required.")

        self._api_url = url.rstrip("/") + "/wp-json/wp/v2"
        self._auth = (username, password)

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self._api_url}{path}"
        try:
            response = httpx.request(method, url, auth=self._auth, timeout=30, **kwargs)
        except httpx.ConnectError as e:
            raise IntegrationConnectionError(f"Cannot reach WordPress at {self._api_url}: {e}") from e
        except httpx.TimeoutException as e:
            raise IntegrationConnectionError(f"WordPress request timed out: {e}") from e

        if response.status_code in (401, 403):
            raise IntegrationAuthError(
                f"WordPress authentication failed (HTTP {response.status_code}). "
                "Check your username and application password."
            )
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise IntegrationRateLimitError(
                f"WordPress rate limit reached. Retry after {retry_after}s.",
                retry_after=retry_after,
            )
        if not response.is_success:
            raise IntegrationError(
                f"WordPress API error {response.status_code}: {response.text[:300]}"
            )
        return response

    def _extract_seo_meta(self, data: dict) -> tuple[str, str]:
        """Extract current SEO title and description from Yoast or RankMath response data."""
        yoast_json = data.get("yoast_head_json") or {}
        meta = data.get("meta") or {}
        title = (
            yoast_json.get("title")
            or meta.get("_yoast_wpseo_title")
            or meta.get("rank_math_title")
            or ""
        )
        description = (
            yoast_json.get("description")
            or meta.get("_yoast_wpseo_metadesc")
            or meta.get("rank_math_description")
            or ""
        )
        return str(title), str(description)

    def detect_seo_plugin(self) -> str:
        """
        Detect the active SEO plugin via the REST API namespace registry.
        Returns 'yoast', 'rankmath', or 'none'.
        Namespace-based detection is reliable even when no meta values have been saved yet.
        """
        try:
            root_url = self._api_url.rsplit("/wp/v2", 1)[0]
            response = httpx.get(root_url, auth=self._auth, timeout=10)
            namespaces = response.json().get("namespaces", [])
            if any("yoast" in ns.lower() for ns in namespaces):
                return "yoast"
            if any("rankmath" in ns.lower() for ns in namespaces):
                return "rankmath"
        except Exception:
            pass
        return "none"

    def test_connection(self) -> bool:
        self._request("GET", "/users/me")
        return True

    def create_post(self, draft: PostDraft) -> PublishedPost:
        payload: dict = {
            "title": draft.title,
            "content": draft.content,
            "status": draft.status,
        }
        if draft.slug:
            payload["slug"] = draft.slug

        response = self._request("POST", "/posts", json=payload)
        data = response.json()
        return PublishedPost(
            id=data["id"],
            url=data["link"],
            title=data["title"]["rendered"],
            status=data["status"],
        )

    def get_posts(self, page: int = 1, per_page: int = 100) -> list[dict]:
        response = self._request(
            "GET",
            "/posts",
            params={
                "page": page,
                "per_page": per_page,
                "_fields": "id,link,slug,title,status,date",
            },
        )
        return response.json()

    def create_page(self, draft: PostDraft) -> PublishedPost:
        payload: dict = {
            "title": draft.title,
            "content": draft.content,
            "status": draft.status,
        }
        if draft.slug:
            payload["slug"] = draft.slug
        response = self._request("POST", "/pages", json=payload)
        data = response.json()
        return PublishedPost(
            id=data["id"],
            url=data["link"],
            title=data["title"]["rendered"],
            status=data["status"],
        )

    def get_post(self, post_id: int) -> dict:
        response = self._request("GET", f"/posts/{post_id}", params={"context": "edit"})
        data = response.json()
        meta = data.get("meta") or {}
        current_meta_title, current_meta_description = self._extract_seo_meta(data)
        return {
            "id": data["id"],
            "title": data["title"]["raw"],
            "content": data["content"]["raw"],
            "link": data["link"],
            "slug": data["slug"],
            "type": "post",
            "has_yoast": "yoast_head" in data,
            "has_rankmath": "rank_math_title" in meta,
            "current_meta_title": current_meta_title,
            "current_meta_description": current_meta_description,
        }

    def get_page(self, page_id: int) -> dict:
        response = self._request("GET", f"/pages/{page_id}", params={"context": "edit"})
        data = response.json()
        meta = data.get("meta") or {}
        current_meta_title, current_meta_description = self._extract_seo_meta(data)
        return {
            "id": data["id"],
            "title": data["title"]["raw"],
            "content": data["content"]["raw"],
            "link": data["link"],
            "slug": data["slug"],
            "type": "page",
            "has_yoast": "yoast_head" in data,
            "has_rankmath": "rank_math_title" in meta,
            "current_meta_title": current_meta_title,
            "current_meta_description": current_meta_description,
        }

    def find_post_by_url(self, url: str) -> dict | None:
        slug = urlparse(url).path.rstrip("/").split("/")[-1]
        if not slug:
            # Homepage — fetch whichever page WordPress set as the front page
            try:
                settings = self._request("GET", "/settings").json()
                page_id = settings.get("page_on_front")
                if page_id:
                    return self.get_page(int(page_id))
            except Exception:
                pass
            return None
        for content_type in ("posts", "pages"):
            resp = self._request(
                "GET", f"/{content_type}",
                params={
                    "slug": slug,
                    "context": "edit",
                    "_fields": "id,title,content,link,slug,meta,yoast_head,yoast_head_json",
                },
            )
            results = resp.json()
            if results:
                data = results[0]
                meta = data.get("meta") or {}
                current_meta_title, current_meta_description = self._extract_seo_meta(data)
                return {
                    "id": data["id"],
                    "title": data["title"]["raw"],
                    "content": data["content"]["raw"],
                    "link": data["link"],
                    "slug": data["slug"],
                    "type": content_type.rstrip("s"),
                    "has_yoast": "yoast_head" in data,
                    "has_rankmath": "rank_math_title" in meta,
                    "current_meta_title": current_meta_title,
                    "current_meta_description": current_meta_description,
                }
        return None

    def update_post(self, post_id: int, new_content: str) -> None:
        self._request("PUT", f"/posts/{post_id}", json={"content": new_content})

    def update_page(self, page_id: int, new_content: str) -> None:
        self._request("PUT", f"/pages/{page_id}", json={"content": new_content})

    def update_seo_meta(
        self,
        post_id: int,
        post_type: str,
        plugin: str,
        title: str | None,
        description: str | None,
    ) -> None:
        """Update Yoast or RankMath SEO meta fields via WordPress REST API."""
        meta: dict = {}
        if plugin == "yoast":
            if title:
                meta["_yoast_wpseo_title"] = title
            if description:
                meta["_yoast_wpseo_metadesc"] = description
        elif plugin == "rankmath":
            if title:
                meta["rank_math_title"] = title
            if description:
                meta["rank_math_description"] = description
        if not meta:
            return
        endpoint = f"/pages/{post_id}" if post_type == "page" else f"/posts/{post_id}"
        self._request("PATCH", endpoint, json={"meta": meta})

    def find_url_by_slug(self, slug: str) -> str | None:
        """
        Return the published live URL for a slug across posts and pages.
        Returns None if not found. Does not raise on empty result.
        Used by the broken-link scanner to find replacements for internal 404s.
        """
        if not slug:
            return None
        for content_type in ("posts", "pages"):
            try:
                resp = self._request(
                    "GET", f"/{content_type}",
                    params={"slug": slug, "_fields": "link", "status": "publish"},
                )
                results = resp.json()
                if results:
                    return results[0]["link"]
            except IntegrationError:
                pass
        return None

    def get_sitemap_urls(self) -> list[str]:
        urls: list[str] = []
        for content_type in ("posts", "pages"):
            page = 1
            while True:
                batch = self._request(
                    "GET",
                    f"/{content_type}",
                    params={"page": page, "per_page": 100, "_fields": "link", "status": "publish"},
                ).json()
                if not batch:
                    break
                urls.extend(item["link"] for item in batch)
                if len(batch) < 100:
                    break
                page += 1
        return urls
