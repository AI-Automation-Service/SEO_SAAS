from core.knowledge import KnowledgeLoader


def test_load_knowledge_returns_content(projects_dir, sample_project):
    name, _ = sample_project
    loader = KnowledgeLoader(projects_dir)
    knowledge = loader.load(name)
    assert "brand" in knowledge
    assert "audience" in knowledge
    assert "professional services" in knowledge["brand"]


def test_load_knowledge_empty_dir_returns_empty_dict(projects_dir, sample_project):
    name, project_dir = sample_project
    for f in (project_dir / "knowledge").iterdir():
        f.unlink()
    loader = KnowledgeLoader(projects_dir)
    assert loader.load(name) == {}


def test_load_knowledge_skips_empty_files(projects_dir, sample_project):
    name, project_dir = sample_project
    (project_dir / "knowledge" / "empty.md").write_text("", encoding="utf-8")
    loader = KnowledgeLoader(projects_dir)
    knowledge = loader.load(name)
    assert "empty" not in knowledge


def test_load_knowledge_skips_placeholder_files(projects_dir, sample_project):
    name, project_dir = sample_project
    (project_dir / "knowledge" / "tone.md").write_text(
        "<!-- Fill in tone details for this project -->", encoding="utf-8"
    )
    loader = KnowledgeLoader(projects_dir)
    knowledge = loader.load(name)
    assert "tone" not in knowledge


def test_load_knowledge_missing_dir_returns_empty_dict(tmp_path):
    loader = KnowledgeLoader(tmp_path)
    assert loader.load("nonexistent-project") == {}
