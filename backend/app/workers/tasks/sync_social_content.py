"""Periodic task: auto-publish social content for due automations."""

import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_due_social_content_async() -> int:
    from app.db.session import async_session_factory
    from app.modules.marketing.service import run_due_social_automations

    async with async_session_factory() as session:
        count = await run_due_social_automations(session)
        await session.commit()
        return count


@celery_app.task(
    name="app.workers.tasks.sync_social_content.sync_social_content",
    bind=True,
    max_retries=1,
)
def sync_social_content(self):
    logger.info("Running due social automations...")
    try:
        done = asyncio.run(_run_due_social_content_async())
        logger.info("Social automation cycle complete. published=%d", done)
    except Exception as exc:
        logger.error("Social automation cycle failed: %s", exc)
        raise self.retry(exc=exc, countdown=120)
