# Contributing

This is a private internal tool. These guidelines are for the operator maintaining the platform.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/AI-Automation-Service/SEO_SAAS.git seo-os
cd seo-os

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -e ".[dev]"

# Copy env file and fill in values
cp .env.example .env

# Download skills from claude-seo
python scripts/download_skills.py

# Verify setup
seo-os list-projects
seo-os list-skills
```

## Adding a New Client

1. Create the project directory:
   ```
   projects/<client-name>/
       config/project.yaml
       knowledge/brand.md
       knowledge/audience.md
       knowledge/competitors.md
   ```
2. Copy `projects/client-example/config/project.yaml` and fill in all fields.
3. Add client secrets to `.env` on the VPS.
4. Run `seo-os info <client-name>` to verify the config loads correctly.

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md`
2. The skill is automatically available via `SkillLoader`
3. Reference it in an agent using `SkillLoader().load("<skill-name>")`

## Adding a New Integration

1. Create `integrations/<name>/client.py`
2. Extend `BaseIntegration` from `integrations/base.py`
3. Implement `validate_credentials()` and `health_check()`

## Code Standards

- Python 3.12+
- Type hints on all function signatures
- No hardcoded client data anywhere in the codebase
- All secrets via environment variables
- No silent failures — log errors explicitly

## Testing

```bash
pytest tests/unit/
pytest tests/integration/
```
