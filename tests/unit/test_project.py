import pytest
import yaml

from core.project import ProjectLoader
from shared.exceptions import ProjectConfigError, ProjectNotFoundError


def test_list_projects_empty(projects_dir):
    loader = ProjectLoader(projects_dir)
    assert loader.list_projects() == []


def test_list_projects_returns_name(projects_dir, sample_project):
    name, _ = sample_project
    loader = ProjectLoader(projects_dir)
    assert name in loader.list_projects()


def test_load_valid_project(projects_dir, sample_project):
    name, _ = sample_project
    loader = ProjectLoader(projects_dir)
    config = loader.load(name)
    assert config.name == name
    assert config.business_name == "Test Client Ltd"
    assert config.cms == "wordpress"
    assert config.seo_plugin == "rankmath"
    assert config.image_source == "client"
    assert config.active is True


def test_load_missing_project_raises(projects_dir):
    loader = ProjectLoader(projects_dir)
    with pytest.raises(ProjectNotFoundError):
        loader.load("does-not-exist")


def test_load_missing_config_file_raises(projects_dir):
    project_dir = projects_dir / "no-config"
    (project_dir / "config").mkdir(parents=True)
    loader = ProjectLoader(projects_dir)
    with pytest.raises(ProjectConfigError):
        loader.load("no-config")


def test_load_invalid_yaml_raises(projects_dir):
    project_dir = projects_dir / "bad-yaml"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "config" / "project.yaml").write_text(
        "name: [broken yaml:", encoding="utf-8"
    )
    loader = ProjectLoader(projects_dir)
    with pytest.raises(ProjectConfigError):
        loader.load("bad-yaml")


def test_load_empty_yaml_raises(projects_dir):
    project_dir = projects_dir / "empty"
    (project_dir / "config").mkdir(parents=True)
    (project_dir / "config" / "project.yaml").write_text("", encoding="utf-8")
    loader = ProjectLoader(projects_dir)
    with pytest.raises(ProjectConfigError):
        loader.load("empty")


def test_load_missing_required_field_raises(projects_dir):
    project_dir = projects_dir / "incomplete"
    (project_dir / "config").mkdir(parents=True)
    # Missing required fields like business_name
    (project_dir / "config" / "project.yaml").write_text(
        yaml.dump({"name": "incomplete", "website": "https://example.com"}),
        encoding="utf-8",
    )
    loader = ProjectLoader(projects_dir)
    with pytest.raises(ProjectConfigError):
        loader.load("incomplete")
