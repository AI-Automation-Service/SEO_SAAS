# Lessons Learned

## Phase 1

### Skills integration approach
**Decision:** Rather than committing 24 SKILL.md files directly, we provide `scripts/download_skills.py` to fetch them from the upstream claude-seo repo.  
**Why:** WebFetch returns summaries, not raw file content, making direct copying unreliable. A download script ensures we always get the full, correct content from the source.  
**Gap to monitor:** If the upstream claude-seo repo moves or renames skills, the download script will need updating. Pin to a specific commit hash if stability becomes a concern.

### No database for Phase 1
**Decision:** File-based storage (YAML + JSON).  
**Why:** Sufficient for current scale, matches the project-as-directory model, no infrastructure overhead.  
**Gap to monitor:** If queries across 50+ client projects become necessary, revisit with SQLite or PostgreSQL.

## Phase 3

### WordPress adapter has no connection pooling
`WordPressAdapter._request()` calls `httpx.request()` (a top-level convenience function) which creates a new TCP connection per call. For bulk operations (publishing 50 articles, fetching full sitemap) this means repeated handshakes. Fix when throughput becomes a concern: replace with a persistent `httpx.Client` instance on the adapter, calling `self._client.request()`. The client is thread-safe and pools connections internally. Tests would patch `httpx.Client` instead of `httpx.request`.

### Integration status checks run sequentially
`GET /api/projects/{name}/integrations/status` runs WordPress, GSC, and GA4 checks one after another. Each is a network call; total latency = sum of all three. Fix when response time matters: use `concurrent.futures.ThreadPoolExecutor(max_workers=3)` with `executor.map()` to run all three in parallel.
