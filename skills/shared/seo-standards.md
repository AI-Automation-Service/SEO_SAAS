# SEO Standards

**Layer:** Shared Document  
**Loaded by:** seo-analyzer, seo-editor, seo-meta, seo-article-writer  
**Purpose:** The canonical on-page SEO standards applied by all analysis and editing agents. Covers keyword placement, heading hierarchy, meta tag rules, URL standards, and content structure norms. These are measurable, technical SEO rules — not quality/authority signals (which belong in `eeat-framework.md`).

> **Maintenance rule:** When SEO best practices change (e.g., Google updates its guidance on title length or heading structure), update this file. Do NOT scatter updated SEO rules into individual SKILL.md files.

---

## Keyword Placement Rules

### Primary keyword placement (required)

- **Title tag:** Primary keyword must appear in the first half of the title tag.
- **H1:** Primary keyword must appear in the H1, either verbatim or as a close semantic variant.
- **First paragraph:** Primary keyword must appear naturally within the first 100 words of body content.
- **Meta description:** Primary keyword must appear once, naturally integrated — not force-inserted.

### Keyword density

| Signal | Threshold | Action |
|---|---|---|
| Below 0.3% | Keyword appears too rarely | Flag as thin on keyword — consider adding naturally |
| 0.3% – 1.5% | Normal range for most content | No action |
| 1.5% – 2.5% | Elevated — watch for stuffing pattern | Review context; acceptable if naturally distributed |
| Above 2.5% | Signals keyword stuffing | Flag — reduce occurrences or rewrite affected sections |

Density = (keyword occurrences / total word count) × 100. Count exact match + close variants together.

### Secondary keywords

- Secondary keywords belong in H2s, sub-paragraphs, and image alt text — not forced into the first paragraph.
- Semantic variants and related terms should appear organically throughout the body.
- Never repeat the primary keyword as a section heading to inflate density.

---

## Title Tag Standards

| Rule | Specification |
|---|---|
| **Length** | 45–60 characters. Google truncates at approximately 600px (≈60 chars for standard font). Minimum 30 characters — below this, the title lacks informational value. |
| **Keyword position** | Primary keyword in the first half; ideally in the first 3 words. |
| **Format** | `[Primary Keyword] \| [Compelling Differentiator]` for service/product pages. Homepage: `[Brand] — [Core Value Proposition]`. |
| **Uniqueness** | Every page must have a unique title tag. Duplicate titles are a crawl and ranking signal failure. |
| **Brand** | Include brand name after a pipe separator when it adds recognition value. Omit if the keyword already includes the brand. |
| **Never** | Template variables (%%title%%, %%sitename%%). Keyword repetition after the pipe. Generic titles ("Home", "Page 1"). |

### Good vs. bad examples

- Good: `AI Consultant Services \| Custom AI Built for Your Business` (54 chars)
- Good: `SEO Audit Tool \| Catch Issues Before Google Does` (49 chars)
- Bad: `AI Consultant Services \| AI Consultant Service` — keyword repeated
- Bad: `Our Amazing Web Services For All Businesses` — generic, no keyword value
- Bad: `SEO` — too short, no context

---

## Meta Description Standards

| Rule | Specification |
|---|---|
| **Length** | 120–158 characters. Google truncates at approximately 920px (≈158 chars). Minimum 100 characters — below this, Google typically rewrites it. |
| **Keyword inclusion** | Include the primary keyword once, integrated naturally. Google bolds matching terms in SERPs. |
| **Intent match** | First sentence must answer the dominant search intent for the target keyword. |
| **CTA** | End with a subtle action or value differentiator — not a command, but a pull. |
| **Uniqueness** | Every page must have a unique meta description. |
| **Never** | Template variables. Keyword stuffing. Pure keyword lists. |

### Intent-matched opening patterns

| Intent | Opening approach |
|---|---|
| Informational | Answer the question the keyword implies in the first sentence |
| Commercial investigation | Lead with the key differentiator (what makes this option worth considering) |
| Transactional | Lead with the action and primary benefit |
| Navigational | Confirm what the user will find on this specific page |

