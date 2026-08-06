"""
Autopilot Service.

Checks eligible PageChanges after cron runs and auto-applies them based on
the project's autopilot_mode setting.

Safety rules (always enforced):
- Never auto-apply > autopilot_daily_limit changes/day (default 5)
- Never auto-apply plagiarism_status = "flagged"
- new_draft changes always remain as WordPress draft (status=draft) even in full_auto
- Kill switch: autopilot_mode = "manual" disables all auto-apply immediately
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _count_today_auto_applied(db: "Session", user_id: int, project_name: str) -> int:
    from core.db.models import PageChange
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.query(PageChange).filter(
        PageChange.user_id == user_id,
        PageChange.project_name == project_name,
        PageChange.applied_by == "autopilot",
        PageChange.approved_at >= today_start,
    ).count()


def _is_eligible(record, mode: str) -> bool:
    """Return True if this PageChange can be auto-applied."""
    if record.plagiarism_status == "flagged":
        return False
    if mode == "semi_auto":
        return (record.action_type or "page_edit") == "meta_edit"
    if mode == "full_auto":
        return True
    return False


def run_autopilot(
    user_id: int,
    project_name: str,
    cron_job_id: int | None = None,
) -> list[int]:
    """
    Find pending PageChanges and auto-apply eligible ones.
    Returns list of applied change IDs.
    """
    from core.db.base import SessionLocal
    from core.db.models import PageChange
    from core.project import load_project_context
    from core.secrets import SecretManager
    from integrations.cms.wordpress import WordPressAdapter
    from integrations.base import IntegrationError
    from core.change_utils import get_artifact, restore_original_meta, wp_push

    db = SessionLocal()
    applied_ids: list[int] = []
    try:
        ctx = load_project_context(user_id, project_name)
        if not ctx:
            return []

        mode = ctx.config.autopilot_mode
        if mode == "manual":
            return []

        daily_limit = ctx.config.autopilot_daily_limit
        today_count = _count_today_auto_applied(db, user_id, project_name)
        remaining = daily_limit - today_count
        if remaining <= 0:
            logger.info(f"Autopilot: daily limit {daily_limit} reached for {project_name}")
            return []

        # Load pending changes (cron-sourced first if cron_job_id given)
        query = db.query(PageChange).filter(
            PageChange.user_id == user_id,
            PageChange.project_name == project_name,
            PageChange.status == "pending",
        )
        if cron_job_id:
            query = query.order_by(
                (PageChange.cron_job_id == cron_job_id).desc(),
                PageChange.created_at.asc(),
            )
        else:
            query = query.order_by(PageChange.created_at.asc())

        pending = query.limit(remaining * 3).all()  # fetch extra so we can filter
        eligible = [r for r in pending if _is_eligible(r, mode)][:remaining]

        if not eligible:
            return []

        # Build WP adapter once
        wp_cfg = ctx.config.integrations.wordpress
        if not wp_cfg.enabled:
            return []

        secrets = SecretManager()
        try:
            wp = WordPressAdapter(
                url=wp_cfg.url,
                username=secrets.get(wp_cfg.username_env),
                password=secrets.get(wp_cfg.password_env),
            )
        except Exception:
            return []

        for record in eligible:
            try:
                action_type = record.action_type or "page_edit"
                rolled_back = False

                if action_type == "new_draft":
                    # Always publish as draft, even in full_auto
                    from integrations.cms.base import PostDraft
                    import markdown as md
                    html = md.markdown(record.new_content, extensions=["tables", "fenced_code"])
                    draft = PostDraft(
                        title=record.draft_title or "New Article",
                        content=html,
                        slug=record.draft_slug or "",
                        status="draft",
                    )
                    created = wp.create_page(draft)
                    record.wp_post_id = created.id
                    record.wp_post_url = created.url

                elif action_type in ("page_edit", "meta_edit"):
                    content_changed = record.original_content != record.new_content
                    if content_changed and action_type == "page_edit":
                        wp_push(wp, record, record.new_content)

                        hint = get_artifact(record.statistics, "verification_hint")
                        if hint:
                            try:
                                verified = wp.verify_content(record.wp_post_id, record.wp_post_type, hint)
                            except Exception as exc:
                                logger.warning("Autopilot PageChange %s: verification failed: %s", record.id, exc)
                                verified = True
                            if not verified:
                                logger.warning(
                                    "Autopilot PageChange %s: WP readback missing content — rolling back (theme-controlled).",
                                    record.id,
                                )
                                try:
                                    wp_push(wp, record, record.original_content)
                                except Exception as exc:
                                    logger.warning("Autopilot PageChange %s: rollback failed: %s", record.id, exc)
                                if record.meta_updates:
                                    restore_original_meta(wp, record, record.meta_updates)
                                record.status = "rolled_back"
                                record.rejection_reason = "theme_controlled_detected"
                                rolled_back = True

                    if not rolled_back and record.meta_updates:
                        mu = record.meta_updates
                        raw_title = (mu.get("suggested_meta_title") or "").strip()
                        raw_description = (mu.get("suggested_meta_description") or "").strip()
                        wp.update_seo_meta(
                            record.wp_post_id,
                            record.wp_post_type,
                            mu.get("plugin", "none"),
                            raw_title or None,
                            raw_description or None,
                        )

                if not rolled_back:
                    record.status = "approved"
                record.approved_at = datetime.utcnow()
                record.applied_by = "autopilot"
                db.commit()
                applied_ids.append(record.id)
                logger.info(f"Autopilot applied change {record.id} ({action_type}) for {project_name}")

            except Exception as e:
                logger.warning(f"Autopilot: failed to apply change {record.id}: {e}")
                continue

        return applied_ids
    finally:
        db.close()
