---
name: seo-refresh
description: When the user wants to know when to re-run SEO improvements, re-cluster keywords, refresh content, or update meta titles. Use when the user asks about refresh cadence, re-analysis timing, content update schedules, or "when should I improve this again."
metadata:
  version: 1.0.0
---

# SEO Refresh Decision Framework

Determines the optimal timing for each type of SEO action — meta update, content improvement, content rewrite, and keyword re-clustering — using days-since-last-action and Google Search Console signals.

## Refresh Cadence Thresholds

| Action | Minimum wait | Trigger earlier if |
|--------|-------------|-------------------|
| Meta title/description | **60 days** | CTR drops ≥40% below position benchmark |
| Content improvement | **90 days** | Position drops 3+ spots vs last snapshot |
| Content rewrite | **180 days** | Position 31+ with declining impressions over 60 days |
| Keyword re-clustering | **90 days** | 10+ new untargeted queries appear in GSC for the site |

**Why these minimums:** Google uses ~3–6 months of data to assess changes (see penalty recovery in seo-monitoring). Acting too frequently produces noise in analytics and wastes AI quota. The minimum thresholds ensure Google has time to index and rank the previous change before triggering another.

## GSC Signal Decision Matrix

### CTR Benchmarks by Position

Compare actual CTR from GSC to these baselines. If actual is ≥40% below expected, meta refresh is warranted even before the 60-day threshold.

| Position | Expected CTR (clean SERP) | With AI Overviews |
|----------|--------------------------|-------------------|
| 1 | 25–35% | ~19% |
| 2 | 12–18% | ~12% |
| 3 | 8–12% | ~7% |
| 4–5 | 5–7% | ~5% |
| 6–10 | 2–5% | 2–5% |

**Meta refresh trigger:** Actual CTR < (benchmark × 0.60). Example: position 4 at 2% CTR vs 5–7% expected → 2% < 5% × 0.6 = 3% → trigger.

### Position Bucket Changes

| Change | Action |
|--------|--------|
| Moved from 31+ → 11–30 | Run content improvement (new chance to reach page 1) |
| Moved from 11–30 → 4–10 | Update meta title for new position (CTR opportunity) |
| Dropped 3+ spots | Run content improvement |
| Stable in 1–3 | No content change — monitor CTR only |
| Stuck at 31+ for 180+ days | Consider content rewrite |

## Decision Flow

```
1. Is this the first time this page has been improved?
   YES → Improve freely (no minimum wait)
   NO → continue

2. How many days since last improvement?
   < 30 days → BLOCKED: Too soon. No action recommended.
   30–59 days → MONITOR: Watch GSC signals. No meta or content changes yet.
   60–89 days → META READY: Meta title/description can be updated. Content: wait.
   90–179 days → FULL READY: Meta + content improvement ready to run.
   180+ days → REWRITE ELIGIBLE: Consider full content rewrite if position is stuck.

3. GSC signal override (if data available):
   CTR < benchmark × 0.60 → allow meta refresh even before 60 days (min 30 days)
   Position dropped 3+ spots → allow content improvement even before 90 days (min 45 days)
```

## Action Descriptions

### Meta Title/Description Refresh
- **What:** Re-run `seo-meta` agent to generate a new title and description
- **When ready:** 60 days since last meta update, OR CTR signal override
- **Expected outcome:** CTR improvement when new title better matches search intent for current position
- **Note:** Do not refresh if position changed significantly — title should match the new position's opportunity

### Content Improvement
- **What:** Re-run full `seo-analyzer` + `seo-editor` pipeline
- **When ready:** 90 days since last content edit, OR position drop signal
- **Expected outcome:** Position improvement when content gaps are addressed
- **Note:** Give Google 90 days to index and rank the previous improvement before running again

### Content Rewrite
- **What:** Full rewrite — delete old content, start fresh with new outline
- **When eligible:** 180 days since last improvement AND position 31+ with declining impressions
- **Expected outcome:** Break out of position stagnation
- **Note:** Higher risk than improvement — use when incremental improvement has failed

### Keyword Re-Clustering
- **What:** Re-run `seo-cluster` agent on the keyword set
- **When ready:** 90 days since cluster was created
- **Trigger earlier if:** 10+ new queries appear in GSC that aren't covered by existing clusters
- **Expected outcome:** New content opportunities discovered; better intent matching

## Output Format

When used as an agent (future), output JSON:

```json
{
  "days_since_last_improvement": 45,
  "meta": {
    "ready": false,
    "days_remaining": 15,
    "signal_override": false,
    "reason": "Wait 15 more days (60-day minimum)."
  },
  "content": {
    "ready": false,
    "days_remaining": 45,
    "signal_override": false,
    "reason": "Wait 45 more days (90-day minimum)."
  },
  "cluster": {
    "ready": false,
    "days_remaining": 45,
    "reason": "Wait 45 more days (90-day minimum)."
  },
  "overall_action": "monitor",
  "message": "Last improved 45 days ago. Meta refresh available in 15 days. Check GSC CTR — if below benchmark, meta can be refreshed sooner."
}
```

## Related Skills

- **google-search-console**: CTR benchmarks, position tracking, impressions trends
- **seo-monitoring**: Article database, traffic benchmark, penalty recovery cadence
- **seo-meta**: Meta title/description rewrite for meta-only pages
- **seo-editor**: Full content improvement pipeline
- **seo-cluster**: Keyword clustering and re-clustering
