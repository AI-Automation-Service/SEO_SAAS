# SEO OS — AI Agent Architecture

**Version:** 1.1  
**Status:** Authoritative. All future agents, prompts, and refactors must conform to this document.  
**Audience:** Developers, AI assistants, and anyone adding or modifying agents in SEO OS.

**Changelog:**  
- v1.1: Resolved 8 issues from design review — retry ownership, shared_docs authority, SKILL.md test rule, removed Output Hint layer, added platform-identity auto-loading, added Migration Guide, created contracts/ layer, clarified all responsibilities.
- v1.0: Initial architecture definition.

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
11. [Validation and Retry](#11-validation-and-retry)
12. [Agent Registry](#12-agent-registry)
13. [Folder Structure](#13-folder-structure)
14. [Responsibility Matrix](#14-responsibility-matrix)
15. [Adding a New Agent](#15-adding-a-new-agent)
16. [Migrating an Existing Agent](#16-migrating-an-existing-agent)

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
│  Selects agent, checks capabilities, assembles runtime context,  │
│  calls PromptComposer, calls BaseAgent, validates via Pydantic,  │
│  enforces business rules, writes to DB, routes to CMS            │
└───────────────────────┬──────────────────────────────────────────┘
                        │ calls
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│  PromptComposer (agents/composer.py)  [FUTURE]                   │
│  Auto-loads platform-identity.md + assembles system prompt from: │
│  agent identity → SKILL.md → registry shared docs → output disc. │
└───────────────────────┬──────────────────────────────────────────┘
                        │ passes composed system prompt + user message to
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│  BaseAgent (agents/base.py)                                      │
│  Executes OpenAI call, handles transport retry, logs cost        │
└───────────────────────┬──────────────────────────────────────────┘
                        │ returns raw string
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│  Router (validation phase)                                       │
│  Parses raw string via Pydantic contract, enforces business rules│
│  Decides: accept / retry with error context / raise HTTP error   │
└──────────────────────────────────────────────────────────────────┘
```

Each layer has exactly one job. Validation is in the router, not BaseAgent, because BaseAgent does not own schema knowledge.

---

## 3. BaseAgent

BaseAgent is **transport infrastructure**. It knows *how* to call GPT — never *what* to say, never *whether* the response is correct.

### What BaseAgent owns

| Responsibility | Detail |
|---|---|
| OpenAI API call | Model, temperature, output_mode, max_tokens, timeout — all passed by the caller |
| Structured Outputs transmission | For `output_mode: "structured"`: passes `contract.model_json_schema()` as `response_format` with `strict: True`. For `output_mode: "json_mode"`: passes `response_format: {"type": "json_object"}`. |
| Transport retry | Exponential backoff on rate limits and transient network errors **only**; max 3 retries |
| Token counting | Input and output tokens extracted from every API response |
| Cost calculation | `input_tokens × input_rate + output_tokens × output_rate` per model |
| AIHistory logging | One row per call: agent_name, model, tokens, cost, duration_ms, status, error_detail |
| Error normalization | Rate limits, network errors, timeouts → typed exceptions the router handles |
| Response extraction | Raw OpenAI response → string; BaseAgent returns the raw string and nothing more |
| Timeout enforcement | Hard cutoff; logs status = "timeout"; raises a typed timeout exception |

### What BaseAgent must NEVER own

- Prompt content of any kind
- Domain knowledge (SEO, writing, clustering, content strategy)
- Output schema definitions, parsing, or validation
- Routing decisions (which agent handles which task)
- Business context (project data, user data, platform state)
- Capability checks (the router knows the user's plan — BaseAgent does not)
- Prompt composition logic
- Validation retries — if the response fails Pydantic parsing, the **router** decides whether to retry

### Transport retry vs. validation retry — the boundary

This distinction is critical and must never be blurred:

| Failure type | Owner | What happens |
|---|---|---|
| Rate limit (HTTP 429) | **BaseAgent** | Exponential backoff, retry transparently, up to 3 attempts |
| Network error / timeout | **BaseAgent** | Retry up to 3 attempts, then raise typed exception |
| Pydantic `ValidationError` | **Router** | BaseAgent never sees this; router parses the raw string and decides |
| Business rule failure | **Router** | Router decides: retry with error context, raise HTTP error, or log |

BaseAgent has no knowledge of Pydantic models, contracts, or expected field names. It cannot participate in validation retry without violating its single responsibility.

**The test:** if this code could be extracted into a standalone OpenAI wrapper library and used for any purpose by any application, it belongs in BaseAgent. If it contains the word "SEO", "keyword", "WordPress", or any domain concept — it does not.

---

## 4. Router

The router is the **orchestrator**. It is the only layer that holds full context: user plan, project data, platform state, and the decision of which agent to call.

### What the router owns

| Responsibility | Detail |
|---|---|
| Agent selection | Decides which agent(s) to call based on page profile, user request, and capability flags |
| Capability checks | Verifies the user's plan allows the requested operation before any AI call |
| Context assembly | Builds the runtime context block from DB, request body, and resolved platform state |
| PromptComposer call | Passes agent name to PromptComposer; shared_docs are looked up from registry — never passed manually |
| BaseAgent call | Passes composed prompt + user message + config (model, temperature, etc.) from registry |
| Pydantic validation | Parses BaseAgent's raw string through the agent's Pydantic contract |
| Business rule assertions | Word count ≥ minimum, required link present, required sections present — after parsing |
| Validation retry decision | If Pydantic parsing fails: retry with error appended to user message, or raise, or log |
| DB write | Writes AIHistory, PageChange, or other records |
| CMS routing | Sends approved changes to WordPress or Shopify |

### What the router must NEVER own

- Domain knowledge — no SEO logic embedded in Python router code
- Prompt content beyond runtime context injection
- OpenAI call mechanics (those belong in BaseAgent)
- Schema definitions (those belong in `contracts/`)
- Hard-coded model names (look up from registry)

---

## 5. Prompt Composition

Every agent call assembles two components: a **system prompt** (stable, eligible for OpenAI caching) and a **user message** (dynamic, never cached).

```
SYSTEM PROMPT:

  ┌──────────────────────────────────────────────────────┐
  │ 0. Platform Identity  [AUTO-LOADED BY PROMPTCOMPOSER]│
  │    "You are an AI agent in SEO OS, a production      │
  │    SaaS platform for SEO management. You work with   │
  │    real client websites. Accuracy is non-negotiable."│
  │                                                      │
  │    ► Agents NEVER register this document.            │
  │    ► PromptComposer prepends it unconditionally.     │
  │    ► It is not in the agent registry shared_docs.    │
  ├──────────────────────────────────────────────────────┤
  │ 1. Agent Identity  (skills/<agent>/identity.md)      │
  │    Role, mission, scope, behavioral constraints      │
  ├──────────────────────────────────────────────────────┤
  │ 2. SKILL.md  (skills/<agent>/SKILL.md)               │
  │    Domain expertise specific to this agent           │
  ├──────────────────────────────────────────────────────┤
  │ 3. Shared Documents  [FROM AGENT REGISTRY]           │
  │    Loaded in the order listed in the registry entry. │
  │    e.g., eeat-framework.md → writing-rules.md        │
  │                                                      │
  │    ► The registry is the authoritative source.       │
  │    ► identity.md may document the same list for      │
  │      human reference, but the registry governs.      │
  ├──────────────────────────────────────────────────────┤
  │ 4. Output Discipline                                 │
  │    (shared/json-output-discipline.md)                │
  │    "Respond with valid JSON only."                   │
  │    NOT loaded for Markdown-output agents.            │
  └──────────────────────────────────────────────────────┘

USER MESSAGE:

  ┌──────────────────────────────────────────────────────┐
  │ 5. Runtime Context                                   │
  │    Business profile, platform state, current content,│
  │    project preferences, change history               │
  ├──────────────────────────────────────────────────────┤
  │ 6. Task                                              │
  │    What to do right now — specific and unambiguous   │
  └──────────────────────────────────────────────────────┘
```

**There is no Output Hint layer.** Output contracts live exclusively in Pydantic models (`contracts/*.py`). The agent does not receive field names or schema descriptions in the prompt. Pydantic is the enforcement mechanism. A field list in a prompt is a schema description in prose, which violates Principle P2 and will drift from the real contract without warning.

### Why this composition scales

- **Adding a new agent** — new `identity.md` + `SKILL.md` + registry entry. PromptComposer, BaseAgent, and all shared docs are untouched.
- **Adding a new platform** (Webflow, Wix) — new runtime context fields in Python. No prompt file changes.
- **Updating writing rules** — edit `skills/shared/writing-rules.md` once. Every agent that registers it receives the change on next call.
- **Changing an output schema** — edit one Pydantic model and update the contract in the registry entry. For Structured Outputs agents, OpenAI enforces the new schema at the API level before the response is returned; Pydantic re-validates as the application-level safety net. The prompt is unaffected.
- **OpenAI prompt caching** — the system prompt (layers 0–4) is stable across calls for the same agent, maximising cache hit rate. Runtime context (layers 5–6) is in the user message and is never cached.

---

## 6. Agent Identity (`identity.md`)

Every agent has an `identity.md` file. This is the **"who am I"** document. It is loaded as layer 1 of the system prompt, after platform-identity.md and before SKILL.md.

### What belongs in identity.md

| Section | Content |
|---|---|
| **Role** | One sentence. "You are the SEO Content Analyzer for SEO OS." |
| **Mission** | The outcome this agent produces — not what it does, but what the subscriber receives. |
| **Scope** | Explicit in-scope responsibilities and explicit non-goals. |
| **Constraints** | Hard behavioral rules that override all other instructions, including task instructions. |
| **Behavioral Notes** | How to reason in ambiguous or incomplete-input scenarios. |
| **Shared Documents** | *Documentation only* — lists the shared docs for human reference. The registry is authoritative. |

### Shared Documents section — authority rule

The `Shared Documents` section in identity.md is **for human readability only**. It must be kept in sync with the agent's registry entry, but if they disagree, **the registry governs**. PromptComposer reads the registry — it does not read identity.md to determine which shared docs to load.

### What must NOT be in identity.md

- JSON schema or output field names
- Anti-AI word lists (`skills/shared/writing-rules.md`)
- E-E-A-T framework text (`skills/shared/eeat-framework.md`)
- Validation checklists
- Any runtime value

**The stability test:** if you printed this file in twelve months, would it still be accurate with no changes? If a change to the output schema, runtime context fields, or shared doc content would make it stale — that content belongs elsewhere.

See `skills/_templates/identity.md` for the standard template.

---

## 7. SKILL.md

SKILL.md is **domain expertise**. It is the "what do I know" document.

It is what makes the SEO Analyzer different from the Article Writer different from the Humanizer. It should read like a domain expert's operating manual — comprehensible to a human SEO professional with zero knowledge of the codebase.

### What belongs in SKILL.md

| Content type | Example |
|---|---|
| SEO theory and methodology | How Google evaluates quality, what signals matter and why |
| Domain heuristics | "Keyword density above 3% signals stuffing; below 0.3% signals thin content" |
| Decision rules that reference runtime signals | "When is_homepage is true, prioritize brand positioning over keyword targeting" |
| Quality thresholds with meaning | What a score of 80+ means vs. 40–60 vs. below 40 |
| Edge case handling | "If the page has no headings, flag it — do not fabricate headings" |
| Agent-specific workflow | The internal reasoning process for this agent's primary task |
| Agent-specific application of shared doc principles | "For this agent, the E-E-A-T Experience signal carries more weight than Authoritativeness for service-industry content" |

### What must NEVER be in SKILL.md

| Forbidden content | Correct location |
|---|---|
| Output field names defined as schema ("return a field called `severity`") | `contracts/*.py` (Pydantic) |
| Output field types ("severity must be a string, one of: low, medium, high, critical") | `contracts/*.py` (Pydantic) |
| Anti-AI word blacklist | `skills/shared/writing-rules.md` |
| E-E-A-T framework text (the doctrine itself) | `skills/shared/eeat-framework.md` |
| Validation checklists ("before responding, verify...") | Python assertions in router |
| Platform-specific conditional logic resolved by Python | Router resolves; agent receives the result |

### The SKILL.md test — two parts

**Part 1 — Output schema references are forbidden:**  
If a line tells the model what to *return* — defines a field name, its type, its allowed values, or its format as part of the output contract — it is in the wrong file. Move it to `contracts/*.py`.

**Part 2 — Runtime field references in heuristics are permitted:**  
If a line tells the model how to *reason given what it received* — references a runtime context field as part of a domain rule — it is legitimate domain knowledge and belongs in SKILL.md. "When `is_homepage` is true, prioritize brand positioning over keyword targeting" is domain expertise. The field name is a reference to a known input, not a schema definition.

**The distinguishing question:** Does this line tell the model *what to return*, or *how to reason about what it received?*  
- "Return a field called `score` as an integer" → wrong file.  
- "When the page score is below 40, treat it as a full rewrite candidate" → SKILL.md.  
- "When `is_homepage` is true, apply the homepage prioritization rules" → SKILL.md.

See `skills/_templates/SKILL.md` for the standard template.

---

## 8. Shared Documents

Shared documents are **canonical, versioned, cross-agent knowledge**. They are assembled into the system prompt by PromptComposer at call time, in the order the registry specifies.

### The special case: platform-identity.md

`skills/shared/platform-identity.md` is the only shared document that is **never registered per-agent**. PromptComposer prepends it unconditionally as layer 0 of every system prompt. It does not appear in any agent's registry `shared_docs` list. It does not appear in identity.md's Shared Documents section.

If `platform-identity.md` appears in a registry entry, it is a bug.

### Document catalog

| File | Purpose | Registerable? | Agents that register it |
|---|---|---|---|
| `platform-identity.md` | Foundation statement: "You operate within SEO OS..." | **No — auto-loaded** | All (automatic) |
| `writing-rules.md` | Anti-AI word blacklist, sentence patterns, voice/tone | Yes | article-writer, editor, humanizer, content-strategy |
| `eeat-framework.md` | Full E-E-A-T doctrine and signals | Yes | article-writer, editor, analyzer, content-strategy |
| `seo-standards.md` | Keyword placement, heading hierarchy, meta standards | Yes | analyzer, editor, meta, article-writer |
| `internal-linking.md` | Hub/spoke model, anchor text, link density | Yes | article-writer, editor |
| `content-safety.md` | YMYL handling, citation requirements, accuracy standards | Yes | article-writer, editor, content-strategy |
| `json-output-discipline.md` | "Respond with valid JSON only." | Yes | All JSON-output agents |

### Authority rule

**The Agent Registry is the single authoritative source for which shared documents an agent loads.** identity.md may document the same list for human readability, but if they conflict, the registry governs. PromptComposer reads the registry — it never inspects identity.md's content.

### Shared document rules

1. **One canonical version.** Never copy content from a shared doc into a SKILL.md. The composer loads the real document.
2. **Documents are independent.** No shared doc references another shared doc.
3. **platform-identity.md is loaded unconditionally.** Agents do not register it.
4. **Order matters.** Earlier documents appear higher in the system prompt. The registry order is preserved.
5. **Adding a new shared document** requires no changes to existing agents. Add it to the relevant agents' registry entries.

---

## 9. Runtime Context

Runtime context is **everything that changes between calls**. It belongs exclusively in the user message — never in any static file.

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

- **Python resolves before the call.** The agent receives `builder: "elementor"` — not "figure out the builder from this HTML."
- **Format is `## field_name\n{value}` consistently across all agents.** One format, always.
- **Absent fields are omitted entirely.** No brand_voice → no `## brand_voice` section. No empty strings.
- **Context is the user message. Expertise is the system prompt.** This boundary is absolute.

---

## 10. Output Contracts (Pydantic)

Output contracts live **exclusively in Pydantic models**. Nowhere else.

### Location: `contracts/*.py`

One file per agent that returns structured output. See `contracts/README.md` for structure and `contracts/meta.py` for a reference implementation.

### Standard path: OpenAI Structured Outputs

**Structured Outputs is the standard for all JSON-output agents.**

The registry entry for every JSON-output agent sets `output_mode: "structured"`. BaseAgent passes the Pydantic model's JSON schema to OpenAI using `response_format={"type": "json_schema", "json_schema": {"strict": True, "schema": contract.model_json_schema()}}`. OpenAI enforces field names, types, and required field presence at the API level before the response is returned. This eliminates structural schema validation failures entirely.

**Why Structured Outputs over json_mode for SEO OS specifically:**  
SEO OS is BYOK (Bring Your Own Key). Every subscriber uses their own OpenAI API key. A json_mode structural failure (wrong field name, missing required field) causes a retry that consumes the subscriber's own tokens and adds latency. Structured Outputs prevents these failures at the API level. The subscriber never pays for a retry caused by a preventable schema error.

### Fallback path: json_mode

`output_mode: "json_mode"` is the fallback for two specific cases only:

1. **The target model predates Structured Outputs support** — some older GPT-4o-mini model snapshots do not support Structured Outputs.
2. **The contract contains types incompatible with strict mode** — recursive schemas, complex unions, or dict fields with non-string values.

When the fallback path is active, PromptComposer generates a **one-line field hint** from the contract's `required` fields and appends it to the system prompt. This is the **only** situation where contract field names appear in a prompt. It is explicitly not the standard approach and must never be normalized as a default.

The fallback hint is derived from the Pydantic model at runtime — it is never written manually into any prompt file.

### Strict mode contract design rules

Pydantic models used with Structured Outputs must be compatible with OpenAI's strict mode. These four rules are mandatory:

1. **Every field must be either required or nullable.** No `Field(default_factory=...)` patterns. No `Field(default=...)` patterns on non-nullable fields. If a field may be absent, use `Type | None = None`. If a field is always present, make it required with no default.
2. **No `dict` fields with non-string values.** Strict mode maps dicts to `additionalProperties`, which does not support mixed-type values.
3. **Constrained strings must use `Literal[...]`.** Enum-like string fields must use `Literal["a", "b", "c"]` — plain `str` passes anything through; Pydantic validates, OpenAI does not.
4. **No recursive schemas.** Strict mode does not support `model_validator` patterns that reference the model itself.

**The required-vs-nullable convention:**  
- A field the model always returns (even when "empty") → required, no default. Example: `change_notes: list[str]` — the model returns `[]` when there are no notes.
- A field the model may legitimately not return → nullable. Example: `redirect_url: str | None = None`.
- An optional list with a default factory → **not allowed**. Change it to a required field and instruct the model to return an empty list when not applicable.

### What each layer contributes to output

| Layer | Contributes |
|---|---|
| `contracts/*.py` | Field names, types, validators, range checks, required vs nullable — **everything structural** |
| OpenAI Structured Outputs | Enforces the contract schema at the API level; structural failures impossible when active |
| `json-output-discipline.md` | "Your response must be valid JSON. No markdown fences." — one behavioral instruction |
| `SKILL.md` | Semantic meaning: what a `severity: "critical"` *means* to the agent — never what its type is |
| `identity.md` | Nothing |
| Prompt (any layer) | Nothing beyond what `json-output-discipline.md` covers — **no field names, no schema descriptions** |
| Fallback hint (generated) | One-line required-field list, generated from Pydantic model at runtime; **only on the fallback path** |

### Why field names must never appear in prompt files

A field name written in a prompt file is a schema description in prose, which violates P2. The moment a field is renamed in Python, the prompt description becomes a lie. Models learn from that lie. Pydantic raises `ValidationError` instantly on the wrong field name. Prose never does. With Structured Outputs, field names are transmitted at the API level — they never need to appear in any prompt file at all.

---

## 11. Validation and Retry

Validation is **entirely Python's responsibility**. Retry responsibility is split between BaseAgent (transport failures) and the Router (application-level failures). These must never be confused.

### BaseAgent retry — transport failures only

BaseAgent retries automatically and transparently for:

| Condition | Action |
|---|---|
| HTTP 429 (rate limit) | Wait `retry-after` header value, then retry. Max 3 attempts. |
| Network error / connection reset | Exponential backoff, retry. Max 3 attempts. |
| HTTP 5xx from OpenAI | Exponential backoff, retry. Max 3 attempts. |
| Timeout | Log `status = "timeout"`, raise typed `AgentTimeoutError`. No retry. |

BaseAgent does **not** look at the content of the response. It returns the raw string unconditionally. It has no knowledge of whether the response is valid JSON, matches a Pydantic schema, or satisfies any business rule.

### Router validation and retry — application failures

After BaseAgent returns the raw string, the router owns all validation:

| Stage | Layer | Checks |
|---|---|---|
| 1. Structural | `json.loads()` | Valid JSON syntax |
| 2. Schema | `Pydantic.model_validate_json()` | Field presence, correct types, format |
| 3. Range | Pydantic validators | Scores 0–100, non-empty required strings, valid URLs |
| 4. Business rules | Python assertions | Word count ≥ minimum, required link present, required sections present |
| 5. Content checks | Python parsers | HTML validity, internal link count |

**When validation fails, the router decides:**
- Retry: call BaseAgent again with the validation error appended to the user message
- Raise: return HTTP 422/500 to the caller with a structured error
- Log and continue: for non-critical failures where partial output is acceptable

The router's retry decision is made in Python code, not registered in the agent configuration. There is no `retry_on_validation_error` registry field — retry policy is orchestration logic, not agent configuration.

### The one acceptable prompt instruction about validation

> "Your response must be valid JSON."

This is a behavioral instruction from `json-output-discipline.md`. It tells the model what form to use. Python handles whether the content is correct.

**Self-audit checklists ("before responding, verify that…") must not appear in any agent prompt.** Remove them; replace with Python assertions.

---

## 12. Agent Registry

The registry is the **single source of truth for every agent's configuration**. No router may hard-code a model name, timeout, or shared document list.

See `agents/REGISTRY_SPEC.md` for the complete field specification.

### Authority rules

- **The registry owns `shared_docs`.** identity.md may document the same list; the registry governs if they differ.
- **`platform-identity.md` is never listed in shared_docs.** It loads unconditionally. Any entry that includes it is a bug.
- **The registry owns the model assignment.** The model selection rule (gpt-4o for writing, gpt-4o-mini for analysis) is enforced here. Routers look up the agent name; they never specify a model directly.
- **The registry owns `output_mode`.** If an agent has a Pydantic contract and can use Structured Outputs, `output_mode` is `"structured"`. If the agent requires the json_mode fallback, `output_mode` is `"json_mode"`. Markdown agents set it `"markdown"`. The router reads this from the registry — it never hard-codes a mode.

### What every agent registers

| Field | Type | Purpose |
|---|---|---|
| `name` | string | Unique identifier; matches `skills/<name>/` folder |
| `model` | string | `gpt-4o` or `gpt-4o-mini` — enforced by selection rule |
| `temperature` | float | 0.0–1.0 |
| `timeout` | int | Seconds; BaseAgent enforces this hard cutoff |
| `max_tokens` | int | Upper bound on output length |
| `output_mode` | `"structured"` \| `"json_mode"` \| `"markdown"` | `"structured"` for Pydantic + Structured Outputs (standard); `"json_mode"` for fallback path only; `"markdown"` for non-JSON agents |
| `shared_docs` | list[str] | Ordered list of shared doc names (no `.md` extension); **does not include `platform-identity`** |
| `contract` | class | Pydantic model class from `contracts/`; `null` for Markdown agents |
| `capabilities` | list[str] | Required user capability flags checked by router before calling |
| `description` | string | One-sentence description for AGENTS.md and logging |

### Model selection rule

| Task type | Model |
|---|---|
| Writing, editing, rewriting, long-form generation | `gpt-4o` |
| Analysis, classification, clustering, meta generation, scoring | `gpt-4o-mini` |

**Temperature constraint for structured-output agents:** Maximum temperature is 0.7 for any agent with `output_mode: "structured"` or `"json_mode"`. Higher temperatures increase the rate of structural failures in long outputs. For `output_mode: "structured"` this is belt-and-suspenders — Structured Outputs prevents structural failures — but consistent discipline across modes avoids surprises when the fallback path is active. The article writer currently uses 0.75 — cap it at 0.7 when the registry is implemented.

---

## 13. Folder Structure

```
seo-os/
│
├── ARCHITECTURE.md              ← This document. The single source of truth.
│
├── agents/
│   ├── base.py                  ← BaseAgent: call, transport retry, logging, cost
│   ├── composer.py              ← PromptComposer: assembles system prompt from parts
│   │                               Always prepends platform-identity.md as layer 0.
│   │                               Reads shared_docs from registry, not identity.md.
│   ├── registry.py              ← Maps agent name → full configuration
│   └── REGISTRY_SPEC.md         ← Human-readable specification for the registry schema
│
├── skills/
│   │
│   ├── _templates/
│   │   ├── identity.md          ← Standard template for all new agent identity files
│   │   └── SKILL.md             ← Standard template for all new agent SKILL files
│   │
│   ├── shared/
│   │   ├── platform-identity.md ← Auto-loaded by PromptComposer. Never registered.
│   │   ├── writing-rules.md     ← Anti-AI words, sentence patterns, voice/tone
│   │   ├── eeat-framework.md    ← E-E-A-T doctrine and signals
│   │   ├── seo-standards.md     ← Keyword placement, headings, meta standards
│   │   ├── internal-linking.md  ← Hub/spoke model, anchor text, link density
│   │   ├── content-safety.md    ← YMYL, citations, accuracy standards
│   │   └── json-output-discipline.md  ← "Respond with valid JSON only."
│   │
│   ├── seo-analyzer/
│   │   ├── identity.md
│   │   └── SKILL.md
│   │
│   └── [one folder per agent — always identity.md + SKILL.md, nothing else]
│
├── contracts/
│   ├── README.md                ← How to write a contract; structure guide
│   ├── __init__.py              ← Package init; imports for convenience
│   ├── meta.py                  ← MetaResponse — reference implementation
│   ├── analyzer.py              ← AnalyzerResponse
│   ├── editor.py                ← EditorResponse
│   ├── article.py               ← ArticlePhase1/2/3Response
│   ├── cluster.py               ← ClusterResponse
│   ├── schema.py                ← SchemaResponse
│   ├── humanizer.py             ← HumanizerResponse
│   └── [one file per agent that returns structured output]
│
├── prompts/
│   └── context_builder.py       ← Python functions that assemble runtime context:
│                                   build_business_block(), build_platform_block(),
│                                   build_content_block(), build_preferences_block()
│
└── api/
    └── routers/                 ← Orchestration only; no domain knowledge
```

---

## 14. Responsibility Matrix

| Layer | Owns | Never Owns |
|---|---|---|
| **BaseAgent** | OpenAI call, transport retry (rate limits / network), token counting, cost tracking, AIHistory logging, error normalization, Structured Outputs schema transmission (`response_format` assembly from contract) | Prompt content, domain knowledge, schema definition, routing, capability checks, validation retry |
| **Router** | Agent selection, capability checks, context assembly, PromptComposer call, BaseAgent call, Pydantic validation, validation retry decision, business rule assertions, DB writes, CMS routing | AI call mechanics, domain knowledge, prompt content, schema definitions, model names |
| **PromptComposer** | Prepending platform-identity.md unconditionally; loading shared docs from registry in registry order; assembling system prompt layers in correct sequence | Deciding which docs to load beyond what the registry specifies; any domain content; platform-identity.md routing (always first, always loaded) |
| **Agent Registry** | Agent name → model, temperature, timeout, max_tokens, output_mode, shared_docs, contract, capabilities, description | AI call execution, domain knowledge, prompt content, validation retry policy |
| **Agent Identity** (`identity.md`) | Agent role, mission, scope, behavioral constraints; Shared Documents section as documentation-only human reference | JSON schema, output field names, writing rules, E-E-A-T text, validation checklists |
| **SKILL.md** | Domain expertise, decision heuristics (including runtime field references), quality thresholds, edge case handling, agent-specific application of shared doc principles | Output field definitions, field types, anti-AI word lists, E-E-A-T doctrine text, validation checklists |
| **Shared Documents** | Canonical cross-agent knowledge (writing, SEO, E-E-A-T, linking, safety); platform-identity.md as universal foundation | Agent-specific logic, runtime values, JSON schema, content for one agent only |
| **Runtime Context** | Per-call state: business profile, platform resolution, current content, preferences, task specification | Stable knowledge, domain expertise, schema, any content that doesn't change per call |
| **Pydantic Models** (`contracts/`) | Output field names, types, range validators, required vs optional, parse-time enforcement | Domain knowledge, prompt assembly, business logic beyond schema |

---

## 15. Adding a New Agent

Follow this checklist every time a new agent is introduced. Complete every step in order.

**Before writing any prompts:**
- [ ] Define the agent's single responsibility in one sentence
- [ ] Confirm no overlap with an existing agent's scope
- [ ] Identify which existing shared documents it needs
- [ ] Identify whether new shared documents must be created first

**Prompt files (`skills/<agent-name>/`):**
- [ ] `identity.md` — from `skills/_templates/identity.md`
- [ ] `SKILL.md` — from `skills/_templates/SKILL.md`
- [ ] Verify: no JSON field names defined as schema in either file
- [ ] Verify: no anti-AI word list in either file
- [ ] Verify: no validation checklist in either file
- [ ] Verify: `platform-identity.md` is NOT listed in the identity.md Shared Documents section

**Contract (`contracts/`):**
- [ ] Create `contracts/<agent-name>.py` using `contracts/meta.py` as reference
- [ ] Define all fields with types, validators, and range checks
- [ ] Confirm every field SKILL.md semantically references exists in the model

**Registry (`agents/registry.py`):**
- [ ] Add entry: name, model, temperature, timeout, max_tokens, output_mode, shared_docs, contract, capabilities, description
- [ ] Confirm model follows the gpt-4o / gpt-4o-mini selection rule
- [ ] Set `output_mode: "structured"` for Pydantic contract agents (standard); use `"json_mode"` only if the model or contract is incompatible with Structured Outputs (document why)
- [ ] Confirm `output_mode: "structured"` or `"json_mode"` agents have temperature ≤ 0.7
- [ ] Confirm `platform-identity` is NOT in shared_docs
- [ ] Confirm contract fields satisfy strict mode: all fields are either required or nullable (`Type | None = None`); no `Field(default_factory=...)` on non-nullable fields
- [ ] Update identity.md Shared Documents section to match registry entry

**Router:**
- [ ] Call PromptComposer with agent name only (shared_docs come from registry)
- [ ] Call BaseAgent; receive raw string
- [ ] Parse via `ContractClass.model_validate_json(raw)`
- [ ] Add Python assertions for business rules
- [ ] Log to AIHistory

**Documentation:**
- [ ] Update `AGENTS.md` agent registry table

**Tests:**
- [ ] One test for Pydantic contract parsing (valid input)
- [ ] One test for Pydantic contract rejection (invalid input)
- [ ] One test for Python business rule assertions

---

## 16. Migrating an Existing Agent

Migrating an existing production agent into the target architecture is different from creating a new one. An existing SKILL.md contains mixed content that must be sorted, relocated, or removed without breaking the agent's output quality.

### Step 1 — Audit the existing SKILL.md

Read the file in full. Classify every paragraph or section using this table:

| Content type | Classification | Action |
|---|---|---|
| SEO theory, methodology, principles | Domain expertise | **Keep in SKILL.md** |
| Decision heuristics, rules referencing runtime signals | Domain expertise | **Keep in SKILL.md** |
| Quality thresholds and their meaning | Domain expertise | **Keep in SKILL.md** |
| Edge case handling | Domain expertise | **Keep in SKILL.md** |
| Identity / role / mission text | Identity | **Move to identity.md** |
| Output field names or types defined as schema | Contract | **Move to `contracts/*.py`** |
| Anti-AI word list | Shared doc | **Mark — migrates to writing-rules.md** |
| E-E-A-T framework text | Shared doc | **Mark — migrates to eeat-framework.md** |
| Input field documentation (`## is_homepage\n...`) | Runtime context | **Remove** — runtime context provides this |
| Validation checklist ("before responding, verify...") | Prompt theatre | **Remove** — replace with Python assertions |
| Platform conditional logic ("if Elementor, then...") | Python | **Remove** — router resolves this before the call |
| JSON-only output instruction | Shared doc | **Remove** — `json-output-discipline.md` handles this |

**Do not proceed to Step 2 until every line is classified.**

### Step 2 — Create `identity.md`

1. Open `skills/_templates/identity.md`
2. Copy the identity/role/mission content extracted in Step 1
3. Add the constraint list — at minimum the three universal constraints in the template, plus agent-specific ones
4. Fill the Behavioral Notes section with ambiguous-input guidance
5. Set the Shared Documents section to match what the agent currently receives (this is documentation only — the registry governs)
6. Do not add the platform-identity.md row to Shared Documents

### Step 3 — Rewrite `SKILL.md`

1. Remove all content classified as non-domain in Step 1
2. Verify what remains passes the two-part test in Section 7
3. Reorganize using the template sections: Domain Expertise → Decision Framework → Quality Standards → Edge Cases → What This Agent Must Not Do
4. Do not reference the shared docs you removed — the composer loads them automatically

### Step 4 — Create the Pydantic contract

1. Open `contracts/meta.py` as a reference
2. Create `contracts/<agent-name>.py`
3. Reconstruct the full output schema from: the old SKILL.md schema section, the router's current `json.loads()` usage, and the frontend's consumption of the response fields
4. Add field-level validators for every range or format constraint that currently exists as a prompt instruction
5. Replace every `json.loads(raw)` in the router with `AgentNameResponse.model_validate_json(raw)`

### Step 5 — Update the registry

1. Add or update the agent's entry in `agents/registry.py` (or AGENTS.md until registry.py is built)
2. Set `shared_docs` to the list the agent actually needs — include docs that cover content removed from SKILL.md
3. Update the Shared Documents section in identity.md to match

### Step 6 — Add Python assertions

For every validation rule that lived in the SKILL.md checklist and is not covered by Pydantic field validation, add a Python assertion in the router after `model_validate_json()`.

### Step 7 — Verify

- [ ] Run the agent against a test input; confirm output quality is maintained
- [ ] Confirm the Pydantic contract catches a deliberately malformed response
- [ ] Confirm word count / business rule assertions fire on bad output
- [ ] Confirm `platform-identity` is not in the registry entry
- [ ] Confirm no output field names remain in SKILL.md
- [ ] Confirm no validation checklist remains in SKILL.md
- [ ] Confirm the identity.md Shared Documents section matches the registry entry

### Migration order recommendation

Migrate agents from least complex to most complex. Start with agents that have the smallest SKILL.md and simplest JSON output. Suggested order:

1. `feedback-distiller` — smallest output contract, no shared docs needed
2. `seo-meta` — simple schema (title + description), well-isolated job
3. `seo-cluster` — well-defined JSON output, no content writing
4. `seo-schema` — compact scope
5. `seo-analyzer` — larger schema but clear structure
6. `seo-editor` — complex but well-understood
7. `seo-article-writer` — most complex; three-phase pipeline; migrate last

---

*This document supersedes the earlier `docs/ARCHITECTURE.md` for all AI agent decisions.*  
*The `docs/ARCHITECTURE.md` remains as historical reference for the Python clean-architecture layers.*
