# Output Contracts

**Layer:** Pydantic models — the single source of truth for every agent's output schema.  
**Location:** `contracts/<agent-name>.py`  
**Authority:** These models are the authoritative schema. SKILL.md prose, identity.md, and prompt text are all subordinate. If any prompt description of an output field contradicts a Pydantic model, the Pydantic model wins — and the prompt description must be updated or removed.

---

## Purpose

Every AI agent in SEO OS that returns structured output (JSON) has exactly one Pydantic model that defines what that output must look like. The contract is enforced at parse time in the router:

```python
# In the router — never bare json.loads()
response = AgentNameResponse.model_validate_json(raw_string)
```

A `ValidationError` raised here means the agent returned non-conforming output. The router decides whether to retry with the error appended to the user message, or raise an HTTP error.

---

## What belongs in a contract

- **All field names** — exactly as the agent is instructed to return them
- **All field types** — `str`, `int`, `float`, `bool`, `list`, nested models
- **Required vs optional** — required fields have no default; optional fields use `Optional[T] = None`
- **Range validators** — scores in 0–100, lengths within bounds, enums for constrained strings
- **Non-empty validators** — required strings must not be empty after stripping
- **Field descriptions** — `Field(description="...")` for human documentation of what each field means

## What does NOT belong in a contract

- Domain knowledge — a validator should check "is this a valid score?" not "is this a good score?"
- Business logic — that goes in router assertions after parsing
- Prompt content — contracts are pure Python; they never become part of the system prompt

---

## Standard File Structure

```python
# contracts/<agent-name>.py
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator


class AgentNameResponse(BaseModel):
    """
    Output contract for the <agent-name> agent.
    
    Usage in router:
        raw = BaseAgent(...).run(...)
        response = AgentNameResponse.model_validate_json(raw)
    """

    # --- Required fields ---
    field_name: FieldType = Field(description="What this field contains")

    # --- Optional fields ---
    optional_field: str | None = Field(default=None, description="...")

    # --- Validators ---
    @field_validator("field_name")
    @classmethod
    def field_name_must_be_valid(cls, v: FieldType) -> FieldType:
        # Check constraints. Raise ValueError with a clear message if invalid.
        return v
```

See `contracts/meta.py` for a complete reference implementation.

---

## Naming Convention

| Agent | Contract class | File |
|---|---|---|
| seo-analyzer | `AnalyzerResponse` | `contracts/analyzer.py` |
| seo-editor | `EditorResponse` | `contracts/editor.py` |
| seo-meta | `MetaResponse` | `contracts/meta.py` |
| seo-article-writer (p1) | `ArticlePhase1Response` | `contracts/article.py` |
| seo-article-writer (p2) | `ArticlePhase2Response` | `contracts/article.py` |
| seo-article-writer (p3) | `ArticlePhase3Response` | `contracts/article.py` |
| seo-cluster | `ClusterResponse` | `contracts/cluster.py` |
| seo-schema | `SchemaResponse` | `contracts/schema.py` |
| humanizer | `HumanizerResponse` | `contracts/humanizer.py` |
| feedback-distiller | `PreferencesResponse` | `contracts/feedback_distiller.py` |

Pattern: `<AgentName>Response`, PascalCase, always ends in `Response`.

---

## Migrating from `json.loads()`

When migrating an existing router from `json.loads()` to Pydantic:

1. Find every `json.loads(raw_*)` call in the router
2. Reconstruct the expected schema from the SKILL.md (before migration removes it), the router's field accesses (`.get("field_name")`), and the frontend's consumption
3. Write the Pydantic model with all fields, types, and validators
4. Replace `json.loads(raw)` with `ContractClass.model_validate_json(raw)`
5. Replace `result.get("field")` with `result.field` — Pydantic models use attribute access
6. Add `ValidationError` handling in the router for the retry/error decision

---

## Adding a New Contract

1. Create `contracts/<agent-name>.py` using the structure above
2. Add the import to `contracts/__init__.py`
3. Import and use in the router
4. Do NOT add field descriptions or schema documentation to SKILL.md

---

## Pydantic Version Note

All contracts use **Pydantic v2** (`pydantic>=2.0`). Use `model_validate_json()`, not `parse_raw()`. Use `@field_validator` with `@classmethod`, not `@validator`.
