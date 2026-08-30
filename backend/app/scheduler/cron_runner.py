"""
Standalone CLI Cron Runner for GitScout.
Can be triggered directly by external cron schedulers (Render Cron, Linux crontab, Windows Task Scheduler, GitHub Actions).
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from app.database import async_session_maker, close_db, init_db
from app.scrapers.orchestrator import ScraperOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [CRON]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("cron_runner")


async def run_cron(limit_per_repo: int = 8, prune: bool = True):
    """Execute a single complete harvest and pruning pass."""
    start_time = datetime.now(timezone.utc)
    logger.info(f"[*] Starting GitScout Cron Job at {start_time.isoformat()}...")
    
    await init_db()
    
    async with async_session_maker() as session:
        orchestrator = ScraperOrchestrator()
        
        # 1. Harvest latest open issues & bounties
        logger.info(f"[*] Step 1: Crawling new open issues & bounties (limit: {limit_per_repo}/repo)...")
        scrape_result = await orchestrator.scrape_and_index_all(
            session=session,
            limit_per_repo=limit_per_repo,
            include_bounty_search=True,
        )
        logger.info(
            f"[OK] Harvested: indexed={scrape_result['indexed_count']}, "
            f"bounties={scrape_result['bounties_found']}, "
            f"repos={scrape_result['repos_scraped']}"
        )
        
        # 2. Prune closed/fixed issues
        if prune:
            logger.info("[*] Step 2: Checking database for closed or merged issues to prune...")
            pruned_count = await orchestrator.prune_closed_issues(session)
            logger.info(f"[OK] Pruning complete: removed {pruned_count} closed issues.")

    await close_db()
    
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(f"[SUCCESS] GitScout Cron Execution completed cleanly in {duration:.2f} seconds.")


def main():
    parser = argparse.ArgumentParser(description="GitScout Standalone Cron Runner")
    parser.add_argument("--limit-per-repo", type=int, default=8, help="Max issues to fetch per repository")
    parser.add_argument("--no-prune", action="store_true", help="Skip closed issue pruning")
    args = parser.parse_args()

    asyncio.run(run_cron(limit_per_repo=args.limit_per_repo, prune=not args.no_prune))


if __name__ == "__main__":
    main()
