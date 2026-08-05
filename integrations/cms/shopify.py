"""
Shopify Admin REST API adapter.

Uses a private app / custom app access token stored in the project secrets.
Shopify Plus / Partner App OAuth support is Phase 3 — for now this handles
token-based access which covers custom app installs.

Required scope: read_content, write_content, read_products, write_products,
                read_metafields, write_metafields
"""

from urllib.parse import urlparse

import httpx

from shared.exceptions import IntegrationError


_API_VERSION = "2024-01"

# Storefront URL prefix per resource type (blog_post is built from its blog id).
_STOREFRONT_PATH = {
    "product": "products",
    "collection": "collections",
    "page": "pages",
}

# Admin API owner resource per resource type, used for metafield endpoints.
_OWNER_RESOURCE = {
    "product": "products",
    "collection": "custom_collections",
    "page": "pages",
    "blog_post": "blogs",
}


def _normalize(item: dict, resource_type: str, blog_id: int | None = None) -> dict:
    """Map a raw Shopify resource onto the shape the improve pipeline expects."""
    handle = item.get("handle", "")
    normalized = {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "handle": handle,
        "body_html": item.get("body_html", ""),
        "type": resource_type,
    }
    if resource_type == "blog_post":
        normalized["blog_id"] = blog_id
        normalized["link"] = f"/blogs/{blog_id}/{handle}"
    else:
        normalized["link"] = f"/{_STOREFRONT_PATH[resource_type]}/{handle}"
    return normalized


