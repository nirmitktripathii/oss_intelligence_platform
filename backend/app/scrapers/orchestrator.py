"""Live Scraper Orchestrator populating database with real, live, open unassigned GitHub issues."""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import async_session_maker, init_db
from app.models.issue import Issue
from app.models.triage import TriageReport
from app.scrapers.bounty_extractor import BountyExtractor
from app.scrapers.classifier import IssueClassifier
from app.scrapers.domain_registry import DOMAIN_REGISTRY, get_repo_by_fullname
from app.scrapers.github_client import GitHubClient
from app.triage.ast_localizer import ASTLocalizer
from app.triage.fix_planner import FixPlanner
from app.triage.repro_generator import ReproGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def parse_datetime(dt_str: Optional[str]) -> datetime:
    """Parse ISO 8601 string to timezone-aware UTC datetime."""
    if not dt_str:
        return datetime.now(timezone.utc)
    try:
        # Handle 'Z' suffix
        cleaned = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except Exception:
        return datetime.now(timezone.utc)


class ScraperOrchestrator:
    """Orchestrates live harvesting, classification, triage, and database upsert."""

    def __init__(self, client: Optional[GitHubClient] = None):
        self.client = client or GitHubClient()

    async def scrape_and_index_all(
        self,
        session: AsyncSession,
        limit_per_repo: int = 5,
        include_bounty_search: bool = True,
    ) -> Dict[str, Any]:
        """
        Harvest live open unassigned issues across curated domain repositories and global bounty search.
        Strict verification: zero mock data, genuine live GitHub issues.
        """
        indexed_count = 0
        bounties_found = 0
        repos_scraped = 0
        errors = []

        logger.info(f"[*] Starting live scrape across {len(DOMAIN_REGISTRY)} domain repositories...")

        # 1. Scrape curated registry repos
        for repo_target in DOMAIN_REGISTRY:
            try:
                raw_issues = await self.client.fetch_repo_issues(
                    owner=repo_target.owner,
                    repo=repo_target.repo,
                    per_page=limit_per_repo,
                )
                repos_scraped += 1

                for raw_item in raw_issues:
                    issue_obj, triage_obj = await self._process_raw_issue(raw_item, repo_target.full_name)
                    if issue_obj:
                        await self._upsert_issue_and_triage(session, issue_obj, triage_obj)
                        indexed_count += 1
                        if issue_obj.has_bounty:
                            bounties_found += 1

            except Exception as exc:
                err_msg = f"Error scraping {repo_target.full_name}: {exc}"
                logger.error(f"[ERROR] {err_msg}")
                errors.append(err_msg)

        # 2. Global Bounty Search to discover high-value bounties
        if include_bounty_search:
            try:
                logger.info("[*] Running global bounty search across GitHub...")
                bounty_items = await self.client.search_bounty_issues(per_page=30)
                for raw_item in bounty_items:
                    # Extract repository full name from html_url
                    html_url = raw_item.get("html_url", "")
                    repo_fullname = ""
                    if "github.com/" in html_url:
                        parts = html_url.split("github.com/")[-1].split("/")
                        if len(parts) >= 2:
                            repo_fullname = f"{parts[0]}/{parts[1]}"

                    issue_obj, triage_obj = await self._process_raw_issue(raw_item, repo_fullname)
                    if issue_obj:
                        await self._upsert_issue_and_triage(session, issue_obj, triage_obj)
                        indexed_count += 1
                        if issue_obj.has_bounty:
                            bounties_found += 1

            except Exception as exc:
                err_msg = f"Error in bounty search: {exc}"
                logger.error(f"[ERROR] {err_msg}")
                errors.append(err_msg)

        await session.commit()
        logger.info(
            f"[OK] Scraping complete: indexed={indexed_count}, bounties={bounties_found}, "
            f"repos={repos_scraped}, errors={len(errors)}"
        )

        return {
            "indexed_count": indexed_count,
            "bounties_found": bounties_found,
            "repos_scraped": repos_scraped,
            "errors": errors,
        }

    async def _process_raw_issue(
        self,
        raw_item: Dict[str, Any],
        repo_fullname: str,
    ) -> Tuple[Optional[Issue], Optional[TriageReport]]:
        """Process a raw GitHub issue dictionary into validated ORM models."""
        # Verification filter
        if raw_item.get("pull_request") is not None:
            return None, None
        if raw_item.get("state") != "open":
            return None, None
        if raw_item.get("assignee") is not None or len(raw_item.get("assignees", [])) > 0:
            return None, None

        issue_number = raw_item.get("number")
        if not issue_number:
            return None, None

        # Parse owner and repo name
        if not repo_fullname:
            html_url = raw_item.get("html_url", "")
            if "github.com/" in html_url:
                parts = html_url.split("github.com/")[-1].split("/")
                if len(parts) >= 2:
                    repo_fullname = f"{parts[0]}/{parts[1]}"
            else:
                return None, None

        parts = repo_fullname.split("/")
        owner = parts[0]
        repo_name = parts[1] if len(parts) > 1 else parts[0]

        issue_id = f"{owner}/{repo_name}#{issue_number}"
        title = raw_item.get("title", "").strip()
        body = raw_item.get("body") or ""
        html_url = raw_item.get("html_url") or f"https://github.com/{owner}/{repo_name}/issues/{issue_number}"
        author = raw_item.get("user", {}).get("login", "unknown") if raw_item.get("user") else "unknown"
        comments_count = raw_item.get("comments", 0)
        labels = raw_item.get("labels", [])

        repo_target = get_repo_by_fullname(repo_fullname)
        domain = repo_target.domain.value if hasattr(repo_target.domain, "value") else str(repo_target.domain)

        # 1. Bounty Extraction
        has_bounty, bounty_amount, bounty_source, bounty_url = BountyExtractor.parse_issue(
            title=title,
            body=body,
            labels=labels,
            html_url=html_url,
        )

        # 2. Classification
        tech_stack = IssueClassifier.classify_tech_stack(repo_target, title, body, labels)
        difficulty = IssueClassifier.classify_difficulty(labels, title, body)
        estimated_hours = IssueClassifier.estimate_hours(difficulty, body, labels)
        hourly_roi = IssueClassifier.calculate_hourly_roi(bounty_amount, estimated_hours)

        github_created = parse_datetime(raw_item.get("created_at"))
        github_updated = parse_datetime(raw_item.get("updated_at"))

        issue_model = Issue(
            id=issue_id,
            repo_owner=owner,
            repo_name=repo_name,
            issue_number=issue_number,
            title=title,
            body=body,
            html_url=html_url,
            author=author,
            domain=domain,
            tech_stack=tech_stack,
            difficulty=difficulty.value if hasattr(difficulty, "value") else str(difficulty),
            estimated_hours=estimated_hours,
            has_bounty=has_bounty,
            bounty_amount_usd=bounty_amount,
            bounty_source=bounty_source,
            bounty_url=bounty_url,
            hourly_roi=hourly_roi,
            state="open",
            comments_count=comments_count,
            labels=labels,
            github_created_at=github_created,
            github_updated_at=github_updated,
            indexed_at=datetime.now(timezone.utc),
        )

        # 3. AI Triage & Localization
        localized_files, root_cause = ASTLocalizer.localize(owner, repo_name, title, body)
        repro_code, repro_lang, repro_inst = ReproGenerator.generate(
            owner, repo_name, title, body, repo_target.primary_language
        )
        fix_steps, contrib_summary = FixPlanner.generate_plan(
            owner, repo_name, issue_number, title, localized_files
        )

        triage_model = TriageReport(
            issue_id=issue_id,
            summary=f"Automated AI Triage for #{issue_number} in {owner}/{repo_name}: {title}",
            root_cause_analysis=root_cause,
            localized_files=[f.model_dump() for f in localized_files],
            reproduction_code=repro_code,
            reproduction_lang=repro_lang,
            reproduction_instructions=repro_inst,
            fix_plan_steps=[s.model_dump() for s in fix_steps],
            contributing_guidelines_summary=contrib_summary,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        return issue_model, triage_model

    async def _upsert_issue_and_triage(
        self,
        session: AsyncSession,
        issue_obj: Issue,
        triage_obj: Optional[TriageReport],
    ) -> None:
        """Upsert issue and triage records into the database."""
        # Check existing issue
        stmt = select(Issue).where(Issue.id == issue_obj.id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update fields
            existing.title = issue_obj.title
            existing.body = issue_obj.body
            existing.tech_stack = issue_obj.tech_stack
            existing.difficulty = issue_obj.difficulty
            existing.estimated_hours = issue_obj.estimated_hours
            existing.has_bounty = issue_obj.has_bounty
            existing.bounty_amount_usd = issue_obj.bounty_amount_usd
            existing.bounty_source = issue_obj.bounty_source
            existing.bounty_url = issue_obj.bounty_url
            existing.hourly_roi = issue_obj.hourly_roi
            existing.comments_count = issue_obj.comments_count
            existing.labels = issue_obj.labels
            existing.github_updated_at = issue_obj.github_updated_at
            existing.indexed_at = datetime.now(timezone.utc)
        else:
            session.add(issue_obj)

        if triage_obj:
            triage_stmt = select(TriageReport).where(TriageReport.issue_id == issue_obj.id)
            triage_res = await session.execute(triage_stmt)
            existing_triage = triage_res.scalar_one_or_none()
            if existing_triage:
                existing_triage.summary = triage_obj.summary
                existing_triage.root_cause_analysis = triage_obj.root_cause_analysis
                existing_triage.localized_files = triage_obj.localized_files
                existing_triage.reproduction_code = triage_obj.reproduction_code
                existing_triage.reproduction_instructions = triage_obj.reproduction_instructions
                existing_triage.fix_plan_steps = triage_obj.fix_plan_steps
                existing_triage.contributing_guidelines_summary = triage_obj.contributing_guidelines_summary
                existing_triage.updated_at = datetime.now(timezone.utc)
            else:
                session.add(triage_obj)

    async def prune_closed_issues(self, session: AsyncSession) -> int:
        """
        Verify all tracked issues in the database against live GitHub status.
        If an issue is fixed, closed, merged, assigned, or deleted, purge it from the database.
        """
        import httpx
        logger.info("[*] Checking for closed, assigned, or fixed issues to prune...")
        stmt = select(Issue)
        res = await session.execute(stmt)
        all_issues = res.scalars().all()

        pruned_count = 0
        headers = self.client._build_headers()

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for iss in all_issues:
                try:
                    url = f"{self.client.base_url}/repos/{iss.repo_owner}/{iss.repo_name}/issues/{iss.issue_number}"
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 404:
                        await session.delete(iss)
                        pruned_count += 1
                        logger.info(f"[PRUNED] Purged 404 deleted issue: {iss.id}")
                    elif resp.status_code == 200:
                        data = resp.json()
                        if (
                            data.get("state") != "open"
                            or data.get("pull_request") is not None
                            or data.get("assignee") is not None
                            or len(data.get("assignees", [])) > 0
                        ):
                            await session.delete(iss)
                            pruned_count += 1
                            logger.info(f"[PRUNED] Purged closed/assigned issue: {iss.id} (state={data.get('state')})")
                except Exception as exc:
                    logger.error(f"Error checking issue {iss.id} for pruning: {exc}")

        if pruned_count > 0:
            await session.commit()
        logger.info(f"[OK] Pruning complete: purged {pruned_count} closed or stale issues.")
        return pruned_count


async def main():
    parser = argparse.ArgumentParser(description="GitScout Live Issue Scraper Runner")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode without committing to DB")
    parser.add_argument("--seed-live", action="store_true", help="Harvest and seed database with live issues")
    parser.add_argument("--limit-per-repo", type=int, default=4, help="Max issues to fetch per repository")
    parser.add_argument("--prune-closed", action="store_true", help="Verify and delete all closed/fixed issues from DB")
    args = parser.parse_args()

    print("[*] Initializing GitScout Database...")
    await init_db()

    orchestrator = ScraperOrchestrator()
    async with async_session_maker() as session:
        if args.prune_closed:
            pruned = await orchestrator.prune_closed_issues(session)
            print(f"[OK] Pruned {pruned} closed/stale issues from database.")
        else:
            result = await orchestrator.scrape_and_index_all(
                session=session,
                limit_per_repo=args.limit_per_repo,
                include_bounty_search=True,
            )
            print(f"[OK] Finished: Indexed {result['indexed_count']} issues with {result['bounties_found']} funded bounties.")


if __name__ == "__main__":
    asyncio.run(main())
