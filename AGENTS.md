# AGENTS.md — SEO OS Agent Reference

## System Overview

SEO OS is a multi-tenant SaaS that automates WordPress on-page SEO, keyword clustering, and content strategy. Every subscriber runs the same pipeline against their own WordPress site and keyword data. Tenant isolation is enforced by `user_id` + `project_name` on every database query.

**Three-layer model:**
- **Skills / Directives** — `skills/<agent>/SKILL.md` loaded as system prompt via `SkillAgent`
- **Routers / Orchestration** — `api/routers/*.py` — routing logic, message construction, model selection
- **Integrations / Execution** — `integrations/cms/wordpress.py` — WordPress REST API, Yoast/RankMath meta updates

**Security rules (non-negotiable):**
- All OpenAI calls use `get_user_secret("openai", user_id, db)` — never server env vars
- BYOK model: each user enters their own OpenAI API key during onboarding
- Never commit secrets — .env, API keys, JWT secret, encryption master key are VPS-only

---

## Agent Registry

| Agent | Model | Skill file | Router | Output |
|---|---|---|---|---|
| seo-cluster | gpt-4o-mini | skills/seo-cluster/SKILL.md | keywords.py:691 | JSON |
| seo-refresh | — (Python logic) | skills/seo-refresh/SKILL.md | improve.py:_compute_refresh_status | dict |
| seo-analyzer | gpt-4o-mini | skills/seo-analyzer/SKILL.md | improve.py:214 | JSON |
| seo-editor | gpt-4o | skills/seo-editor/SKILL.md | improve.py:274 | JSON |
| seo-meta | gpt-4o-mini | skills/seo-meta/SKILL.md | improve.py:_run_meta_only | JSON |
| seo-plan | gpt-4o | skills/seo-plan/SKILL.md | strategy.py:247 | Markdown |
| content-strategy | gpt-4o | skills/content-strategy/SKILL.md | strategy.py:281 | Markdown |
| site-architecture | gpt-4o | skills/site-architecture/SKILL.md | strategy.py:316 | Markdown |
| seo-flow | gpt-4o | skills/seo-flow/SKILL.md | strategy.py:360 | Markdown |
| seo-page | gpt-4o | skills/seo-page/SKILL.md | strategy.py:420 | Markdown |
| seo-competitor-pages | gpt-4o | skills/seo-competitor-pages/SKILL.md | strategy.py:463 | Markdown |

**How agents load skills:** `SkillAgent(skill_name, openai_key, model=...)` reads `skills/<skill_name>/SKILL.md` as the OpenAI system prompt. Skill files are cached in `_SKILL_CACHE` per process. Subdirectory paths work: `SkillAgent("marketing/seo/on-page/title", ...)`.

**Prompt caching:** OpenAI caches system prompts after the first call (~75% token discount). Larger SKILL.md files are a one-time cost per process restart.

---

## Routing Rules

| Page scenario | Pipeline |
|---|---|
| Gutenberg or Classic + Yoast/RankMath | analyzer (mini) → editor (gpt-4o) |
| Gutenberg or Classic, no SEO plugin | analyzer (mini) → editor (gpt-4o, content only, no meta) |
| Builder/theme-controlled + Yoast/RankMath | **seo-meta (mini)**, NO HTML sent — zero content calls |
| Builder/theme-controlled, no SEO plugin | Blocked — zero AI calls |
| WordPress posts listing page + Yoast/RankMath | **seo-meta (mini)** — content is the WordPress Loop, not editable |
| WordPress posts listing page, no SEO plugin | Blocked — zero AI calls |

**Meta-only path** (Phase 3 optimization): When `not content_editable and meta_editable`, skip both analyzer and editor. Route to `_run_meta_only()` which calls `seo-meta` with keyword + business context + current meta — no HTML. Saves one gpt-4o call and one gpt-4o-mini call for every Elementor/Divi/theme page.

**Analyzer vs Editor HTML:** Analyzer receives `_strip_html_for_analysis()` output (block comments and class/style/data attributes removed — structural tags kept). Editor receives the original full HTML (needs `<!-- wp:... -->` block markers for correct insertion).

---