class ShopifyAdapter:
    def __init__(self, store_url: str, access_token: str):
        # Normalize store URL to just the myshopify.com domain
        host = store_url.rstrip("/")
        if not host.startswith("http"):
            host = f"https://{host}"
        self.base_url = f"{host}/admin/api/{_API_VERSION}"
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }
        self._client = httpx.Client(headers=self.headers, timeout=20)

    def test_connection(self) -> bool:
        try:
            resp = self._client.get(self._url("shop.json"))
            return resp.status_code == 200
        except Exception as e:
            raise IntegrationError(f"Shopify connection failed: {e}") from e

    # ── Request helpers ────────────────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path}"

    @staticmethod
    def _check(resp: httpx.Response, action: str) -> httpx.Response:
        if resp.status_code not in (200, 201):
            raise IntegrationError(
                f"Shopify {action} failed: {resp.status_code} — {resp.text[:200]}"
            )
        return resp

    # ── Products ───────────────────────────────────────────────────────────────

    def get_product(self, product_id: int) -> dict:
        resp = self._client.get(self._url(f"products/{product_id}.json"))
        self._check(resp, "get_product")
        return _normalize(resp.json().get("product") or {}, "product")

    def update_product_body(self, product_id: int, body_html: str) -> None:
        self._check(
            self._client.put(
                self._url(f"products/{product_id}.json"),
                json={"product": {"id": product_id, "body_html": body_html}},
            ),
            "update_product",
        )

    def get_products(self, limit: int = 50) -> list[dict]:
        resp = self._client.get(
            self._url("products.json"),
            params={"limit": min(limit, 250), "fields": "id,title,handle,body_html"},
        )
        self._check(resp, "get_products")
        return [_normalize(p, "product") for p in resp.json().get("products", [])]

    # ── Collections ────────────────────────────────────────────────────────────

    def get_collection(self, collection_id: int) -> dict:
        resp = self._client.get(self._url(f"custom_collections/{collection_id}.json"))
        key = "custom_collection"
        if resp.status_code != 200:
            resp = self._client.get(self._url(f"smart_collections/{collection_id}.json"))
            key = "smart_collection"
        self._check(resp, "get_collection")
        return _normalize(resp.json().get(key) or {}, "collection")

    def update_collection_body(self, collection_id: int, body_html: str) -> None:
        # Try custom collection first, then smart collection
        resp = self._client.put(
            self._url(f"custom_collections/{collection_id}.json"),
            json={"custom_collection": {"id": collection_id, "body_html": body_html}},
        )
        if resp.status_code not in (200, 201):
            resp = self._client.put(
                self._url(f"smart_collections/{collection_id}.json"),
                json={"smart_collection": {"id": collection_id, "body_html": body_html}},
            )
        self._check(resp, "update_collection")

    # ── Pages ──────────────────────────────────────────────────────────────────

    def get_page(self, page_id: int) -> dict:
        resp = self._client.get(self._url(f"pages/{page_id}.json"))
        self._check(resp, "get_page")
        return _normalize(resp.json().get("page") or {}, "page")

    def update_page_body(self, page_id: int, body_html: str) -> None:
        self._check(
            self._client.put(
                self._url(f"pages/{page_id}.json"),
                json={"page": {"id": page_id, "body_html": body_html}},
            ),
            "update_page",
        )

    # ── SEO Meta (global namespace metafields) ─────────────────────────────────

    def update_seo_meta(
        self,
        resource_type: str,  # product / collection / page / blog_post
        resource_id: int,
        meta_title: str | None,
        meta_description: str | None,
    ) -> None:
        """
        Update SEO title and description via Shopify metafields (global namespace).
        resource_type: product | collection | page | blog_post
        """
        owner_resource = _OWNER_RESOURCE.get(resource_type)
        if not owner_resource:
            raise IntegrationError(f"Unknown resource type for SEO meta: {resource_type}")

        for key, value in (("title_tag", meta_title), ("description_tag", meta_description)):
            if not value:
                continue
            resp = self._client.post(
                self._url(f"{owner_resource}/{resource_id}/metafields.json"),
                json={"metafield": {
                    "namespace": "global",
                    "key": key,
                    "value": value,
                    "type": "single_line_text_field",
                }},
            )
            if resp.status_code in (200, 201):
                continue

            # Most likely the metafield already exists — update it in place.
            existing_id = self._find_metafield_id(owner_resource, resource_id, key)
            if not existing_id:
                raise IntegrationError(
                    f"Shopify update_seo_meta({key}) failed: {resp.status_code} — {resp.text[:200]}"
                )
            self._check(
                self._client.put(
                    self._url(f"metafields/{existing_id}.json"),
                    json={"metafield": {"id": existing_id, "value": value}},
                ),
                f"update_seo_meta({key})",
            )

    def _find_metafield_id(self, owner_resource: str, resource_id: int, key: str) -> int | None:
        resp = self._client.get(
            self._url(f"{owner_resource}/{resource_id}/metafields.json"),
            params={"namespace": "global", "key": key},
        )
        if resp.status_code != 200:
            return None
        metafields = resp.json().get("metafields", [])
        return metafields[0]["id"] if metafields else None

    def get_seo_meta(self, resource_type: str, resource_id: int) -> dict:
        owner_resource = _OWNER_RESOURCE.get(resource_type)
        if not owner_resource:
            return {}
        resp = self._client.get(
            self._url(f"{owner_resource}/{resource_id}/metafields.json"),
            params={"namespace": "global"},
        )
        if resp.status_code != 200:
            return {}
        metafields = {m["key"]: m["value"] for m in resp.json().get("metafields", [])}
        return {
            "meta_title": metafields.get("title_tag", ""),
            "meta_description": metafields.get("description_tag", ""),
        }

    # ── Blog articles ──────────────────────────────────────────────────────────

    def get_blogs(self) -> list[dict]:
        resp = self._client.get(self._url("blogs.json"))
        if resp.status_code != 200:
            return []
        return resp.json().get("blogs", [])

    def get_article(self, blog_id: int, article_id: int) -> dict:
        resp = self._client.get(self._url(f"blogs/{blog_id}/articles/{article_id}.json"))
        self._check(resp, "get_article")
        return _normalize(resp.json().get("article") or {}, "blog_post", blog_id)

    def create_article(self, blog_id: int, title: str, body_html: str, status: str = "draft") -> dict:
        resp = self._client.post(
            self._url(f"blogs/{blog_id}/articles.json"),
            json={"article": {
                "title": title,
                "body_html": body_html,
                "published": status == "published",
            }},
        )
        self._check(resp, "create_article")
        art = resp.json().get("article") or {}
        return {
            "id": art.get("id"),
            "blog_id": blog_id,
            "title": art.get("title", ""),
            "handle": art.get("handle", ""),
        }

    def update_article_body(self, blog_id: int, article_id: int, body_html: str) -> None:
        self._check(
            self._client.put(
                self._url(f"blogs/{blog_id}/articles/{article_id}.json"),
                json={"article": {"id": article_id, "body_html": body_html}},
            ),
            "update_article",
        )

    # ── URL → resource lookup ──────────────────────────────────────────────────

    def find_resource_by_url(self, url: str) -> dict | None:
        """
        Parse a Shopify storefront URL and return the resource dict with type info.
        Handles: /products/handle, /collections/handle, /pages/handle,
                 /blogs/{blog-handle}/{article-handle}
        """
        parts = [p for p in urlparse(url).path.split("/") if p]
        if len(parts) < 2:
            return None
        kind, handle = parts[0], parts[1]

        if kind == "products":
            return self._find_by_handle("products", handle, "product")

        if kind == "collections":
            return (
                self._find_by_handle("custom_collections", handle, "collection")
                or self._find_by_handle("smart_collections", handle, "collection")
            )

        if kind == "pages":
            return self._find_by_handle("pages", handle, "page")

        if kind == "blogs" and len(parts) >= 3:
            blog = self._find_blog_by_handle(handle)
            if not blog:
                return None
            return self._find_article_by_handle(blog["id"], parts[2])

        return None

    def _find_by_handle(self, resource_path: str, handle: str, resource_type: str) -> dict | None:
        # Shopify list endpoints key the response by the resource path,
        # e.g. products.json → {"products": [...]}
        resp = self._client.get(
            self._url(f"{resource_path}.json"),
            params={"handle": handle, "fields": "id,title,handle,body_html"},
        )
        if resp.status_code != 200:
            return None
        items = resp.json().get(resource_path) or []
        return _normalize(items[0], resource_type) if items else None

    def _find_blog_by_handle(self, handle: str) -> dict | None:
        return next((b for b in self.get_blogs() if b.get("handle") == handle), None)

    def _find_article_by_handle(self, blog_id: int, article_handle: str) -> dict | None:
        resp = self._client.get(
            self._url(f"blogs/{blog_id}/articles.json"),
            params={"handle": article_handle, "fields": "id,title,handle,body_html"},
        )
        if resp.status_code != 200:
            return None
        articles = resp.json().get("articles", [])
        return _normalize(articles[0], "blog_post", blog_id) if articles else None

    def update_resource_body(self, resource: dict, new_body_html: str) -> None:
        """Dispatch body update to the right Shopify API endpoint by resource type."""
        rtype = resource.get("type")
        rid = resource["id"]
        if rtype == "product":
            self.update_product_body(rid, new_body_html)
        elif rtype == "collection":
            self.update_collection_body(rid, new_body_html)
        elif rtype == "page":
            self.update_page_body(rid, new_body_html)
        elif rtype == "blog_post":
            self.update_article_body(resource["blog_id"], rid, new_body_html)
        else:
            raise IntegrationError(f"Unknown Shopify resource type: {rtype}")
