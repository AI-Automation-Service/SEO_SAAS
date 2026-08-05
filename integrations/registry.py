from core.models.context import ProjectContext
from core.secrets import SecretManager
from integrations.base import IntegrationConfigError
from integrations.cms.base import CMSAdapter
from integrations.cms.shopify import ShopifyAdapter
from integrations.cms.wordpress import WordPressAdapter


def get_cms_adapter(context: ProjectContext, secrets: SecretManager) -> CMSAdapter:
    cms = context.config.cms.lower()

    if cms == "wordpress":
        cfg = context.config.integrations.wordpress
        if not cfg.enabled:
            raise IntegrationConfigError(
                f"WordPress integration is not enabled for project '{context.name}'. "
                "Set integrations.wordpress.enabled: true in project.yaml."
            )
        return WordPressAdapter(
            url=cfg.url,
            username=secrets.get(cfg.username_env),
            password=secrets.get(cfg.password_env),
        )

    if cms == "shopify":
        cfg = context.config.integrations.shopify
        if not cfg.enabled:
            raise IntegrationConfigError(
                f"Shopify integration is not enabled for project '{context.name}'. "
                "Set integrations.shopify.enabled: true in project.yaml."
            )
        return ShopifyAdapter(
            store_url=cfg.store_url,
            access_token=secrets.get(cfg.token_env),
        )

    raise IntegrationConfigError(
        f"No CMS adapter available for '{cms}'. Supported: wordpress, shopify."
    )
