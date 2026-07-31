from pydantic import BaseModel, HttpUrl
from typing import Optional


class ProjectIntegrations(BaseModel):
    wordpress_secret: Optional[str] = None
    shopify_secret: Optional[str] = None
    google_search_console_secret: Optional[str] = None
    google_analytics_secret: Optional[str] = None
    cloudflare_secret: Optional[str] = None
    github_secret: Optional[str] = None


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
    integrations: ProjectIntegrations = ProjectIntegrations()
    active: bool = True
