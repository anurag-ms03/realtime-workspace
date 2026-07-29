import json
import logging
from datetime import datetime, timedelta

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.workspace import Workspace, AuditLog

logger = logging.getLogger(__name__)

GRACE_PERIOD_DAYS = 30


@celery_app.task(
    name="purge_expired_soft_deleted_workspaces",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,    # cap at 5 min — this runs once daily, no rush
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=120,      # this touches the DB and could scan many rows
    time_limit=180,
)
def purge_expired_soft_deleted_workspaces() -> dict:
    """
    Hard-deletes workspaces that have been soft-deleted (is_active=False)
    for longer than GRACE_PERIOD_DAYS. Writes an audit log entry for each
    purge before deleting, since AuditLog.entity_id has no FK constraint
    and survives the workspace's removal.
    """
    db = SessionLocal()
    purged = []

    try:
        cutoff = datetime.utcnow() - timedelta(days=GRACE_PERIOD_DAYS)

        expired = (
            db.query(Workspace)
            .filter(Workspace.is_active == False, Workspace.updated_at < cutoff)
            .all()
        )

        if not expired:
            logger.info("[CLEANUP] No expired soft-deleted workspaces found")
            return {"purged_count": 0, "workspace_ids": []}

        for workspace in expired:
            log = AuditLog(
                user_id=None,  # system-initiated, not a specific user
                entity_type="workspace",
                entity_id=str(workspace.id),
                action="purged",
                changes=json.dumps({
                    "name": workspace.name,
                    "slug": workspace.slug,
                    "soft_deleted_at": workspace.updated_at.isoformat(),
                    "grace_period_days": GRACE_PERIOD_DAYS,
                }),
                ip_address=None,
            )
            db.add(log)
            purged.append(str(workspace.id))

            # Cascades to projects → tasks via the relationship cascade
            # and DB-level ON DELETE CASCADE already in your schema
            db.delete(workspace)

        db.commit()
        logger.info(f"[CLEANUP] Purged {len(purged)} expired workspace(s): {purged}")
        return {"purged_count": len(purged), "workspace_ids": purged}

    except Exception as e:
        db.rollback()
        logger.error(f"[CLEANUP] Failed to purge expired workspaces: {e}")
        raise
    finally:
        db.close()