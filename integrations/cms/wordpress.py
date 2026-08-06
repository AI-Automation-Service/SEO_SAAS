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
    def __init__(
        self,
        url: str,
        username: str = "",
        password: str = "",
        *,
        site_token: str = "",
    ):
        """
        Accepts either username + app-password (Basic auth) or a site_token
        from the SEO OS WordPress Plugin (Bearer auth, Phase 3 §21).
        At least one credential method must be provided.
        """
        if not url:
            raise IntegrationConfigError("WordPress URL is required.")
        if not site_token and (not username or not password):
            raise IntegrationConfigError(
                "Either a site_token or username + application password is required."
            )

        self._api_url = url.rstrip("/") + "/wp-json/wp/v2"
        if site_token:
            self._auth = None
            self._bearer = site_token
        else:
            self._auth = (username, password)
            self._bearer = ""

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self._api_url}{path}"
        headers = kwargs.pop("headers", {})
        if self._bearer:
            headers["Authorization"] = f"Bearer {self._bearer}"
        try:
            response = httpx.request(
                method,
                url,
                auth=self._auth,
                headers=headers,
                timeout=30,
                **kwargs,
            )
        except httpx.ConnectError as e:
            raise IntegrationConnectionError(f"Cannot reach WordPress at {self._api_url}: {e}") from e
        except httpx.TimeoutException as e:
            raise IntegrationConnectionError(f"WordPress request timed out: {e}") from e

        if response.status_code in (401, 403):
            hint = "Check your site token." if self._bearer else "Check your username and application password."
            raise IntegrationAuthError(
                f"WordPress authentication failed (HTTP {response.status_code}). {hint}"
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
            headers = {"Authorization": f"Bearer {self._bearer}"} if self._bearer else {}
            response = httpx.get(root_url, auth=self._auth, headers=headers, timeout=10)
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

    def get_content(self, post_id: int, post_type: str) -> dict:
        if post_type == "page":
            return self.get_page(post_id)
        return self.get_post(post_id)

    def verify_content(self, post_id: int, post_type: str, hint: str) -> bool:
        """
        Read back saved content via WP REST API and check hint is present.
        Returns False only when content is genuinely absent (theme-controlled page).
        Raises on network/API errors so callers can apply their own fail-open policy.
        """
        data = self.get_content(post_id, post_type)
        return hint in (data.get("content") or "")

    def find_post_by_url(self, url: str) -> dict | None:
        slug = urlparse(url).path.rstrip("/").split("/")[-1]

        # Fetch reading settings once — used for both homepage and posts-page detection
        page_on_front: int | None = None
        page_for_posts: int | None = None
        try:
            settings = self._request("GET", "/settings").json()
            page_on_front = settings.get("page_on_front") or None
            page_for_posts = settings.get("page_for_posts") or None
        except Exception:
            pass

        if not slug:
            # Homepage — fetch whichever page WordPress set as the front page
            if page_on_front:
                return self.get_page(int(page_on_front))
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
                    # True when this page is configured as the WordPress blog listing
                    # page (Settings → Reading → "Posts page"). Its post_content is
                    # always empty — WordPress generates the listing via The Loop.
                    "is_posts_page": bool(page_for_posts and data["id"] == int(page_for_posts)),
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
        focus_keyword: str | None = None,
    ) -> None:
        """Update Yoast or RankMath SEO meta fields via WordPress REST API."""
        meta: dict = {}
        if plugin == "yoast":
            if title:
                meta["_yoast_wpseo_title"] = title
            if description:
                meta["_yoast_wpseo_metadesc"] = description
            if focus_keyword:
                meta["_yoast_wpseo_focuskw"] = focus_keyword
        elif plugin == "rankmath":
            if title:
                meta["rank_math_title"] = title
            if description:
                meta["rank_math_description"] = description
            if focus_keyword:
                meta["rank_math_focus_keyword"] = focus_keyword
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

    def upload_media(self, image_bytes: bytes, filename: str, mime_type: str = "image/png") -> dict:
        """
        Upload an image to the WordPress Media Library.
        Returns dict with 'id' and 'url' keys.
        """
        response = self._request(
            "POST", "/media",
            content=image_bytes,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": mime_type,
            },
        )
        data = response.json()
        return {
            "id": data.get("id"),
            "url": data.get("source_url") or data.get("guid", {}).get("rendered", ""),
        }

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
