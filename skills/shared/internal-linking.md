# Internal Linking Rules

**Layer:** Shared Document  
**Loaded by:** seo-article-writer, seo-editor  
**Purpose:** The canonical rules for internal linking strategy, hub/spoke architecture, anchor text selection, and link density. Agents that create or modify content use this document to ensure every internal link is purposeful, structurally correct, and aligned with the site's content hierarchy.

> **Maintenance rule:** Internal linking strategy and hub/spoke model guidance lives here exclusively. Do NOT place internal linking rules in SKILL.md files.

---

## What belongs in this document

- Hub/spoke content model — definition and how agents apply it
- How to identify which page is the hub for a given cluster
- Required vs. contextual internal links — the difference and when each applies
- Anchor text rules: descriptive, keyword-relevant, natural in context
- Link density guidelines: how many internal links per article/page
- How to choose which pages to link to (relevance, authority, user journey)
- When NOT to include an internal link
- How to handle pages that have no obvious hub
- The required internal link instruction format (how the router communicates it to the agent)

## What does NOT belong here

- Technical link attributes (nofollow, canonical) — those are developer concerns
- External linking rules — out of scope for these agents
- Backlink strategy — handled by `seo-backlinks` agent
- General SEO standards (keyword placement, heading hierarchy) → `seo-standards.md`
- Agent-specific article structure logic → `SKILL.md`

---

## Hub/Spoke Content Model

> **[CONTENT TO BE DEFINED HERE]**  
> Definition: what a hub page is, what a spoke page is, and how they relate. The semantic relationship the link represents. Why Google values this structure. How clusters are organized in SEO OS (the `cluster` and `is_hub` fields in the keyword table).

<!-- PLACEHOLDER: Hub/spoke model definition and principles -->

---

## Required Internal Links

> **[CONTENT TO BE DEFINED HERE]**  
> When a link is marked as required (injected by the router via the `required_internal_link` field). The agent's obligation: this link MUST appear in the content. How to find a natural placement. The self-check requirement. What to do if no natural placement exists (note it in output; do not force it unnaturally).

<!-- PLACEHOLDER: Required internal link rules -->

---

## Contextual Internal Links

> **[CONTENT TO BE DEFINED HERE]**  
> Links chosen by the agent based on the available sitemap URLs. How to select them: relevance to the paragraph, user journey logic, avoiding over-linking. How many contextual links are appropriate per article length.

<!-- PLACEHOLDER: Contextual internal link rules -->

---

## Anchor Text Standards

> **[CONTENT TO BE DEFINED HERE]**  
> Anchor text must be descriptive of the destination page's topic. Never use "click here", "read more", or the raw URL as anchor text. Keyword-rich anchors are acceptable; exact-match keyword anchors require variation. Natural fit in the sentence is required.

<!-- PLACEHOLDER: Anchor text standards -->

---

## Link Density Guidelines

> **[CONTENT TO BE DEFINED HERE]**  
> Recommended number of internal links by article length. Thresholds above which linking becomes excessive and hurts readability. The minimum to satisfy SEO value.

<!-- PLACEHOLDER: Link density guidelines -->

---

## When Not to Link

> **[CONTENT TO BE DEFINED HERE]**  
> Scenarios where an internal link should not be included even if a relevant page exists. Forced links that interrupt reading flow. Duplicate links to the same page in the same article.

<!-- PLACEHOLDER: When not to link -->
