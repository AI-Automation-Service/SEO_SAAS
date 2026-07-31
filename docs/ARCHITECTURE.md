# Architecture

## Overview

SEO OS uses a Clean Architecture layered approach. Each layer has a single responsibility and only depends on layers below it.

```
Web Frontend (future SaaS)
    └── FastAPI (api/)          ← Phase 2+
CLI / Typer (cli/)              ← Phase 1+
    └── Agents (agents/)        ← orchestrators
            ├── Skills (skills/)            stateless capabilities
            ├── Integrations (integrations/) external API clients
            └── Core (core/)               config, loaders, models
```

## Technology Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.12+ | Native ecosystem for AI, crawling, SEO tooling |
| CLI | Typer | Terminal interface for operator use |
| Web API | FastAPI + uvicorn | REST API for future SaaS frontend (added Phase 2) |
| Storage | YAML + JSON files | Matches project-as-directory model |
| Scheduling | Ubuntu cron | Simple, no queue infrastructure |
| AI | OpenAI API (GPT-4o) | Powers all agents and skills |
| Logging | Loguru | Simple file + console structured logging |
| Testing | pytest | Standard Python testing |
| Deployment | git pull on Ubuntu VPS | Simple, no Docker needed |

## Directory Structure

```
seo-os/
├── cli/              # Typer CLI entry point
├── core/             # Config, project loader, secret manager, models
├── agents/           # Orchestrators (technical_seo, seo_strategy, content, monitoring)
├── skills/           # Stateless SEO capabilities (claude-seo SKILL.md files)
├── integrations/     # External API clients (WordPress, GSC, GA4, Shopify)
├── workflows/        # Multi-step orchestrated sequences
├── scheduler/        # Cron job configurations
├── shared/           # Logging, exceptions, shared utilities
├── projects/         # Per-client project directories (gitignored data)
├── scripts/          # Setup and maintenance scripts
├── tests/            # Unit and integration tests
└── docs/             # This documentation set
```

## Key Design Decisions

See DECISIONS.md for the full decision log.

- **Config over code:** All client-specific logic lives in project.yaml. No hardcoded business logic.
- **Agents orchestrate, Skills execute:** Agents make decisions; Skills perform stateless tasks.
- **Secrets never in config:** project.yaml references env var key names only. Real values live in .env on the VPS.
- **Skills from claude-seo:** 24 expert SKILL.md files provide the SEO knowledge layer. Downloaded via `scripts/download_skills.py`.

## Data Flow

```
Operator runs CLI command
    → CLI parses args
    → Agent loads project config + knowledge
    → Agent loads skill (SKILL.md prompt)
    → Agent calls OpenAI API with skill prompt + project context
    → GPT-4o returns structured analysis
    → Agent saves output to projects/<client>/reports/ or data/
    → Agent prints summary to terminal
```
