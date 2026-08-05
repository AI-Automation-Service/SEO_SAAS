"""
APScheduler-based cron system for SEO OS.

Six job types:
  gsc_sync         — weekly: pull fresh keyword positions from GSC
  ranking_monitor  — weekly: detect P0/P1 drops, run improve pipeline on affected pages
  content_refresh  — monthly: re-run seo-analyzer on stale pages (30+ days)
  content_calendar — per plan: trigger article writer on scheduled dates
  cluster_improve  — weekly: pick next cluster from improvement_queue, run improve pipeline
  meta_audit       — monthly: run seo-meta on pages missing optimized titles/descriptions

All cron runs produce pending PageChanges — never auto-apply unless Autopilot is active.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ── Job implementations ────────────────────────────────────────────────────────

def _run_gsc_sync(user_id: int, project_name: str, cron_job_id: int) -> int:
    """Pull fresh GSC keyword data and update positions."""
    from core.db.base import SessionLocal
    from core.db.models import CronRun, CronJob, Keyword
    from api.routers.keywords import _sync_keywords_from_gsc
    from core.project import load_project
    from core.secrets import SecretManager

    db = SessionLocal()
    run = CronRun(cron_job_id=cron_job_id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        from core.project import load_project_context
        ctx = load_project_context(user_id, project_name)
        if not ctx:
            raise ValueError(f"Project not found: {project_name}")

        count = _sync_keywords_from_gsc(user_id, project_name, ctx, db)
        run.status = "success"
        run.completed_at = datetime.utcnow()
        run.changes_created = count
        db.query(CronJob).filter(CronJob.id == cron_job_id).update({
            "last_run_at": datetime.utcnow(),
            "next_run_at": datetime.utcnow() + timedelta(days=7),
        })
        db.commit()
        return count
    except Exception as e:
        run.status = "error"
        run.error_detail = str(e)
        run.completed_at = datetime.utcnow()
        db.commit()
        logger.error(f"gsc_sync failed for {project_name}: {e}")
        return 0
    finally:
        db.close()


def _run_cluster_improve(user_id: int, project_name: str, cron_job_id: int) -> int:
    """Pick the next cluster from the improvement_queue and run the improve pipeline."""
    from core.db.base import SessionLocal
    from core.db.models import CronRun, CronJob, Keyword, StrategyOutput, PageChange
    import json

    db = SessionLocal()
    run = CronRun(cron_job_id=cron_job_id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    changes_created = 0

    try:
        # Load execution plan to find next priority cluster
        plan_row = db.query(StrategyOutput).filter(
            StrategyOutput.user_id == user_id,
            StrategyOutput.project_name == project_name,
            StrategyOutput.strategy_type == "plan_json",
        ).first()

        if plan_row:
            plan = json.loads(plan_row.output)
            queue = plan.get("improvement_queue", [])
        else:
            queue = []

        # Pick the first cluster from the improvement queue that has a hub with existing_url
        target_cluster = None
        for item in queue:
            cluster_name = item.get("cluster")
            has_hub = db.query(Keyword).filter(
                Keyword.user_id == user_id,
                Keyword.project_name == project_name,
                Keyword.cluster == cluster_name,
                Keyword.is_hub == True,
                Keyword.existing_url.isnot(None),
            ).first()
            if has_hub:
                target_cluster = cluster_name
                break

        if not target_cluster:
            # Fall back to oldest-unimproved cluster
            keywords = db.query(Keyword).filter(
                Keyword.user_id == user_id,
                Keyword.project_name == project_name,
                Keyword.is_hub == True,
                Keyword.existing_url.isnot(None),
                Keyword.cluster.isnot(None),
            ).all()
            improved_clusters = {
                pc.cluster_name
                for pc in db.query(PageChange).filter(
                    PageChange.user_id == user_id,
                    PageChange.project_name == project_name,
                    PageChange.status.in_(["pending", "approved"]),
                ).all()
            }
            unimproved = [k for k in keywords if k.cluster not in improved_clusters]
            if unimproved:
                target_cluster = unimproved[0].cluster

        if target_cluster:
            from api.routers.improve import _run_cron_improve
            new_changes = _run_cron_improve(user_id, project_name, target_cluster, cron_job_id, db)
            changes_created = len(new_changes)

        run.status = "success"
        run.completed_at = datetime.utcnow()
        run.changes_created = changes_created
        db.query(CronJob).filter(CronJob.id == cron_job_id).update({
            "last_run_at": datetime.utcnow(),
            "next_run_at": datetime.utcnow() + timedelta(days=7),
        })
        db.commit()
        return changes_created
    except Exception as e:
        run.status = "error"
        run.error_detail = str(e)
        run.completed_at = datetime.utcnow()
        db.commit()
        logger.error(f"cluster_improve failed for {project_name}: {e}")
        return 0
    finally:
        db.close()


def _run_meta_audit(user_id: int, project_name: str, cron_job_id: int) -> int:
    """Run seo-meta on pages that are missing optimized meta title or description."""
    from core.db.base import SessionLocal
    from core.db.models import CronRun, CronJob, Keyword, PageChange
    from api.routers.api_keys import get_user_secret
    from api.routers.improve import _get_wp_adapter, _run_meta_only, _knowledge_block
    from core.project import load_project

    db = SessionLocal()
    run = CronRun(cron_job_id=cron_job_id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    changes_created = 0

    try:
        openai_key = get_user_secret("openai", user_id, db)
        from core.project import load_project_context
        ctx = load_project_context(user_id, project_name)
        if not ctx:
            raise ValueError(f"Project not found: {project_name}")

        wp = _get_wp_adapter(ctx)
        seo_plugin = wp.detect_seo_plugin()

        if seo_plugin == "none":
            run.status = "success"
            run.completed_at = datetime.utcnow()
            run.changes_created = 0
            db.commit()
            return 0

        hubs = db.query(Keyword).filter(
            Keyword.user_id == user_id,
            Keyword.project_name == project_name,
            Keyword.is_hub == True,
            Keyword.existing_url.isnot(None),
        ).all()

        knowledge = _knowledge_block(db, user_id, project_name)

        for hub in hubs[:10]:
            try:
                post_data = wp.find_post_by_url(hub.existing_url)
                if not post_data:
                    continue
                current_title = (post_data.get("current_meta_title") or "").strip()
                current_desc = (post_data.get("current_meta_description") or "").strip()
                if current_title and current_desc:
                    continue  # already optimized
                profile = {
                    "seo_plugin": seo_plugin,
                    "is_homepage": False,
                    "is_theme_controlled": False,
                    "is_posts_page": False,
                    "meta_editable": True,
                }
                record = _run_meta_only(
                    hub.keyword, post_data, profile, knowledge, openai_key,
                    user_id, project_name, hub.cluster or "meta_audit", ctx.config, db,
                )
                if record.status == "pending":
                    record.cron_job_id = cron_job_id
                    record.source_agent = "meta_audit"
                    db.commit()
                    changes_created += 1
            except Exception as e:
                logger.warning(f"meta_audit: skipping {hub.existing_url}: {e}")
                continue

        run.status = "success"
        run.completed_at = datetime.utcnow()
        run.changes_created = changes_created
        db.query(CronJob).filter(CronJob.id == cron_job_id).update({
            "last_run_at": datetime.utcnow(),
            "next_run_at": datetime.utcnow() + timedelta(days=30),
        })
        db.commit()
        return changes_created
    except Exception as e:
        run.status = "error"
        run.error_detail = str(e)
        run.completed_at = datetime.utcnow()
        db.commit()
        logger.error(f"meta_audit failed for {project_name}: {e}")
        return 0
    finally:
        db.close()


# ── Dispatcher ─────────────────────────────────────────────────────────────────

_JOB_HANDLERS = {
    "gsc_sync": _run_gsc_sync,
    "cluster_improve": _run_cluster_improve,
    "meta_audit": _run_meta_audit,
}


def _dispatch_job(user_id: int, project_name: str, job_type: str, cron_job_id: int) -> None:
    handler = _JOB_HANDLERS.get(job_type)
    if handler:
        logger.info(f"Cron {job_type} starting for {project_name}")
        changes_created = handler(user_id, project_name, cron_job_id)
        # After cron creates changes, trigger autopilot if enabled
        if changes_created:
            try:
                from agents.autopilot import run_autopilot
                applied = run_autopilot(user_id, project_name, cron_job_id)
                if applied:
                    logger.info(f"Autopilot applied {len(applied)} change(s) for {project_name}")
                    # Update CronRun auto_applied count
                    from core.db.base import SessionLocal
                    from core.db.models import CronRun
                    _db = SessionLocal()
                    try:
                        last_run = (
                            _db.query(CronRun)
                            .filter(CronRun.cron_job_id == cron_job_id)
                            .order_by(CronRun.started_at.desc())
                            .first()
                        )
                        if last_run:
                            last_run.auto_applied = len(applied)
                            _db.commit()
                    finally:
                        _db.close()
            except Exception as e:
                logger.warning(f"Autopilot post-cron failed: {e}")
    else:
        logger.warning(f"Unknown cron job type: {job_type}")


def _tick() -> None:
    """Check all enabled cron jobs and dispatch those that are due."""
    from core.db.base import SessionLocal
    from core.db.models import CronJob

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due_jobs = db.query(CronJob).filter(
            CronJob.enabled == True,
            CronJob.next_run_at <= now,
        ).all()

        for job in due_jobs:
            try:
                _dispatch_job(job.user_id, job.project_name, job.job_type, job.id)
            except Exception as e:
                logger.error(f"Cron dispatch error for job {job.id}: {e}")
    finally:
        db.close()


# ── Lifecycle ──────────────────────────────────────────────────────────────────

def start_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _tick,
        trigger=IntervalTrigger(minutes=15),
        id="cron_tick",
        replace_existing=True,
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info("APScheduler started — cron tick every 15 minutes")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
