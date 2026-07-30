# Changelog

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
