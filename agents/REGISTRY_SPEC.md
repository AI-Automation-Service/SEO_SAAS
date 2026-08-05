# Agent Registry Specification

**Purpose:** This document defines the schema that every agent must register. The registry (`agents/registry.py`, to be implemented) is the single source of truth for agent configuration. No router should hard-code a model name, timeout, or shared document list.

**Status:** Specification only. Implementation in `agents/registry.py` is a future step.

---

## Why a Registry Exists

Without a registry:
- Model selection is scattered across router files
- Shared document lists are duplicated or forgotten
- Timeouts are guessed per-router
- Adding a new agent requires editing multiple files
- Changing a model requires finding every place it's referenced

With a registry:
- One entry per agent defines everything
- Routers look up configuration by agent name
- Adding an agent = adding one registry entry
- Model assignment follows enforced rules, not per-developer judgment

---

## Registry Entry Schema

Each agent registers a single entry with the following fields.

### Required Fields

#### `name` — string

The unique identifier for the agent. Must match the folder name in `skills/<name>/`.

```
name: "seo-analyzer"
```

Rules:
- Lowercase, hyphen-separated
- Must exactly match the `skills/<name>/` folder
- Must be unique across all agents
- Used as the key in `SkillAgent(name, ...)` calls

---

#### `model` — string

The OpenAI model to use for this agent.

```
model: "gpt-4o-mini"
```

**Model selection rule (enforced — not a suggestion):**

| Task type | Model |
|---|---|
| Writing, editing, rewriting, long-form generation | `gpt-4o` |
| Analysis, classification, clustering, scoring, meta generation | `gpt-4o-mini` |

No router may override this with a hard-coded model name. All model selection goes through the registry.

---

#### `temperature` — float (0.0 to 1.0)

Controls output randomness.

```
temperature: 0.3
```

**Guidance by task type:**

| Task | Temperature range |
|---|---|
| Structured JSON output (analyzer, meta, cluster) | 0.2 – 0.4 |
| Content editing (editor) | 0.5 – 0.6 |
| Long-form creative writing (article writer) | 0.7 – 0.8 |
| Humanization / rewriting | 0.7 – 0.8 |
| Strategy and planning (plan, content-strategy) | 0.6 – 0.7 |

---

#### `timeout` — integer (seconds)

Hard cutoff for the API call. BaseAgent enforces this and logs `status = "timeout"` to AIHistory.

```
timeout: 60
```

**Guidance by expected output size:**

| Output type | Timeout |
|---|---|
| Short structured JSON (meta, cluster, analyzer) | 30 – 60s |
| Medium structured JSON (editor) | 60 – 120s |
| Long-form content (article phases) | 120 – 180s |
| Multi-section strategy documents | 120 – 240s |

---

#### `max_tokens` — integer

Upper bound on output token count. Prevents runaway generation and controls cost.

```
max_tokens: 2000
```

**Guidance:**

| Output type | max_tokens |
|---|---|
| JSON-only responses (meta, cluster, analyzer) | 800 – 1500 |
| Content editing with full HTML | 3000 – 4000 |
| Article writing phases | 2000 – 3000 per phase |
| Strategy/planning Markdown | 3000 – 5000 |

---

#### `shared_docs` — list of strings

The ordered list of shared document filenames (from `skills/shared/`) to load into the system prompt. The PromptComposer appends them in this order after the agent's SKILL.md.

```
shared_docs:
  - "eeat-framework"
  - "seo-standards"
  - "json-output-discipline"
```

Rules:
- File extension is omitted (`.md` is implied)
- Order matters — earlier docs appear higher in the system prompt
- `json-output-discipline` must be last for all JSON-returning agents
- `writing-rules` must be included for all content-producing agents (article writer, editor, humanizer)
- No agent should load shared docs it does not need — unnecessary context wastes tokens

**Reference: which agents load which shared docs**

| Agent | writing-rules | eeat-framework | seo-standards | internal-linking | content-safety | json-output |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| seo-analyzer | | ✓ | ✓ | | | ✓ |
| seo-editor | ✓ | ✓ | ✓ | ✓ | | ✓ |
| seo-meta | | | ✓ | | | ✓ |
| seo-article-writer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| humanizer | ✓ | | | | | ✓ |
| seo-cluster | | | | | | ✓ |
| content-strategy | ✓ | ✓ | ✓ | ✓ | ✓ | |
| seo-plan | | | ✓ | ✓ | | |
| feedback-distiller | | | | | | ✓ |
| seo-schema | | | ✓ | | | ✓ |

---

#### `contract` — class reference

The Pydantic model class used to parse and validate the agent's response. Must be importable from `contracts/`.

```
contract: "AnalyzerResponse"  # from contracts/analyzer.py
```

Rules:
- One Pydantic model per agent response type
- Agents that return Markdown (not JSON) set this to `null`
- The router imports and uses this class for `model_validate_json()` — never bare `json.loads()`

