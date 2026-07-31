import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_knowledge_loader, get_project_loader, get_scaffolder
from api.main import app
from core.knowledge import KnowledgeLoader
from core.project import ProjectLoader
from core.scaffold import ProjectScaffolder


@pytest.fixture
def client(projects_dir, sample_project):
    app.dependency_overrides[get_project_loader] = lambda: ProjectLoader(projects_dir)
    app.dependency_overrides[get_knowledge_loader] = lambda: KnowledgeLoader(projects_dir)
    app.dependency_overrides[get_scaffolder] = lambda: ProjectScaffolder(projects_dir)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_projects_includes_sample(client, sample_project):
    name, _ = sample_project
    r = client.get("/api/projects")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert name in names


def test_get_project_detail(client, sample_project):
    name, _ = sample_project
    r = client.get(f"/api/projects/{name}")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == name
    assert data["cms"] == "wordpress"
    assert "brand" in data["knowledge_files"]


def test_get_project_not_found(client):
    r = client.get("/api/projects/does-not-exist")
    assert r.status_code == 404


def test_validate_project_valid(client, sample_project):
    name, _ = sample_project
    r = client.get(f"/api/projects/{name}/validate")
    assert r.status_code == 200
    data = r.json()
    assert data["project"] == name
    assert data["valid"] is True


def test_validate_project_not_found(client):
    r = client.get("/api/projects/ghost/validate")
    assert r.status_code == 404


def test_create_project(client, projects_dir):
    r = client.post("/api/projects", json={"name": "new-client"})
    assert r.status_code == 201
    data = r.json()
    assert data["project"] == "new-client"
    assert (projects_dir / "new-client" / "config" / "project.yaml").exists()
    assert (projects_dir / "new-client" / "knowledge" / "brand.md").exists()


def test_create_project_duplicate(client, sample_project):
    name, _ = sample_project
    r = client.post("/api/projects", json={"name": name})
    assert r.status_code == 409


def test_list_skills(client):
    r = client.get("/api/skills")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
