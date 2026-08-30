"""
In-Process Asynchronous Background Crawler & Pruning Task Scheduler for GitScout.
Runs continuously inside the FastAPI lifespan process, executing periodic scrapes and auto-pruning.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from app.config import settings
from app.database import async_session_maker
from app.dispatcher.base import AlertPayload
from app.dispatcher.router import notification_router
from app.scrapers.orchestrator import ScraperOrchestrator

logger = logging.getLogger("gitscout.scheduler")


class BackgroundTaskScheduler:
    """Manages periodic async scraping and closed-issue pruning inside FastAPI."""

    def __init__(self, interval_seconds: int = 1800):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start the background scheduler task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop(), name="gitscout_background_crawler")
        logger.info(f"[OK] Background crawler scheduler started (interval: {self.interval_seconds // 60} minutes).")

    async def stop(self) -> None:
        """Cancel and await graceful termination of the scheduler."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[OK] Background crawler scheduler stopped gracefully.")

    async def _scheduler_loop(self) -> None:
        """Continuous execution loop."""
        # Initial sleep of 10 seconds to allow clean app startup
        await asyncio.sleep(10)

        while self._running:
            logger.info(f"[*] [SCHEDULER RUN] Starting periodic scrape & pruning cycle at {datetime.now(timezone.utc)} UTC...")
            try:
                async with async_session_maker() as session:
                    orchestrator = ScraperOrchestrator()
                    
                    # 1. Scrape newly opened issues and bounties
                    scrape_result = await orchestrator.scrape_and_index_all(
                        session=session,
                        limit_per_repo=settings.DEFAULT_REPO_LIMIT,
                        include_bounty_search=True,
                    )
                    logger.info(
                        f"[*] [SCHEDULER] Harvested {scrape_result['indexed_count']} issues "
                        f"({scrape_result['bounties_found']} bounties)."
                    )

                    # 2. Prune closed, fixed, or assigned issues
                    pruned_count = await orchestrator.prune_closed_issues(session)
                    logger.info(f"[*] [SCHEDULER] Pruned {pruned_count} closed/fixed issues from database.")

            except Exception as exc:
                logger.error(f"[ERROR] [SCHEDULER] Error during periodic cycle: {exc}", exc_info=True)

            logger.info(f"[*] [SCHEDULER] Cycle complete. Sleeping for {self.interval_seconds // 60} minutes...")
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break


background_scheduler = BackgroundTaskScheduler(
    interval_seconds=getattr(settings, "SCRAPE_INTERVAL_MINUTES", 30) * 60
)
