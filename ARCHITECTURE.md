# SEO OS — AI Agent Architecture

**Version:** 1.0  
**Status:** Authoritative. All future agents, prompts, and refactors must conform to this document.  
**Audience:** Developers, AI assistants, and anyone adding or modifying agents in SEO OS.

---

## Table of Contents

1. [Core Principles](#1-core-principles)
2. [Layer Map](#2-layer-map)
3. [BaseAgent](#3-baseagent)
4. [Router](#4-router)
5. [Prompt Composition](#5-prompt-composition)
6. [Agent Identity (`identity.md`)](#6-agent-identity-identitymd)
7. [SKILL.md](#7-skillmd)
8. [Shared Documents](#8-shared-documents)
9. [Runtime Context](#9-runtime-context)
10. [Output Contracts (Pydantic)](#10-output-contracts-pydantic)
11. [Validation](#11-validation)
12. [Agent Registry](#12-agent-registry)
13. [Folder Structure](#13-folder-structure)
14. [Responsibility Matrix](#14-responsibility-matrix)
15. [Adding a New Agent](#15-adding-a-new-agent)

---

## 1. Core Principles

These five rules take precedence over all other decisions. When in doubt, return here.

**P1 — Static knowledge in the system prompt. Dynamic state in the user message.**  
If a value changes between calls (page content, business name, platform flags), it is runtime context and belongs in the user message. If it is the same for every call to this agent (SEO theory, writing standards, domain heuristics), it belongs in the system prompt layers.

**P2 — Contracts in code, not prose.**  
A JSON field name written in a SKILL.md is a lie waiting to happen. Pydantic is the only authoritative schema. Any SKILL.md description of a JSON field will eventually drift from the actual contract. Pydantic catches this immediately. Prose never does.

**P3 — Shared rules in one place.**  
Any instruction that appears in more than one agent is a shared document waiting to be extracted. The threshold is two agents, not three. Copy-paste across prompts creates maintenance debt that compounds with every new agent.

**P4 — Validation is never a prompt responsibility.**  
Self-audit checklists inside prompts are not validation. They are polite suggestions the model may or may not follow, with zero enforcement. Python validates. Pydantic enforces. Prompts guide. These roles must not be confused.

**P5 — An agent that knows about another agent is a design error.**  
Agents have no awareness of each other. Each agent receives a task, produces output, and returns. Orchestration is entirely the router's responsibility. Agent isolation is what makes a 30-agent system debuggable.

---

## 2. Layer Map

```
┌──────────────────────────────────────────────────────────────────┐
│  Router (api/routers/*.py)                                       │
│  Selects agent, assembles runtime context, validates output,     │
│  writes to DB, routes to WordPress/Shopify                       │
└───────────────────────┬──────────────────────────────────────────┘
                        │ calls
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│  PromptComposer (agents/composer.py)  [FUTURE]                   │
│  Assembles system prompt from: platform identity +               │
│  agent identity + SKILL.md + shared docs + output discipline     │
└───────────────────────┬──────────────────────────────────────────┘
                        │ passes composed prompt to
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│  BaseAgent (agents/base.py)                                      │
│  Executes OpenAI call, handles retry, logs cost, normalizes errors│
└───────────────────────┬──────────────────────────────────────────┘
                        │ returns raw string
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│  Pydantic Contract (contracts/*.py)                              │
│  Parses and validates the raw response against the schema        │
└──────────────────────────────────────────────────────────────────┘
```

Each layer has exactly one job. No layer does another layer's job.

---

## 3. BaseAgent

BaseAgent is **infrastructure**. It is the HTTP client of AI calls. It knows *how* to call GPT — never *what* to say.

### What BaseAgent owns

| Responsibility | Detail |
|---|---|
| OpenAI API call | Model, temperature, json_mode, max_tokens, timeout — all configurable per call |
| Retry logic | Exponential backoff on rate limits and transient network errors; max 3 retries |
| Token counting | Input and output tokens extracted from every response |
| Cost calculation | `input_tokens × input_rate + output_tokens × output_rate` per model |
| AIHistory logging | One row per call: agent_name, model, tokens, cost, duration_ms, status, error_detail |
| Error normalization | API errors, rate limits, timeouts → typed exceptions the router handles |
| Response extraction | Raw OpenAI response → string; BaseAgent does NOT parse or validate domain content |
| Timeout enforcement | Hard cutoff; logs status = "timeout" to AIHistory |

### What BaseAgent must NEVER own

- Prompt content of any kind
- Domain knowledge (SEO, writing, clustering, content strategy)
- Output schema definitions or parsing
- Routing decisions (which agent handles which task)
- Business context (project data, user data, platform state)
- Capability checks (the router knows the user's plan — BaseAgent does not)
- Composition logic (how to assemble a prompt)

**The test:** if this logic could be reused to call any LLM for any purpose with zero modification, it belongs in BaseAgent. If it mentions SEO, content, or WordPress — it does not.

---

## 4. Router

The router is the **orchestrator**. It is the only layer with full context: user plan, project data, platform state, and which agent to call.

### What the router owns

| Responsibility | Detail |
|---|---|
| Agent selection | Decides which agent(s) to call based on page profile, user request, and capability flags |
| Capability checks | Verifies the user's plan allows the requested operation before any AI call |
| Context assembly | Builds the runtime context block (business, platform, content, preferences) |
| Prompt assembly call | Passes agent name and shared doc list to PromptComposer |
| BaseAgent call | Passes composed prompt + user message to BaseAgent |
| Pydantic validation | Parses BaseAgent output through the agent's Pydantic contract |
| Business rule assertions | Word count, required link presence, required fields — enforced after parsing |
| DB write | Writes AIHistory, PageChange, or other records |
| CMS routing | Sends approved changes to WordPress or Shopify |
| Error handling | Catches BaseAgent exceptions, decides retry vs. fail vs. partial success |

### What the router must NEVER own

- Domain knowledge (no SEO logic embedded in Python router code)
- Prompt content beyond runtime context injection
- OpenAI call mechanics
- Schema definitions

---

## 5. Prompt Composition

Every agent call assembles two components: a **system prompt** (stable, cached) and a **user message** (dynamic, per-call).

```
SYSTEM PROMPT — assembled once per agent call type, eligible for OpenAI caching:

  ┌─────────────────────────────────────────────────────┐
  │ 1. Platform Identity (shared/platform-identity.md)  │
  │    "You are an AI agent in SEO OS, a production     │
  │    SaaS platform for SEO management. You work with  │
  │    real client websites. Accuracy is non-negotiable."│
  ├─────────────────────────────────────────────────────┤
  │ 2. Agent Identity (skills/<agent>/identity.md)      │
  │    Role, mission, scope, behavioral constraints     │
  ├─────────────────────────────────────────────────────┤
  │ 3. SKILL.md (skills/<agent>/SKILL.md)               │
  │    Domain expertise specific to this agent          │
  ├─────────────────────────────────────────────────────┤
  │ 4. Shared Documents (declared in agent registry)    │
  │    e.g., eeat-framework.md + writing-rules.md       │
  ├─────────────────────────────────────────────────────┤
  │ 5. Output Discipline (shared/json-output-discipline)│
  │    "Respond with valid JSON only."                  │
  └─────────────────────────────────────────────────────┘

USER MESSAGE — assembled per call, never cached:

  ┌─────────────────────────────────────────────────────┐
  │ 6. Runtime Context                                   │
  │    Business, platform, content, preferences, history│
  ├─────────────────────────────────────────────────────┤
  │ 7. Task                                              │
  │    What to do right now — scoped and unambiguous    │
  ├─────────────────────────────────────────────────────┤
  │ 8. Output Hint (optional)                           │
  │    Field list for guidance only. Pydantic enforces. │
  └─────────────────────────────────────────────────────┘
```

### Why this composition model scales

- **Adding a new agent** requires only: `identity.md` + `SKILL.md` + registry entry. BaseAgent, composer, and all shared docs are untouched.
- **Adding a new platform** (Webflow, Wix) requires only: new runtime context fields in Python. No prompt files change.
- **Updating writing rules** requires only: editing `skills/shared/writing-rules.md`. All agents that load this document receive the change immediately. No other files change.
- **Changing an output schema** requires only: editing one Pydantic model. The prompt is unaffected. Pydantic catches violations immediately.
- **OpenAI prompt caching** applies to the system prompt prefix (layers 1–5), which is stable across calls for the same agent. Runtime context (layers 6–8) is in the user message and is never cached — as it should be.

---

## 6. Agent Identity (`identity.md`)

Every agent has an `identity.md` file. This is the **"who am I"** document.

### What belongs in identity.md

| Section | Content |
|---|---|
| **Role** | One sentence. "You are the SEO Content Analyzer for SEO OS." |
| **Mission** | The outcome this agent produces — not what it does, but what it produces for the subscriber. |
| **Scope** | Explicit boundaries: what this agent is responsible for, and what it must not do. |
| **Non-Goals** | Explicit list of tasks that belong to other agents or the router. |
| **Constraints** | Hard behavioral rules that override all other instructions. |
| **Shared Documents** | Declarative list of which shared docs this agent loads (consumed by the composer). |

### What must NOT be in identity.md

- JSON schema or field names
- Anti-AI word lists (those live in `skills/shared/writing-rules.md`)
- Platform field documentation (`is_homepage`, `builder`, etc.)
- Validation checklists
- Example inputs or outputs in structured format
- Any runtime value

**The stability test:** if you printed this file in twelve months, would it still be accurate without any changes? If a change to the output schema or runtime context fields would make it stale — that content belongs elsewhere.

See `skills/_templates/identity.md` for the standard template.

---

## 7. SKILL.md

SKILL.md is **domain expertise**. It is the "what do I know" document.

It is what makes the SEO Analyzer different from the Article Writer different from the Humanizer. It should read like a domain expert's operating manual — comprehensible to a human SEO professional with zero knowledge of the codebase.

### What belongs in SKILL.md

| Content type | Example |
|---|---|
| SEO theory and methodology | How Google evaluates quality, what signals matter and why |
| Domain-specific decision heuristics | "Keyword density above 3% signals stuffing; below 0.3% signals thin content" |
| Decision rules for this agent's specific job | "When is_homepage, prioritize brand positioning over keyword targeting" |
| Quality thresholds with meaning | What a score of 80+ means vs. 40–60 vs. below 40 |
| Edge case handling | "If the page has no headings, flag it — do not fabricate headings" |
| Agent-specific workflow | The internal reasoning process for this agent's primary task |

### What must NEVER be in SKILL.md

| Forbidden content | Correct location |
|---|---|
| JSON field names or output schema | `contracts/*.py` (Pydantic) |
| Anti-AI word blacklist | `skills/shared/writing-rules.md` |
| E-E-A-T framework text | `skills/shared/eeat-framework.md` |
| Input field documentation | Injected as runtime context at call time |
| Validation checklists | Python assertions in the router |
| Platform-specific conditional logic | Python router resolves this; agent receives resolved values |
| Any value that changes between calls | Runtime context (user message) |

**The test:** if a line in SKILL.md references a JSON field name, a Python variable, or a database column — it is in the wrong file.

See `skills/_templates/SKILL.md` for the standard template.

---

## 8. Shared Documents

Shared documents are **canonical, versioned, cross-agent rules**. They are loaded into the system prompt by the PromptComposer at call time — never copy-pasted, never summarized.

### Document catalog

| File | Purpose | Agents that load it |
|---|---|---|
| `skills/shared/platform-identity.md` | The "you are in SEO OS" foundation statement | All agents |
| `skills/shared/writing-rules.md` | Anti-AI word blacklist, sentence-level patterns, active voice rules | Article writer, editor, humanizer, content-strategy |
| `skills/shared/eeat-framework.md` | Full E-E-A-T doctrine: experience, expertise, authoritativeness, trustworthiness | Article writer, editor, analyzer, content-strategy |
| `skills/shared/seo-standards.md` | Keyword placement, heading hierarchy, meta tag standards, title/description length | Analyzer, editor, meta, article writer |
| `skills/shared/internal-linking.md` | Hub/spoke model, anchor text rules, link density guidelines | Article writer, editor |
| `skills/shared/content-safety.md` | YMYL handling, citation requirements, accuracy standards | Article writer, editor, content-strategy |
| `skills/shared/json-output-discipline.md` | "Your response must be valid JSON. No markdown fences." | All agents that return structured output |

### Shared document rules

1. **One canonical version.** Never copy a shared document into a SKILL.md. The composer loads it.
2. **Documents are independent.** No shared doc references another shared doc.
3. **Loaded by configuration, not hard-coded.** Each agent's registry entry declares which docs it needs.
4. **PromptComposer loads them; the router specifies which ones.** BaseAgent has no knowledge of shared docs.
5. **Adding a new shared document** does not require modifying any agent. Update the registry entry for agents that should load it.

---

## 9. Runtime Context

Runtime context is **everything that changes between calls**. It belongs in the user message — never in any static file.

### Context categories

| Category | Fields | Source |
|---|---|---|
| **Business context** | `business_name`, `about`, `products_services`, `target_audience`, `brand_voice`, `competitors_notes`, `seo_context` | `ProjectKnowledge` table |
| **Platform context** | `is_homepage`, `is_theme_controlled`, `builder`, `has_yoast`, `has_rankmath`, `has_elementor` | Resolved by Python before the call |
| **Content context** | `html_content`, `current_meta_title`, `current_meta_description`, `word_count` | WordPress REST API |
| **SEO context** | `main_keyword`, `hub_url`, `cluster_name`, `current_position`, `search_volume`, `intent` | `Keyword` table |
| **Execution context** | `current_date`, `plan_phase`, `cron_job_id`, `article_job_id` | Router |
| **Project preferences** | Distilled rules from `ProjectPreferences` | `feedback-distiller` output |
| **Change history** | Recent approved changes to this page | `PageChange` table |
| **Subscriber instruction** | User-provided specific request for this call | Request body |

### Runtime context rules

- **Python resolves before the call.** The agent never receives raw ambiguous signals. It receives `builder: "elementor"` — not "figure out the builder from this HTML."
- **Format is `## field_name\n{value}` consistently across all agents.** Agents learn one format; it applies everywhere.
- **Absent fields are omitted entirely.** If no brand_voice exists, that section is not included. Empty strings are not sent.
- **Context is the user message. Expertise is the system prompt.** This boundary is absolute and must never be crossed.

---

## 10. Output Contracts (Pydantic)

Output contracts live **exclusively in Pydantic models**. Nowhere else.

### Location: `contracts/*.py`

One file per agent that returns structured output. The Pydantic model is the schema. It is the single source of truth.

### What each layer contributes

| Layer | What it says about output |
|---|---|
| `contracts/*.py` | Field names, types, validators, range checks, required vs optional — everything |
| `skills/shared/json-output-discipline.md` | "Your response must be valid JSON. No markdown fences." — one behavioral instruction |
| `SKILL.md` | Semantic meaning of important fields — what a `severity: "critical"` *means* to the agent, not its type |
| `identity.md` | Nothing about schema |

### Why not in SKILL.md

A Pydantic model is verified at parse time. A JSON schema written in SKILL.md prose is never verified. The moment Python renames a field, the SKILL.md description becomes a lie that GPT believes — silently producing the wrong field name that `json.loads()` accepts and forwards. Pydantic raises `ValidationError` immediately. Prose never does.

### Why not in prompt text

Listing 25 fields in prompt text consumes tokens, inflates the system prompt (defeating caching), and still enforces nothing. Pydantic enforces it. The prompt needs only to instruct JSON output.

---

## 11. Validation

Validation is **entirely Python's responsibility**. Prompt-level checklists are not validation.

### Validation stack (in order)

| Stage | Layer | Checks |
|---|---|---|
| 1. Structural | `json.loads()` | Valid JSON syntax |
| 2. Schema | `Pydantic.model_validate_json()` | Field presence, correct types, format |
| 3. Range | Pydantic validators | Scores 0–100, non-empty required strings, valid URLs |
| 4. Business rules | Python assertions in router | Word count ≥ minimum, required internal link present, required sections present |
| 5. Content | Python parsers | HTML validity, image alt text presence, internal link count |
| 6. Retry trigger | Router | Validation failure → retry with error in context, or raise HTTP 500, or log and continue |

### The one acceptable prompt instruction about validation

> "Your response must be valid JSON."

This is a behavioral instruction, not a checklist. It tells the model what form to use. Python handles what that JSON contains.

**Self-audit checklists ("before responding, verify that…") must not appear in any agent prompt.** They create false confidence that enforcement is happening. It is not. Remove them; replace with Python assertions.

---

## 12. Agent Registry

The registry is the **single source of truth for every agent's configuration**. It maps agent name to everything the system needs to call it correctly.

See `agents/REGISTRY_SPEC.md` for the full specification.

### What every agent registers

| Field | Type | Purpose |
|---|---|---|
| `name` | string | Unique identifier; matches the `skills/<name>/` folder |
| `model` | string | `gpt-4o` or `gpt-4o-mini` — determined by task complexity |
| `temperature` | float | 0.0–1.0; lower for structured output, higher for creative writing |
| `timeout` | int | Seconds; scales with expected output length |
| `max_tokens` | int | Upper bound on output; prevents runaway generation |
| `shared_docs` | list[str] | Names of shared documents to load into system prompt |
| `contract` | class | The Pydantic model class for response parsing |
| `capabilities` | list[str] | Required user capabilities (e.g., `AI_WRITER`, `GSC`) |
| `description` | string | One-sentence human-readable description |

### Model selection rule

| Task type | Model |
|---|---|
| Writing, editing, rewriting, long-form generation | `gpt-4o` |
| Analysis, classification, clustering, meta generation, scoring | `gpt-4o-mini` |

This rule is enforced by the registry. No router should hard-code a model name.

---

## 13. Folder Structure

```
seo-os/
│
├── ARCHITECTURE.md              ← This document. The single source of truth.
│
├── agents/
│   ├── base.py                  ← BaseAgent: call, retry, logging, cost tracking
│   ├── composer.py              ← PromptComposer: assembles system prompt from parts
│   ├── registry.py              ← Maps agent name → model, shared_docs, contract, etc.
│   └── REGISTRY_SPEC.md         ← Human-readable specification for the registry schema
│
├── skills/
│   │
│   ├── _templates/
│   │   ├── identity.md          ← Standard template for all agent identity files
│   │   └── SKILL.md             ← Standard template for all agent skill files
│   │
│   ├── shared/
│   │   ├── platform-identity.md ← "You operate within SEO OS..."
│   │   ├── writing-rules.md     ← Anti-AI words, sentence patterns, voice/tone
│   │   ├── eeat-framework.md    ← E-E-A-T doctrine and signals
│   │   ├── seo-standards.md     ← Keyword placement, headings, meta standards
│   │   ├── internal-linking.md  ← Hub/spoke model, anchor text, link density
│   │   ├── content-safety.md    ← YMYL, citations, accuracy standards
│   │   └── json-output-discipline.md  ← "Respond with valid JSON only."
│   │
│   ├── seo-analyzer/
│   │   ├── identity.md          ← Role, mission, scope, constraints, shared doc list
│   │   └── SKILL.md             ← SEO analysis domain expertise
│   │
│   ├── seo-editor/
│   │   ├── identity.md
│   │   └── SKILL.md
│   │
│   ├── seo-article-writer/
│   │   ├── identity.md
│   │   └── SKILL.md
│   │
│   └── [one folder per agent — always identity.md + SKILL.md, nothing else]
│
├── contracts/
│   ├── analyzer.py              ← AnalyzerResponse Pydantic model
│   ├── editor.py                ← EditorResponse Pydantic model
│   ├── article.py               ← ArticlePhase1/2/3Response Pydantic models
│   ├── meta.py                  ← MetaResponse Pydantic model
│   ├── cluster.py               ← ClusterResponse Pydantic model
│   ├── schema.py                ← SchemaResponse Pydantic model
│   ├── humanizer.py             ← HumanizerResponse Pydantic model
│   └── [one file per agent that returns structured output]
│
├── prompts/
│   └── context_builder.py       ← Python functions that assemble runtime context blocks
│                                   build_business_block(), build_platform_block(),
│                                   build_content_block(), build_preferences_block()
│
└── api/
    └── routers/                 ← Orchestration only; no domain knowledge embedded here
```

---

## 14. Responsibility Matrix

| Layer | Owns | Never Owns |
|---|---|---|
| **BaseAgent** | OpenAI call, retry, token counting, cost tracking, AIHistory logging, error normalization | Prompt content, domain knowledge, schema, routing, capability checks |
| **Router** | Agent selection, capability checks, context assembly, Pydantic validation, business rule assertions, DB writes, CMS routing | AI call mechanics, domain knowledge, prompt content, schema definitions |
| **Agent Identity** (`identity.md`) | Agent role, mission, scope, behavioral hard-constraints, shared doc declarations | JSON schema, field names, writing rules, platform field descriptions, validation checklists |
| **SKILL.md** | Domain expertise, decision heuristics, quality thresholds, edge case handling, agent-specific reasoning workflow | JSON schema, anti-AI word lists, E-E-A-T text, input field documentation, validation checklists, any runtime values |
| **Shared Documents** | Canonical cross-agent rules (writing, SEO, E-E-A-T, linking, safety) | Agent-specific logic, runtime values, JSON schema, content specific to one agent |
| **Runtime Context** | Per-call state: business profile, platform resolution, current content, preferences, task | Stable knowledge, domain expertise, schema definitions |
| **Pydantic Models** (`contracts/`) | Output schema, field names and types, range validators, required vs optional | Domain knowledge, prompt assembly, business logic |
| **PromptComposer** | Assembling system prompt in correct layer order, loading shared docs by name | Deciding which docs to load (registry owns that), any domain content |
| **Agent Registry** | Agent name → model, temperature, timeout, shared_docs, contract, capabilities | AI call execution, domain knowledge, prompt content |

---

## 15. Adding a New Agent

Follow this checklist every time a new agent is introduced.

**Before writing any prompts:**
- [ ] Define the agent's single responsibility. Can it be stated in one sentence?
- [ ] Confirm it does not overlap with an existing agent's scope.
- [ ] Identify which existing shared documents it needs.
- [ ] Identify which (if any) new shared documents need to be created first.

**Prompt files (create in `skills/<agent-name>/`):**
- [ ] `identity.md` — using `skills/_templates/identity.md` as base
- [ ] `SKILL.md` — using `skills/_templates/SKILL.md` as base
- [ ] Verify: no JSON field names in either file
- [ ] Verify: no anti-AI word list in either file
- [ ] Verify: no validation checklist in either file

**Contract (create in `contracts/`):**
- [ ] Define Pydantic response model with all fields, types, and validators
- [ ] Confirm every field the SKILL.md semantically references exists in the model

**Registry (update `agents/registry.py`):**
- [ ] Add entry with: name, model, temperature, timeout, max_tokens, shared_docs, contract, capabilities, description
- [ ] Confirm model follows the gpt-4o / gpt-4o-mini selection rule

**Router:**
- [ ] Wire the agent call using BaseAgent + PromptComposer
- [ ] Parse response through the Pydantic contract
- [ ] Add Python assertions for business rules
- [ ] Log to AIHistory

**Documentation:**
- [ ] Update `AGENTS.md` agent registry table

**Tests:**
- [ ] Add at least one test for the Pydantic contract parsing
- [ ] Add at least one test for the Python business rule assertions

---

*This document supersedes the earlier `docs/ARCHITECTURE.md` for all AI agent decisions.*  
*The `docs/ARCHITECTURE.md` remains as historical reference for the system's clean architecture layers.*
