from integrations.cms.base import CMSAdapter, PostDraft, PublishedPost


class ShopifyAdapter(CMSAdapter):
    """Shopify CMS adapter — not yet implemented."""

    def test_connection(self) -> bool:
        raise NotImplementedError(
            "Shopify integration is not yet implemented. "
            "Set cms: wordpress in project.yaml to use WordPress."
        )

    def create_post(self, draft: PostDraft) -> PublishedPost:
        raise NotImplementedError("Shopify integration is not yet implemented.")

    def get_posts(self, page: int = 1, per_page: int = 100) -> list[dict]:
        raise NotImplementedError("Shopify integration is not yet implemented.")

    def get_sitemap_urls(self) -> list[str]:
        raise NotImplementedError("Shopify integration is not yet implemented.")
