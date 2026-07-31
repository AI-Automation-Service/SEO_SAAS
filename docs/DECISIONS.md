# Architecture Decision Records (ADR)

## ADR-001 — Python as the primary language

**Problem:** Choose a programming language for the platform.  
**Alternatives:** TypeScript/Node.js, Go  
**Decision:** Python 3.12+  
**Reasoning:** Python owns the AI/LLM/SEO/crawling ecosystem. Every required library (Anthropic SDK, httpx, pyyaml, playwright, beautifulsoup) has mature Python support. TypeScript would fight the ecosystem constantly.  
**Consequences:** Slightly higher memory usage vs Go, but acceptable for this use case.  
**Status:** Approved  
**Date:** 2026-07-31  

---

## ADR-002 — CLI interface, no web API

**Problem:** Choose an interface layer.  
**Alternatives:** FastAPI web server, Django, Streamlit  
**Decision:** Typer CLI  
**Reasoning:** This is an internal tool used by one operator. A web server adds infrastructure complexity (process management, ports, auth) with no benefit at this stage.  
**Consequences:** No web UI. All interaction is terminal-based. A web UI can be added in a future phase if needed.  
**Status:** Approved  
**Date:** 2026-07-31  

---

## ADR-003 — File-based storage (YAML + JSON), no database

**Problem:** Choose a storage layer for project data.  
**Alternatives:** PostgreSQL, SQLite, MongoDB  
**Decision:** YAML files for config, JSON files for structured data, Markdown for knowledge  
**Reasoning:** The project-as-directory model in the spec maps naturally to files. No database infrastructure to manage. Data is human-readable and editable. For the current scale (dozens of clients), this is sufficient.  
**Consequences:** No complex queries. If we ever need full-text search or relational queries across hundreds of clients, we will revisit this decision.  
**Status:** Approved  
**Date:** 2026-07-31  

---

## ADR-004 — Ubuntu cron for scheduling, no Celery/Redis

**Problem:** Choose a task scheduling and execution system.  
**Alternatives:** Celery + Redis, APScheduler, RQ  
**Decision:** Ubuntu cron jobs  
**Reasoning:** Cron is already available on the VPS. Adding Celery requires Redis, worker processes, and operational overhead. For a single-operator tool with simple periodic jobs, cron is sufficient.  
**Consequences:** No distributed task queues. No retry logic built-in. If the platform grows to need complex workflow orchestration, we will add a queue system then.  
**Status:** Approved  
**Date:** 2026-07-31  

---

## ADR-005 — claude-seo skills as the SEO knowledge layer

**Problem:** Build SEO skill prompts from scratch or reuse existing ones.  
**Alternatives:** Write all skill prompts internally  
**Decision:** Use the 24 SKILL.md files from github.com/AgricIDaniel/claude-seo (MIT license)  
**Reasoning:** These are expert-level, up-to-date SEO audit frameworks covering technical SEO, content, schema, AEO/GEO, local SEO, and more. Building equivalent quality from scratch would take significant time.  
**Consequences:** We depend on an external repo. Skills are downloaded via `scripts/download_skills.py`. If the upstream repo changes breaking our agents, we pin to a specific commit.  
**Status:** Approved  
**Date:** 2026-07-31  

---

## ADR-006 — Secrets via environment variables only

**Problem:** How to handle API credentials for multiple clients.  
**Decision:** All secrets are environment variable references. project.yaml stores only the key NAME (e.g. `WORDPRESS_CLIENT_A_KEY`). Real values live in `.env` on the VPS only, never committed to git.  
**Reasoning:** Prevents credential leaks via git history. Supports credential rotation without config changes.  
**Status:** Approved  
**Date:** 2026-07-31  

---

## ADR-008 — FastAPI web API added alongside CLI (supersedes ADR-002)

**Problem:** The platform needs to eventually support a web dashboard (SaaS) for managing multiple clients without requiring terminal access.  
**Supersedes:** ADR-002 (CLI-only interface)  
**Decision:** Add a FastAPI layer alongside the existing Typer CLI. Both interfaces use the same core loaders and models. Neither replaces the other.  
**Reasoning:** Clean Architecture means the interface layer is independent of the core. Adding FastAPI costs one new `api/` package and does not modify existing CLI or core code. Deferring this decision would require a large refactor later. CORS is included from day one to allow a future web frontend.  
**Consequences:** The API runs as a separate process (`uvicorn api.main:app`). No authentication yet — internal network only in Phase 2. Auth will be added in the SaaS phase.  
**Status:** Approved  
**Date:** 2026-07-31  

---

## ADR-009 — OpenAI API as the AI provider (corrects ARCHITECTURE.md error)

**Problem:** ARCHITECTURE.md incorrectly stated "Anthropic Claude API" as the AI provider.  
**Decision:** All agents call the OpenAI API (GPT-4o by default). The `OPENAI_API_KEY` env var is used. No Anthropic SDK dependency.  
**Reasoning:** User requirement confirmed at project start.  
**Status:** Approved  
**Date:** 2026-07-31  

---

## ADR-007 — Deployment via git pull, no Docker

**Problem:** How to deploy the platform to the Ubuntu VPS.  
**Decision:** `git clone` on first deploy, `git pull` + restart for updates. No Docker.  
**Reasoning:** The user already has a configured Ubuntu VPS with other projects. Docker adds overhead. git pull is simple and predictable.  
**Consequences:** Python and dependencies must be installed on the VPS directly via pip/venv.  
**Status:** Approved  
**Date:** 2026-07-31  
