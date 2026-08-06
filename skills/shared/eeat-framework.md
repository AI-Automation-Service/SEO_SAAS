# E-E-A-T Framework

**Layer:** Shared Document  
**Loaded by:** seo-article-writer, seo-editor, seo-analyzer, content-strategy, seo-page, seo-competitor-pages  
**Purpose:** Canonical source for Google's Experience, Expertise, Authoritativeness, and Trustworthiness framework as applied by SEO OS agents.

> **Maintenance note:** Core Principles reflect timeless content quality standards — update only if fundamental best practices change. Practical Guidance is implementation-level and stable. YMYL Guidance reflects Google's current quality evaluator policies — update when those policies change significantly. SEO OS Conventions are platform-specific implementation decisions.

---

## Core Principles

These four dimensions define how Google's quality evaluators assess content. **Trust is the most important pillar — the other three support it.**

### Experience

Demonstrate that the content reflects real, direct experience with the topic.

- Include specific, concrete details that only someone with genuine experience would know
- Reference actual examples: real products, real places, real outcomes
- Avoid generic advice ("it depends", "consult a professional") as the sole answer
- Surface the client's genuine first-hand experience where it exists

### Expertise

Demonstrate deep, accurate knowledge of the topic.

- Go beyond what the first three Google results say
- Define terms accurately; do not oversimplify technical concepts
- Show knowledge of nuance, edge cases, and common mistakes
- Cite authoritative external sources — government sites, academic research, industry bodies

### Authoritativeness

Demonstrate recognized standing in the topic area.

- Reference credible sources by name — not "studies show", "experts agree", or "research suggests"
- Link to or name recognized authorities in the field
- Stay within the client's established expertise area — do not write about topics the client has no genuine expertise in

### Trust

Trust is the foundation. The other three dimensions are signals that build it.

**Accuracy and honesty:**
- State facts accurately; if uncertain, acknowledge it
- Do not make exaggerated claims ("the only solution", "the best ever")
- Include author attribution: name + credentials or role
- For health, financial, legal, or safety claims: be accurate, balanced, and explicit about limitations
- No clickbait — the title must accurately reflect what the content delivers

**Evidence hierarchy:**

When writing or editing factual content, prefer evidence in the following order:

1. Client-provided knowledge — business context, documented first-hand outcomes, real results the client can substantiate
2. Verified facts — specific, attributable, checkable claims
3. Authoritative external sources — government bodies, academic institutions, established industry bodies
4. General explanation — when no stronger source is available; label it as such

Never fabricate evidence, statistics, studies, customer stories, or case studies to strengthen a claim. If evidence is unavailable, explain honestly without fabricating support.

*This guidance primarily applies to writing agents (seo-article-writer, seo-editor). Other agents that load this document should apply only the sections relevant to their responsibilities.*

---

## Practical Guidance

Implementation guidance that applies when writing or editing any content.

### Answer search intent first

Do not open with generic marketing preamble. Answer the search intent immediately, then add supporting context. This is required for featured snippet eligibility and AI Overview citations.

### Concrete details over generic claims

Avoid vague generalizations. Every significant claim should be grounded in something specific: a named place, a measurable outcome, a named entity.

**Avoid:** "Many businesses have seen strong results."  
**Prefer:** "A manufacturing company in Cairo reduced onboarding time by 40% using this process."

### Depth and nuance

Do not summarize the surface. Cover edge cases, acknowledge complexity, and address questions a reader would naturally ask after reading each section. Content that a reader needs to supplement with another search fails Google's People-First standard.

### First-hand language

Use first-hand language only when it truthfully reflects the client's actual experience. Do not fabricate experience, client outcomes, organizational knowledge, or claimed expertise.

- **When genuine experience exists:** surface it explicitly. "We've found that…", "Our clients typically…", "In our experience…" are appropriate when grounded in the client's real knowledge.
- **When genuine experience is unavailable:** prefer objective, evidence-based explanations. Do not invent first-hand experience to appear more authoritative.

### External citations

- Cite authoritative sources by name
- Prefer: government bodies, academic institutions, established industry bodies, major publications
- Avoid vague attributions ("studies show", "experts agree", "research suggests") — name the source
- If the exact source is not known, use a citation placeholder (see SEO OS Conventions)

### Named examples

Use real, specific examples. A concrete real-world example with a named company, named outcome, or named location is more credible and more quotable by AI systems than a hypothetical scenario.

- Use named examples only when genuinely known — do not invent them
- A realistic unnamed scenario is acceptable when no real example is available, but treat it as illustrative, not as evidence

---

## YMYL Guidance

YMYL ("Your Money or Your Life") topics require elevated E-E-A-T standards. Google applies significantly higher scrutiny to content that can affect a reader's health, financial stability, safety, or legal rights.

### Definition

YMYL topics include:
- Medical symptoms, diagnoses, treatments, medications
- Financial products, investment decisions, tax advice
- Legal advice and rights
- Safety procedures and emergency guidance
- News or information affecting public decisions

**When in doubt, treat the topic as YMYL.** Over-applying scrutiny is safer than under-applying it.

### Elevated requirements

For all YMYL content:
- Every factual claim must be accurate and sourced
- The author or reviewer should have genuine credentials in the topic area
- Cite official, authoritative sources appropriate to the client's country (see table below)
- For health, financial, legal, or safety claims: be accurate, balanced, and explicit about the limits of the advice

### Jurisdiction-appropriate sources

Use authoritative sources appropriate to the subscriber's country, industry, and regulatory environment. The subscriber's Business Context determines the appropriate jurisdiction. Do not assume a country or cite region-specific authorities unless they are relevant to that subscriber.

### When to apply stricter standards

Apply YMYL-level scrutiny when:
- The YMYL flag is explicitly set
- The topic could directly affect a reader's health, financial, legal, or safety decisions
- The topic is borderline — default to the stricter standard

---

## SEO OS Conventions

Platform-specific implementation decisions. These may change if the platform or editorial workflow changes.

### Citation placeholder format

When a specific source is needed but the exact citation is not available, agents must use:

```
[Citation: brief description of the source needed]
```

Examples:
- `[Citation: World Bank data on MENA outsourcing 2024]`
- `[Citation: NHS guidance on type 2 diabetes management]`
- `[Citation: FCA consumer duty guidance 2023]`

The editorial team resolves these placeholders before publishing. This format is how sourcing gaps are tracked across all content produced by SEO OS.

### Never invent URLs

Do not fabricate URLs. A hallucinated link that returns a 404 destroys reader trust and signals low quality to search engines. Use the citation placeholder format instead of inventing a link, even a plausible-sounding one.
