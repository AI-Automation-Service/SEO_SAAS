# [AGENT NAME] — Domain Expertise

<!--
  TEMPLATE INSTRUCTIONS (delete this block before committing)
  -----------------------------------------------------------
  This file defines WHAT this agent knows. It is pure domain expertise.
  It is loaded after identity.md and before shared documents in the system prompt.

  The test: this file should be comprehensible to a human SEO professional
  with zero knowledge of the codebase. If a line references a JSON field name,
  a Python variable, a database column, or a runtime value — it is in the wrong file.

  Rules:
  - NO JSON field names or output schema
  - NO anti-AI word lists → those go in skills/shared/writing-rules.md
  - NO E-E-A-T framework text → that goes in skills/shared/eeat-framework.md
  - NO validation checklists
  - NO platform field documentation (is_homepage, builder, etc.)
  - NO values that change between calls

  Fill every section. Remove comment blocks before committing.
-->

---

## Domain Expertise

<!--
  What is this agent an expert in? The foundational knowledge it applies to every task.
  This is the "what I know" section — not process, but knowledge.

  Write as a domain expert explaining their field.
  3–6 paragraphs or structured bullet groups.
-->

### Core Knowledge

[What does this agent understand at a deep level? What principles, theories, and frameworks guide its decisions?]

### Key Concepts

<!--
  2–5 concepts the agent must understand to do its job.
  Define each concept precisely, especially if it has a specific meaning in SEO
  that differs from general usage.
-->

| Concept | Definition as used by this agent |
|---|---|
| [Concept 1] | [Precise definition] |
| [Concept 2] | [Precise definition] |

---

## Decision Framework

<!--
  The agent's step-by-step reasoning process for its primary task.
  This is the procedural knowledge — how to think about the problem, in order.

  Be specific. Ambiguous instructions produce ambiguous output.
-->

### Standard Path

When given a typical, complete input:

1. [First, do this — what to assess/examine/consider]
2. [Then, do this]
3. [Then, apply this rule or make this decision]
4. [Finally, produce output based on steps 1–3]

### When Inputs Are Ambiguous or Incomplete

<!--
  What should the agent do when it doesn't have everything it needs?
  Each scenario should have a clear resolution.
-->

| Scenario | How to handle |
|---|---|
| Required data is missing | [Specific resolution] |
| Content quality is too low to improve | [Specific resolution] |
| Conflicting signals | [Which takes priority] |

---

## Quality Standards

<!--
  What constitutes good output from this agent?
  Define both the target (what to aim for) and the floor (what is unacceptable).
-->

### High-Quality Output

- [Criterion 1: what makes this agent's output excellent?]
- [Criterion 2]
- [Criterion 3]

### Unacceptable Output

<!--
  Hard failures — specific outputs that must never be produced.
  These are things a subscriber would correctly identify as wrong.
-->

- [Failure 1: what would be a clear mistake?]
- [Failure 2]
- [Failure 3]

### Thresholds and Benchmarks

<!--
  Specific numbers or ranges that define quality levels.
  Examples: score ranges, word count minimums, keyword density thresholds.
-->

| Metric | Below threshold | Acceptable | Excellent |
|---|---|---|---|
| [Metric 1] | [Range] | [Range] | [Range] |

---

## Edge Cases

<!--
  Specific scenarios that require non-standard handling.
  Document each one explicitly so the agent doesn't have to reason from first principles
  in situations the general framework doesn't cover cleanly.
-->

| Scenario | How this agent handles it |
|---|---|
| [Edge case 1] | [Specific resolution] |
| [Edge case 2] | [Specific resolution] |
| [Edge case 3] | [Specific resolution] |

---

## What This Agent Must Not Do

<!--
  Hard prohibitions specific to this agent's domain.
  These override all other instructions in this file.

  Different from constraints in identity.md:
  - identity.md constraints are behavioral (don't fabricate, don't exceed scope)
  - These prohibitions are domain-specific (never remove schema markup, never shorten titles below N chars)
-->

1. [Domain-specific prohibition 1]
2. [Domain-specific prohibition 2]
3. [Domain-specific prohibition 3]

---

<!--
  REMINDERS BEFORE COMMITTING (delete this block):
  ✓ No JSON field names anywhere in this file
  ✓ No anti-AI word list (use skills/shared/writing-rules.md)
  ✓ No E-E-A-T framework text (use skills/shared/eeat-framework.md)
  ✓ No validation checklist
  ✓ No platform field documentation
  ✓ File reads like a domain expert's operating manual, not a software spec
-->
