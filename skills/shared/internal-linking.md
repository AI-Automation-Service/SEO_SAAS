# Internal Linking Rules

**Layer:** Shared Document  
**Loaded by:** seo-plan, site-architecture, seo-flow, seo-editor, seo-article-writer, content-strategy  
**Purpose:** Canonical rules for internal linking strategy: hub/spoke model, anchor text standards, contextual link selection, and when not to link.

> **Maintenance rule:** Internal linking strategy lives here exclusively. Do NOT place internal linking rules in SKILL.md files.
>
> **Scope:** This document covers universal internal linking principles for content agents — anchor text, hub/spoke best practices, orphan prevention, and contextual selection. Dynamic link graph management (tracking published articles, updating cross-links as the content library grows, orchestrating the hub/spoke graph over time) belongs in a future Internal Link Planner component, not here.

---

## Hub/Spoke Content Model

Content is organized into topic clusters. Each cluster has one hub (pillar) page and multiple spoke pages.

**Hub page:**
- Broad topic, comprehensive coverage
- Targets the cluster's primary keyword
- Links to every spoke in its cluster

**Spoke page:**
- One focused subtopic within the cluster
- Always links back to its hub
- Cross-links to related spokes where topically relevant

**Why this structure matters:**
- Hub pages accumulate link equity and distribute it to spokes
- Spoke pages signal topical depth to search engines, strengthening the hub's authority
- Clear cluster boundaries prevent keyword cannibalization — one topic, one page

**No orphan pages.** Every page must have at least one internal link pointing to it. A page with no inbound internal links receives no link equity from the rest of the site and rarely ranks.

---

## Required Internal Links

Some agents receive a required link from the router — a specific target URL that must appear in the content (typically the hub page for the current cluster, passed as `hub_url`).

When a required link is specified:
- It MUST appear somewhere in the content
- Find the most natural placement in existing body text
- Do not fabricate a sentence just to carry the link — if no natural placement exists, note it in the output instead
- Use the exact URL provided — never substitute or invent a URL

---

## Contextual Internal Links

Contextual links are chosen by the agent based on the content and user journey.

**Selection principles:**
- Link to pages that are topically relevant to the paragraph where the link appears
- Follow user journey logic: link to the next most useful page for a reader at that point
- Spoke pages link up to their hub; hub pages link to all their spokes; related spokes cross-link where the connection genuinely serves the reader

**Density:**

There is no fixed count. Judge by content length and cluster structure. Three well-placed links in a page typically satisfy the structural requirement — do not force more. For long-form articles, 2–4 contextual links serve readers without disrupting flow. Density should serve the reader, not a number target.

---

## Anchor Text Standards

**Priority order for selecting anchor text:**

1. Find the first natural occurrence of the target page's primary keyword (or close variation) in the body text — wrap that phrase
2. If the primary keyword is already linked elsewhere in the same content, use a related secondary phrase that describes the destination page's topic
3. If no natural phrase exists, wrap the nearest relevant phrase — do not write a new sentence for the link

**Rules:**
- Anchor text must describe what the destination page covers — it signals to both readers and search engines what to expect at the link destination
- Never use: "click here", "read more", "here", "this article", or the raw URL
- Vary anchors slightly across multiple links to the same destination — exact repetition looks unnatural
- Keyword-rich anchors are acceptable; exact-match keyword stuffing is not — natural phrasing in context takes priority

---

## When Not to Link

- No relevant destination page exists for the context
- The same destination has already been linked earlier in the same content — the first occurrence is sufficient
- The only way to insert the link is to write a new sentence whose sole purpose is to carry it
- The content is very short (under 300 words) and a link would interrupt the reading flow
