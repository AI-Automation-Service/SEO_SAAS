from pathlib import Path

import yaml
from loguru import logger

from shared.exceptions import SEOOSError

KNOWLEDGE_FILES = [
    "brand.md",
    "business.md",
    "products.md",
    "services.md",
    "audience.md",
    "competitors.md",
    "tone.md",
    "writing-guidelines.md",
    "seo-rules.md",
    "faq.md",
    "glossary.md",
    "topic-map.md",
    "locations.md",
]

DATA_FILES = {
    "keywords.json": "[]",
    "clusters.json": "[]",
    "articles.json": "[]",
    "sitemap.json": "{}",
    "internal-links.json": "[]",
    "rankings.json": "[]",
    "backlinks.json": "[]",
    "analytics.json": "{}",
    "search-console.json": "{}",
}

PROJECT_DIRS = [
    "config",
    "knowledge",
    "content",
    "reports",
    "audits",
    "data",
    "cache",
    "logs",
]


class ProjectScaffolder:
    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir

    def scaffold(self, project_name: str, cms: str = "wordpress") -> Path:
        project_dir = self.projects_dir / project_name

        if project_dir.exists():
            raise SEOOSError(
                f"Project '{project_name}' already exists at {project_dir}"
            )

        for dir_name in PROJECT_DIRS:
            (project_dir / dir_name).mkdir(parents=True, exist_ok=True)

        self._write_project_yaml(project_dir / "config" / "project.yaml", project_name, cms)
        self._write_links_yaml(project_dir / "config" / "links.yaml")
        self._write_knowledge_templates(project_dir / "knowledge")
        self._write_data_files(project_dir / "data")

        logger.info(f"Scaffolded new project '{project_name}' at {project_dir}")
        return project_dir

    def _write_project_yaml(self, path: Path, project_name: str, cms: str = "wordpress") -> None:
        env_key = project_name.upper().replace("-", "_")
        template = {
            "name": project_name,
            "website": "https://example.com",
            "business_name": "Your Business Name",
            "business_type": "your business type",
            "country": "UK",
            "language": "en",
            "cms": cms,
            "seo_plugin": "rankmath",
            "image_source": "client",
            "publishing_method": "api",
            "tone_of_voice": "professional and friendly",
            "seo_goals": ["increase organic traffic", "improve keyword rankings"],
            "business_goals": ["generate leads", "increase revenue"],
            "competitors": ["competitor1.com", "competitor2.com"],
            "target_audience": "describe your target audience here",
            "integrations": {
                "wordpress": {
                    "enabled": False,
                    "url": "https://example.com",
                    "username_env": f"WP_{env_key}_USERNAME",
                    "password_env": f"WP_{env_key}_APP_PASSWORD",
                },
                "google": {
                    "enabled": False,
                    "credentials_env": f"GOOGLE_{env_key}_CREDENTIALS_FILE",
                    "gsc_site_url": "https://example.com/",
                    "ga4_property_id": "",
                },
                "shopify": {
                    "enabled": False,
                    "store_url": "",
                    "token_env": f"SHOPIFY_{env_key}_TOKEN",
                },
            },
            "active": True,
        }
        path.write_text(
            yaml.dump(template, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _write_links_yaml(self, path: Path) -> None:
        template = {
            "external_links": [
                {
                    "url": "https://example.com",
                    "anchor": "example anchor text",
                    "purpose": "authority",
                    "note": "Replace with pre-approved external links for this client",
                }
            ]
        }
        path.write_text(
            yaml.dump(template, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    def _write_knowledge_templates(self, knowledge_dir: Path) -> None:
        for filename in KNOWLEDGE_FILES:
            stem = filename.replace(".md", "")
            title = stem.replace("-", " ").title()
            content = (
                f"# {title}\n\n"
                f"<!-- Fill in {stem} details for this project -->\n"
            )
            (knowledge_dir / filename).write_text(content, encoding="utf-8")

    def _write_data_files(self, data_dir: Path) -> None:
        for filename, initial in DATA_FILES.items():
            (data_dir / filename).write_text(initial, encoding="utf-8")
