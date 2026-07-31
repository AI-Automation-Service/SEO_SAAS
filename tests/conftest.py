import pytest
import yaml
from pathlib import Path


@pytest.fixture
def projects_dir(tmp_path) -> Path:
    d = tmp_path / "projects"
    d.mkdir()
    return d


@pytest.fixture
def sample_project(projects_dir) -> tuple[str, Path]:
    name = "test-client"
    project_dir = projects_dir / name
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "knowledge").mkdir()
    (project_dir / "data").mkdir()

    config = {
        "name": name,
        "website": "https://test-client.com",
        "business_name": "Test Client Ltd",
        "business_type": "services",
        "country": "UK",
        "language": "en",
        "cms": "wordpress",
        "seo_plugin": "rankmath",
        "image_source": "client",
        "publishing_method": "api",
        "tone_of_voice": "professional",
        "seo_goals": ["increase traffic"],
        "business_goals": ["generate leads"],
        "competitors": ["competitor.com"],
        "target_audience": "UK small businesses",
        "active": True,
    }
    (project_dir / "config" / "project.yaml").write_text(
        yaml.dump(config, default_flow_style=False), encoding="utf-8"
    )
    (project_dir / "knowledge" / "brand.md").write_text(
        "# Brand\n\nWe are a professional services company based in the UK.",
        encoding="utf-8",
    )
    (project_dir / "knowledge" / "audience.md").write_text(
        "# Audience\n\nUK small business owners aged 30-55.",
        encoding="utf-8",
    )

    return name, project_dir
