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
