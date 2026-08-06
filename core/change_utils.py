"""
Shared utilities for PageChange creation and application.
Used by both improve router and autopilot service.
A future ChangeApplicationService (planned for P3-01) will absorb these.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.db.models import PageChange
    from integrations.cms.wordpress import WordPressAdapter

logger = logging.getLogger(__name__)


# ── statistics["artifacts"] helpers ──────────────────────────────────────────

def get_artifact(statistics: dict | None, key: str):
    return (statistics or {}).get("artifacts", {}).get(key)


def set_artifact(statistics: dict, key: str, value) -> dict:
    statistics.setdefault("artifacts", {})[key] = value
    return statistics


# ── Content push routing ──────────────────────────────────────────────────────

def wp_push(wp: "WordPressAdapter", record: "PageChange", content: str) -> None:
    if record.wp_post_type == "page":
        wp.update_page(record.wp_post_id, content)
    else:
        wp.update_post(record.wp_post_id, content)


# ── Meta updates ──────────────────────────────────────────────────────────────

def _meta_diff(
    current_title: str | None,
    current_desc: str | None,
    suggested_title: str | None,
    suggested_desc: str | None,
) -> dict | None:
    """Compute the shared original/suggested fields. Returns None when nothing changed."""
    cur_title = (current_title or "").strip()
    cur_desc = (current_desc or "").strip()
    title_changed = bool(suggested_title) and suggested_title != cur_title
    desc_changed = bool(suggested_desc) and suggested_desc != cur_desc
    if not title_changed and not desc_changed:
        return None
    return {
        "original_meta_title": cur_title or None,
        "original_meta_description": cur_desc or None,
        "suggested_meta_title": suggested_title if title_changed else None,
        "suggested_meta_description": suggested_desc if desc_changed else None,
    }


def build_meta_updates(
    plugin: str,
    current_title: str | None,
    current_desc: str | None,
    suggested_title: str | None,
    suggested_desc: str | None,
) -> dict | None:
    base = _meta_diff(current_title, current_desc, suggested_title, suggested_desc)
    if base is None:
        return None
    return {"plugin": plugin, **base}


def build_shopify_meta_updates(
    current_title: str | None,
    current_desc: str | None,
    suggested_title: str | None,
    suggested_desc: str | None,
    resource_type: str,
    resource_id: int,
) -> dict | None:
    base = _meta_diff(current_title, current_desc, suggested_title, suggested_desc)
    if base is None:
        return None
    return {
        "platform": "shopify",
        "resource_type": resource_type,
        "shopify_resource_id": resource_id,
        **base,
    }


# ── Verification hint ─────────────────────────────────────────────────────────

def extract_verification_hint(original: str, new: str, min_len: int = 60) -> str | None:
    """
    Find first min_len-char block in new_content absent from original_content.
    Linear scan — no difflib, O(n) amortised. Returns None when no distinct block found.
    """
    step = 20
    for i in range(0, max(0, len(new) - min_len + 1), step):
        candidate = new[i : i + min_len]
        if candidate.strip() and candidate not in original:
            return candidate
    return None


# ── Meta rollback ─────────────────────────────────────────────────────────────

def restore_original_meta(
    wp: "WordPressAdapter",
    record: "PageChange",
    mu: dict,
) -> None:
    plugin = mu.get("plugin", "none")
    if plugin == "none":
        if mu.get("platform"):
            logger.warning(
                "restore_original_meta: cannot restore non-WP meta for PageChange %s (platform=%s) — skipping.",
                record.id, mu["platform"],
            )
        return
    orig_title = mu.get("original_meta_title")
    orig_desc = mu.get("original_meta_description")
    if not orig_title and not orig_desc:
        return
    try:
        wp.update_seo_meta(
            record.wp_post_id, record.wp_post_type, plugin, orig_title, orig_desc,
        )
    except Exception as exc:
        logger.warning(
            "restore_original_meta: failed to restore meta for PageChange %s: %s",
            record.id, exc,
        )