---

## Heading Hierarchy

### H1 rules

- **One H1 per page.** Multiple H1s dilute the topical signal.
- H1 must contain the primary keyword, verbatim or as a close semantic variant.
- H1 must be unique across the site — not a duplicate of the title tag, but thematically aligned.
- H1 should represent the broadest topic covered by the page.

### H2 rules

- H2s are the primary structural signal for topical coverage.
- Each major topic or subtopic the page covers should have its own H2.
- H2s should collectively cover the range of related questions and terms a searcher on the primary keyword would care about.
- Secondary keywords naturally belong in H2s.

### H3–H6 rules

- H3s subdivide an H2 section. They are for detail, not keyword targeting.
- H4 and below: use only when the content genuinely requires sub-division. Never for decorative structure.
- Never skip heading levels (H1 → H3 with no H2).
- Never use headings purely for visual styling — use CSS classes instead.

### What signals a broken hierarchy

- H2 before H1
- Multiple H1s
- Headings used as keyword containers with no structural purpose
- Long pages (>1,500 words) with no H2s — signals lack of topical organization

---

## Content Length Benchmarks

These are signals, not rules. Content length should match the depth required to fully answer the search intent — not a word count target.

| Page type / Intent | Minimum meaningful length | Notes |
|---|---|---|
| Navigational (brand, contact, pricing) | 200–400 words | Long-form is unnecessary and often harmful |
| Informational (how-to, guide, tutorial) | 800–1,500 words | Match competitor depth; above 2,000 words only when topic genuinely requires it |
| Commercial investigation (best X, X vs Y) | 1,000–2,000 words | Needs real comparison depth to rank |
| Transactional (product, service page) | 400–800 words | Focus on clarity and conversion, not volume |
| Long-form pillar content | 2,000–4,000 words | Only for primary hub pages with genuine depth requirement |

### Thin content threshold

A page is at thin-content risk when:
- Body word count is under 300 words for a non-navigational page
- Content does not substantively address the search intent behind the target keyword
- The page is near-duplicate of another page with slight variation (e.g., city-specific landing pages with swapped location names)

---

## Image SEO Standards

| Element | Rule |
|---|---|
| **Alt text** | Descriptive of the image content. Include the primary keyword when it describes the image accurately — never force it. Maximum 125 characters. Empty alt on decorative images. |
| **File naming** | Lowercase, hyphen-separated, descriptive. Example: `seo-audit-dashboard-screenshot.webp` not `IMG_00142.jpg`. |
| **Format** | WebP preferred for photos and complex images. SVG for logos and icons. PNG only when transparency is required and WebP is unavailable. |
| **File size** | Under 150KB for most images. Hero images: under 300KB. Flag images over 500KB as a performance issue. |
| **Dimensions** | Serve images at their display size. No oversized images scaled down by CSS. |
| **CLS** | Width and height attributes required on all `<img>` tags to prevent layout shift. |

---

## Schema Markup Recommendations

Schema markup signals page type to Google directly. Apply based on the page's primary purpose.

| Page type | Recommended schema | Priority |
|---|---|---|
| Article / Blog post | `Article` (or `BlogPosting`) | High |
| FAQ page / FAQ section | `FAQPage` | High |
| How-to guide | `HowTo` | High |
| Local business | `LocalBusiness` | Critical for local |
| Product page | `Product` + `Offer` | High for ecommerce |
| Service page | `Service` | Medium |
| Homepage (service business) | `Organization` or `LocalBusiness` | Medium |
| Review page | `Review` or `AggregateRating` | High if reviews present |

### Implementation notes

- Validate schema with Google's Rich Results Test before deploying.
- JSON-LD format only — not Microdata or RDFa.
- Schema must accurately reflect the page content — do not add schema for content that isn't present.
- Duplicate schema types on the same page are acceptable when they refer to different entities.
