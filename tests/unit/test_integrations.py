"""Unit tests for integration adapters — all external calls are mocked."""
from unittest.mock import MagicMock, patch

import pytest

from integrations.base import (
    IntegrationAuthError,
    IntegrationConfigError,
    IntegrationConnectionError,
    IntegrationRateLimitError,
)
from integrations.cms.shopify import ShopifyAdapter
from integrations.cms.wordpress import WordPressAdapter


def _mock_response(status_code: int, json_data=None, text: str = "", headers: dict = None):
    mock = MagicMock()
    mock.status_code = status_code
    mock.is_success = 200 <= status_code < 300
    mock.json.return_value = json_data or {}
    mock.text = text
    mock.headers = headers or {}
    return mock


# ---------------------------------------------------------------------------
# WordPressAdapter — construction
# ---------------------------------------------------------------------------

def test_wordpress_missing_url_raises():
    with pytest.raises(IntegrationConfigError, match="URL"):
        WordPressAdapter(url="", username="admin", password="pass")


def test_wordpress_missing_credentials_raises():
    with pytest.raises(IntegrationConfigError, match="username"):
        WordPressAdapter(url="https://example.com", username="", password="")


# ---------------------------------------------------------------------------
# WordPressAdapter — test_connection
# ---------------------------------------------------------------------------

def test_wordpress_connection_success():
    with patch("httpx.request", return_value=_mock_response(200)):
        adapter = WordPressAdapter(url="https://example.com", username="admin", password="pass")
        assert adapter.test_connection() is True


def test_wordpress_connection_401_raises_auth_error():
    with patch("httpx.request", return_value=_mock_response(401)):
        adapter = WordPressAdapter(url="https://example.com", username="admin", password="wrong")
        with pytest.raises(IntegrationAuthError):
            adapter.test_connection()


def test_wordpress_connection_403_raises_auth_error():
    with patch("httpx.request", return_value=_mock_response(403)):
        adapter = WordPressAdapter(url="https://example.com", username="admin", password="pass")
        with pytest.raises(IntegrationAuthError):
            adapter.test_connection()


def test_wordpress_connection_429_raises_rate_limit():
    with patch("httpx.request", return_value=_mock_response(429, headers={"Retry-After": "30"})):
        adapter = WordPressAdapter(url="https://example.com", username="admin", password="pass")
        with pytest.raises(IntegrationRateLimitError) as exc_info:
            adapter.test_connection()
        assert exc_info.value.retry_after == 30


def test_wordpress_connect_error_raises_connection_error():
    import httpx as _httpx

    with patch("httpx.request", side_effect=_httpx.ConnectError("refused")):
        adapter = WordPressAdapter(url="https://example.com", username="admin", password="pass")
        with pytest.raises(IntegrationConnectionError):
            adapter.test_connection()


# ---------------------------------------------------------------------------
# WordPressAdapter — create_post
# ---------------------------------------------------------------------------

def test_wordpress_create_post_returns_published_post():
    from integrations.cms.base import PostDraft

    response_data = {
        "id": 42,
        "link": "https://example.com/my-post/",
        "title": {"rendered": "My Post"},
        "status": "draft",
    }
    with patch("httpx.request", return_value=_mock_response(201, json_data=response_data)):
        adapter = WordPressAdapter(url="https://example.com", username="admin", password="pass")
        result = adapter.create_post(PostDraft(title="My Post", content="<p>Content</p>"))

        assert result.id == 42
        assert result.url == "https://example.com/my-post/"
        assert result.status == "draft"


# ---------------------------------------------------------------------------
# WordPressAdapter — get_posts / get_sitemap_urls
# ---------------------------------------------------------------------------

def test_wordpress_get_posts_returns_list():
    posts = [{"id": 1, "link": "https://example.com/post-1/", "status": "publish"}]
    with patch("httpx.request", return_value=_mock_response(200, json_data=posts)):
        adapter = WordPressAdapter(url="https://example.com", username="admin", password="pass")
        result = adapter.get_posts()
        assert len(result) == 1
        assert result[0]["id"] == 1


def test_wordpress_get_sitemap_urls_paginates_until_empty():
    posts_p1 = [{"link": f"https://example.com/post-{i}/"} for i in range(100)]
    posts_p2 = [{"link": "https://example.com/post-100/"}]
    pages = [{"link": "https://example.com/about/"}]

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # posts page 1, posts page 2, pages page 1
        return _mock_response(200, json_data=[posts_p1, posts_p2, pages][call_count - 1])

    with patch("httpx.request", side_effect=side_effect):
        adapter = WordPressAdapter(url="https://example.com", username="admin", password="pass")
        urls = adapter.get_sitemap_urls()

    assert len(urls) == 102  # 100 + 1 + 1
    assert "https://example.com/about/" in urls


# ---------------------------------------------------------------------------
# ShopifyAdapter — stub
# ---------------------------------------------------------------------------

def test_shopify_raises_not_implemented():
    adapter = ShopifyAdapter()
    with pytest.raises(NotImplementedError):
        adapter.test_connection()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_registry_returns_wordpress_adapter():
    from integrations.registry import get_cms_adapter

    context = MagicMock()
    context.name = "test-client"
    context.config.cms = "wordpress"
    context.config.integrations.wordpress.enabled = True
    context.config.integrations.wordpress.url = "https://example.com"
    context.config.integrations.wordpress.username_env = "WP_USER"
    context.config.integrations.wordpress.password_env = "WP_PASS"

    mock_secrets = MagicMock()
    mock_secrets.get.side_effect = ["admin", "secret"]

    adapter = get_cms_adapter(context, mock_secrets)
    assert isinstance(adapter, WordPressAdapter)


def test_registry_wordpress_not_enabled_raises():
    from integrations.registry import get_cms_adapter

    context = MagicMock()
    context.name = "test-client"
    context.config.cms = "wordpress"
    context.config.integrations.wordpress.enabled = False

    with pytest.raises(IntegrationConfigError, match="not enabled"):
        get_cms_adapter(context, MagicMock())


def test_registry_shopify_not_enabled_raises():
    from integrations.registry import get_cms_adapter

    context = MagicMock()
    context.name = "test-client"
    context.config.cms = "shopify"
    context.config.integrations.shopify.enabled = False

    with pytest.raises(IntegrationConfigError, match="not enabled"):
        get_cms_adapter(context, MagicMock())


def test_registry_unknown_cms_raises():
    from integrations.registry import get_cms_adapter

    context = MagicMock()
    context.name = "test-client"
    context.config.cms = "wix"

    with pytest.raises(IntegrationConfigError, match="No CMS adapter"):
        get_cms_adapter(context, MagicMock())
