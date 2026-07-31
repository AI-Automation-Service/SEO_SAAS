# Changelog

## [Unreleased] — Phase 2

### Added
- `core/knowledge.py` — KnowledgeLoader: reads all `knowledge/*.md` files per project
- `core/scaffold.py` — ProjectScaffolder: creates full project folder structure + all template files
- `core/models/context.py` — ProjectContext: bundles config + knowledge + paths for agents
- `core/models/project.py` — Added `seo_plugin` and `image_source` fields to ProjectConfig
- `api/` — FastAPI layer with CORS, health check, project and skills endpoints
- `api/routers/projects.py` — GET/POST projects, GET project detail, GET validate
- `api/routers/skills.py` — GET skills list
- `api/dependencies.py` — Injectable loaders for FastAPI dependency injection
- `api/models/responses.py` — Pydantic response schemas
- `cli/main.py` — Added `add-project` and `validate-project` commands
- `scripts/start_api.sh` — Convenience script to start the API server
- `tests/conftest.py` — Shared pytest fixtures (projects_dir, sample_project)
- `tests/unit/test_project.py` — Unit tests for ProjectLoader
- `tests/unit/test_knowledge.py` — Unit tests for KnowledgeLoader
- `tests/integration/test_api.py` — Integration tests for all API endpoints
- `projects/client-example/knowledge/` — All 13 knowledge template files
- `projects/client-example/data/` — All 9 initialised data files
- `projects/client-example/config/links.yaml` — External links template

### Changed
- FastAPI added alongside CLI (supersedes ADR-002 — see ADR-008)
- Dependencies: added `fastapi>=0.111.0`, `uvicorn[standard]>=0.30.0`

---

## [Unreleased] — Phase 1

### Added
- Full project folder structure
- `core/models/project.py` — ProjectConfig Pydantic model
- `core/project.py` — ProjectLoader
- `core/config.py` — AppConfig (env var loading via pydantic-settings)
- `core/secrets.py` — SecretManager
- `shared/exceptions.py` — Base exception hierarchy
- `shared/logging.py` — Loguru setup
- `skills/base.py` — SkillLoader
- `integrations/base.py` — BaseIntegration interface
- `cli/main.py` — Typer CLI with list-projects, list-skills, info commands
- `scripts/download_skills.py` — Downloads 24 SKILL.md files from claude-seo
- `projects/client-example/` — Example project template with config + knowledge files
- `pyproject.toml`, `.env.example`, `.gitignore`
- Full documentation set (PRD, ARCHITECTURE, DECISIONS, ROADMAP, CHANGELOG, LESSONS_LEARNED, CONTRIBUTING)