## Knowledge Base Contract

Every agent message includes a `## business_context` block derived from `ProjectKnowledge`. Fields:

| DB field | Label in message |
|---|---|
| `about` | About / Business |
| `products_services` | Products/Services |
| `target_audience` | Target Audience |
| `brand_voice` | Brand Voice |
| `competitors_notes` | Competitors |
| `seo_context` | SEO Context |

Empty fields are omitted. If all fields are empty, the block is omitted entirely.

**Wiring status:**
- `strategy.py`: all 6 endpoints use `_knowledge_block()` ✓
- `keywords.py`: cluster agent uses expanded inline KB (all 6 fields) ✓
- `improve.py`: `_run_page_pipeline()` uses `_knowledge_block()` ✓

---

## Page Builder Support Matrix

> **Source of truth: [`config/builders.yaml`](config/builders.yaml)**
> Do not edit the table below directly — update the YAML instead.
> Changes to the YAML take effect within 5 minutes on the live server (no restart needed).
> To add a new builder: add one entry to `builders.yaml`. Zero Python changes required.

| Builder | content_editable | Detection signal |
|---|---|---|
| Gutenberg | Yes | `<!-- wp:` in post_content |
| Elementor | No | `data-elementor-type` / `elementor elementor-` in **rendered HTML** |
| Divi | No | `[et_pb_` in post_content OR `et_pb_section` in rendered HTML |
| WPBakery | No | `[vc_row]` in post_content OR `wpb_wrapper` in rendered HTML |
| Bricks | No | `data-bricks` / `brxe-` in post_content or rendered HTML |
| Oxygen | No | `ct-section` / `oxy-` in post_content or rendered HTML |
| Beaver Builder | No | `[fl_builder_` in post_content OR `fl-builder-content` in rendered HTML |
| Brizy | No | `brz-` class prefix in rendered HTML |
| Thrive Architect | No | `[tve_` in post_content OR `tve_editor_main_content` in rendered HTML |
| Fusion Builder (Avada) | No | `[fusion_builder_` in post_content OR `fusion-builder-row` in rendered HTML |
| SeedProd | No | `seedprod-` in rendered HTML |
| Breakdance | No | `data-breakdance` / `bde-` in rendered HTML |
| Zion Builder | No | `data-zionbuilder` / `zb-element` in rendered HTML |
| Classic Editor | Yes | fallback — none of the above matched |
| Unknown builder (safety net) | No | post_content < 30 words AND rendered page > 200 words AND no builder matched |
| Theme-controlled homepage | No | `is_homepage=True` and `word_count < 100` (Python logic, not YAML) |
| WordPress posts listing page | No | `is_posts_page=True` from `find_post_by_url()` — page ID matches `page_for_posts` in `/wp/v2/settings` |

**Two-pass detection** (both passes use `_detect_builder()` against `config/builders.yaml`):
- **Pass 1** — `post_content` from REST API (`?context=edit`). Works for Gutenberg, Divi shortcodes, WPBakery shortcodes.
- **Pass 2** — rendered public HTML (HTTP GET on the page URL). Fires only when `post_content < 30 words`. Catches Elementor (which stores data in `_elementor_data` meta, leaving `post_content` empty), Brizy, SeedProd, and others.
- **Safety net** — if rendered HTML has > 200 words but no builder matched, treat as `unknown-builder` (non-editable) to avoid overwriting builder data.

Detection: `_detect_builder()` in `improve.py` iterates `config/builders.yaml` in order. `_detect_page_profile()` + Pass 2 in `_run_page_pipeline()` combine into a final `profile` dict before any AI call.

---

## SEO Plugin Support

Detected via WordPress REST API namespace registry (`detect_seo_plugin()` in `wordpress.py`):
- `yoast` → namespace contains `yoast`
- `rankmath` → namespace contains `rankmath`
- `none` → no plugin detected

Meta fields updated via `update_seo_meta()`:
- Yoast: `_yoast_wpseo_title`, `_yoast_wpseo_metadesc`
- RankMath: `rank_math_title`, `rank_math_description`

---

## Skills Library

### Committed on VPS (use-first for enrichment)

