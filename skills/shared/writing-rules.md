# Writing Rules

**Layer:** Shared Document  
**Loaded by:** seo-article-writer, seo-editor, humanizer, content-strategy  
**Purpose:** The canonical, single source of truth for all writing standards applied by AI agents in SEO OS. Every rule about voice, tone, sentence construction, and forbidden language lives here — nowhere else.

> **Maintenance rule:** If you need to add or modify a writing standard, edit this file. Do NOT update individual SKILL.md files with writing rules. Changes here propagate automatically to all agents that load this document.

---

## What belongs in this document

- The complete anti-AI word and phrase blacklist
- Sentence-level construction patterns to avoid
- Active vs. passive voice rules
- Paragraph length and structure standards
- Punctuation and formatting norms for web content
- Tone and register guidelines (professional but human)
- Transition phrase standards
- Forbidden structural patterns (e.g., "In conclusion", "In summary")
- Rules for numbered lists vs. prose

## What does NOT belong here

- SEO-specific rules (keyword placement, heading hierarchy) → `seo-standards.md`
- E-E-A-T principles → `eeat-framework.md`
- JSON output format → `json-output-discipline.md`
- Agent-specific workflow or decision logic → `SKILL.md`

---

## Anti-AI Word Blacklist

> **[CONTENT TO BE MIGRATED HERE]**  
> Source 1: `api/routers/content/article.py` — `_GLOBAL_RULES` constant  
> Source 2: `skills/seo-editor/SKILL.md` — forbidden words section  
> Source 3: `skills/humanizer/SKILL.md` — anti-AI patterns section  
>
> These three sources must be merged, deduplicated, and the canonical list placed here. Once migrated, the word lists in the three source files must be replaced with a reference to this document.

<!-- PLACEHOLDER: Full anti-AI word list goes here -->

---

## Sentence Construction Rules

> **[CONTENT TO BE DEFINED HERE]**  
> Rules about sentence length, passive voice avoidance, filler phrases, and hedge words.

<!-- PLACEHOLDER: Sentence construction rules go here -->

---

## Tone and Register

> **[CONTENT TO BE DEFINED HERE]**  
> Professional but human. Clear over clever. Specific over vague.

<!-- PLACEHOLDER: Tone and register guidelines go here -->

---

## Paragraph and Structure Standards

> **[CONTENT TO BE DEFINED HERE]**  
> Paragraph length limits for web. When to use bullets vs. prose. Transition standards.

<!-- PLACEHOLDER: Paragraph and structure standards go here -->

---

## Patterns That Must Never Appear

> **[CONTENT TO BE DEFINED HERE]**  
> Opening phrases, closing phrases, and structural patterns that signal AI-generated text.

<!-- PLACEHOLDER: Forbidden patterns go here -->
