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