| File | Purpose |
|---|---|
| skills/seo-cluster/SKILL.md | Keyword clustering + intent classification |
| skills/seo-analyzer/SKILL.md | AEO/GEO signal analysis |
| skills/seo-editor/SKILL.md | Content insertion + meta generation |
| skills/seo-meta/SKILL.md | Meta-only optimization (no HTML) |
| skills/seo-plan/SKILL.md | 12-month SEO roadmap |
| skills/content-strategy/SKILL.md | Topic clusters, content calendar |
| skills/site-architecture/SKILL.md | Page hierarchy, URL patterns, nav |
| skills/seo-flow/SKILL.md | FLOW framework + SERP feature targeting |
| skills/seo-page/SKILL.md | Per-page improvement plan |
| skills/seo-competitor-pages/SKILL.md | Competitor comparison pages |
| skills/humanizer/SKILL.md | Anti-AI writing patterns |
| skills/seo-schema/SKILL.md | Schema detection + generation |
| skills/seo-images/SKILL.md | Image alt, format, CLS, SERP |
| skills/seo-technical/SKILL.md | Technical SEO audit |
| skills/seo-audit/SKILL.md | Full SEO audit methodology |
| skills/seo-backlinks/SKILL.md | Backlink profile analysis |
| skills/copywriting/SKILL.md | Conversion copy frameworks |
| skills/seo-local/SKILL.md | Local SEO signals |

### Downloaded skills (skills/marketing/) — enrichment source

172 skills from kostja94/marketing-skills. Key groups used for enrichment:

| Category | Used for |
|---|---|
| seo/content/keyword-research | seo-cluster, seo-flow |
| seo/content/eeat-signals | seo-editor, content-strategy, seo-page |
| seo/on-page/featured-snippet | seo-analyzer, seo-flow, seo-page |
| seo/on-page/title + description | seo-meta |
| seo/content/content-strategy | content-strategy |
| seo/content/competitor-research | seo-competitor-pages |
| strategies/structure/seo | seo-plan |
| pages/marketing/alternatives | seo-competitor-pages |
| seo/on-page/url-structure | site-architecture |
| seo/on-page/internal-links | site-architecture |

---

## Agent → Skill Map (Final)

| Agent | Local skills merged | Downloaded skills merged |
|---|---|---|
| seo-cluster | — | keyword-research |
| seo-analyzer | seo-images (alt count) | featured-snippet |
| seo-editor | seo-schema, humanizer | eeat-signals |
| seo-meta (new) | — | on-page/title, on-page/description |
| seo-plan | seo-audit | strategies/structure/seo |
| content-strategy | copywriting | content-strategy, eeat-signals |
| site-architecture | site-architecture/references/ | url-structure, internal-links |
| seo-flow | — | featured-snippet, keyword-research |
| seo-page | seo-images, seo-schema, seo-local | content-optimization, eeat-signals, featured-snippet |
| seo-competitor-pages | seo-backlinks | competitor-research, alternatives |

---

## Unwired Skills (on VPS, not yet routed to any agent)

These skills exist but are not invoked by any current router endpoint. Available for future features:

`seo-improve`, `seo-article-writer`, `seo-content`, `seo-content-brief`, `seo-dataforseo`, `seo-drift`, `seo-ecommerce`, `seo-geo`, `seo-google`, `seo-hreflang`, `seo-image-gen`, `seo-maps`, `seo-programmatic`, `seo-sitemap`, `seo-sxo`, `copy-editing`, `seo-local` (used for seo-page enrichment), `seo-schema` (used for enrichment, not direct wiring)

**`seo-refresh`**: Currently implemented as pure Python in `improve.py:_compute_refresh_status`. The SKILL.md documents the framework and CTR benchmarks for future agent wiring (e.g., when GSC data is available per page). Outputs `refresh_status` in every `/analyze` response.

---

## Adding a New Agent

1. Create `skills/<agent-name>/SKILL.md` with system prompt
2. Add `SkillAgent("<agent-name>", openai_key, model="...")` call in appropriate router
3. Wire `_knowledge_block()` into the user message
4. Update this file: agent registry table + agent→skill map
5. Push to GitHub, pull on VPS
