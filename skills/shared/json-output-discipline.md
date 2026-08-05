# JSON Output Discipline

**Layer:** Shared Document  
**Loaded by:** All agents that return structured JSON output  
**Purpose:** A single, canonical instruction for JSON output format. This document exists because "respond with JSON" appears in five SKILL.md files today, creating maintenance debt. Every agent that returns structured output loads this document and inherits this instruction. It is not loaded by agents that return Markdown (seo-plan, content-strategy, site-architecture, seo-flow, seo-page).

> **Maintenance rule:** This is intentionally a short document. Do NOT expand it with schema details — those belong in `contracts/*.py`. Do NOT add validation checklists — those belong in Python.

---

## The Rule

Your response must be a single valid JSON object.

- Do not include markdown code fences (no ` ```json ``` `).
- Do not include any explanatory text before or after the JSON object.
- Do not include comments inside the JSON.
- Do not use trailing commas.
- String values must not contain unescaped newlines — use `\n` if line breaks are needed within a string.
- If a field is not applicable, return `null` for nullable fields or omit the field entirely if the schema marks it optional.
- Do not invent fields that are not in the output contract. Include only the fields specified.

## What This Document Does NOT Cover

- **Field names and types** — those are defined in `contracts/*.py`
- **Required vs. optional fields** — defined in `contracts/*.py`
- **Range validation** — enforced by Python after parsing, not by this document
- **Self-audit checklists** — not valid here; Pydantic enforces schema, Python enforces business rules

## Why This Document Exists

The instruction "Do NOT return markdown or code blocks. Your response MUST be valid JSON parseable directly." appeared as an exact duplicate in five SKILL.md files. Each file was independently edited over time and had begun to diverge. This document replaces all five copies. Any future agent that returns structured output loads this document; no agent-specific copy of this instruction is ever needed.