---

#### `capabilities` — list of strings

The user capability flags that must be present for this agent to be callable. Checked by the router before the call.

```
capabilities:
  - "AI_WRITER"
```

Available capability flags (from `_ALL_CAPABILITIES` in `models.py`):

| Flag | Meaning |
|---|---|
| `AI_WRITER` | User has OpenAI key configured and AI generation is enabled |
| `GSC` | Google Search Console is connected |
| `GA4` | Google Analytics 4 is connected |
| `CRON` | Scheduled jobs are enabled |
| `PLAGIARISM_CHECK` | Copyscape integration is active |
| `AUTOPILOT` | Autopilot mode is enabled |
| `FEEDBACK_LOOP` | Feedback distillation is enabled |
| `SHOPIFY` | Shopify integration is active |

All agents that make OpenAI calls require `AI_WRITER`. Additional capabilities are added as needed.

---

#### `description` — string

One-sentence human-readable description of what this agent produces. Used in AGENTS.md, logging, and admin UI.

```
description: "Analyzes page content against 9 SEO signals and outputs a structured improvement plan."
```

---

### Optional Fields

#### `json_mode` — boolean (default: true for JSON agents, false for Markdown agents)

Whether to pass `response_format={"type": "json_object"}` to the OpenAI call.

```
json_mode: true
```

Must be `true` for all agents with a Pydantic contract. Must be `false` for Markdown-output agents.

---

#### `retry_on_validation_error` — boolean (default: false)

Whether BaseAgent should automatically retry the call if the Pydantic contract fails to parse the response. When `true`, the validation error message is appended to the next attempt's user message.

```
retry_on_validation_error: false
```

Use sparingly. Most validation errors indicate a prompt problem, not a transient failure.

---

## Full Example Entry

This is what a complete registry entry looks like for the seo-analyzer agent:

```
Agent: seo-analyzer
  name:             "seo-analyzer"
  model:            "gpt-4o-mini"
  temperature:      0.3
  timeout:          60
  max_tokens:       1200
  json_mode:        true
  shared_docs:
    - "eeat-framework"
    - "seo-standards"
    - "json-output-discipline"
  contract:         AnalyzerResponse        # from contracts/analyzer.py
  capabilities:
    - "AI_WRITER"
  retry_on_validation_error: false
  description:      "Analyzes page content against 9 SEO signals and outputs a structured improvement plan."
```

---

## Current Agent Registry (Pre-implementation reference)

This table reflects the current state of agents before the registry is implemented. Use this as the starting point for `agents/registry.py`.

| Agent | Model | Temp | Timeout | max_tokens | JSON | Contract (to create) |
|---|---|---|---|---|---|---|
| seo-analyzer | gpt-4o-mini | 0.3 | 60 | 1200 | ✓ | AnalyzerResponse |
| seo-editor | gpt-4o | 0.55 | 120 | 4000 | ✓ | EditorResponse |
| seo-meta | gpt-4o-mini | 0.3 | 45 | 600 | ✓ | MetaResponse |
| seo-cluster | gpt-4o-mini | 0.3 | 60 | 2000 | ✓ | ClusterResponse |
| seo-article-writer (p1) | gpt-4o | 0.75 | 180 | 2500 | ✓ | ArticlePhase1Response |
| seo-article-writer (p2) | gpt-4o | 0.75 | 180 | 2500 | ✓ | ArticlePhase2Response |
| seo-article-writer (p3) | gpt-4o | 0.75 | 180 | 2500 | ✓ | ArticlePhase3Response |
| humanizer | gpt-4o-mini | 0.75 | 60 | 3000 | ✓ | HumanizerResponse |
| seo-schema | gpt-4o-mini | 0.3 | 60 | 1000 | ✓ | SchemaResponse |
| feedback-distiller | gpt-4o-mini | 0.3 | 45 | 500 | ✓ | PreferencesResponse |
| seo-plan | gpt-4o | 0.65 | 180 | 4000 | ✗ | None (Markdown) |
| content-strategy | gpt-4o | 0.65 | 180 | 4000 | ✗ | None (Markdown) |
| site-architecture | gpt-4o | 0.65 | 180 | 4000 | ✗ | None (Markdown) |
| seo-flow | gpt-4o | 0.65 | 180 | 4000 | ✗ | None (Markdown) |
| seo-page | gpt-4o | 0.65 | 180 | 4000 | ✗ | None (Markdown) |

---

## Implementation Notes (for when registry.py is built)

1. The registry should be a Python dict or dataclass-based structure, not a YAML file — type checking applies at import time.
2. `SkillAgent` calls should look up configuration from the registry by name, not accept hard-coded model strings.
3. The registry must be the only place a model name appears. Routers import the agent name; the registry resolves the model.
4. Validation: on startup, the registry should verify that every registered agent has a corresponding `skills/<name>/` folder and a valid Pydantic contract class.
