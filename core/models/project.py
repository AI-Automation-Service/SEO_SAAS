from pydantic import BaseModel, HttpUrl
from typing import Optional


class WordPressConfig(BaseModel):
    enabled: bool = False
    url: str = ""
    username_env: Optional[str] = None   # env var name for WP username
    password_env: Optional[str] = None   # env var name for WP application password


class GoogleConfig(BaseModel):
    enabled: bool = False
    credentials_env: Optional[str] = None  # env var name: path to service account JSON file
    gsc_site_url: Optional[str] = None     # property URL as verified in GSC
    ga4_property_id: Optional[str] = None


class ShopifyConfig(BaseModel):
    enabled: bool = False
    store_url: str = ""
    token_env: Optional[str] = None   # env var name for Shopify Admin API token


class ProjectIntegrations(BaseModel):
    wordpress: WordPressConfig = WordPressConfig()
    google: GoogleConfig = GoogleConfig()
    shopify: ShopifyConfig = ShopifyConfig()


class ProjectConfig(BaseModel):
    name: str
    website: HttpUrl
    business_name: str
    business_type: str
    country: str
    language: str
    cms: str  # wordpress | shopify | nextjs | static
    publishing_method: str  # api | git | manual
    tone_of_voice: str
    seo_goals: list[str]
    business_goals: list[str]
    competitors: list[str]
    target_audience: str
    seo_plugin: Optional[str] = None   # rankmath | yoast | aioseo | none
    image_source: str = "client"        # client | dalle
    primary_conversion: str = ""        # lead_generation | ecommerce | phone_call | email_signup | brand_awareness
    business_location: str = ""         # city/region e.g. "Cairo, Egypt"
    integrations: ProjectIntegrations = ProjectIntegrations()
    active: bool = True
