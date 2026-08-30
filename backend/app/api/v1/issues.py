"""Issues search, filtering, and retrieval endpoints."""

import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.issue import Issue
from app.schemas.issue import (
    IssueDifficulty,
    IssueDomain,
    IssueResponse,
    PaginatedIssuesResponse,
)

router = APIRouter(tags=["Issues"])


@router.get("/issues", response_model=PaginatedIssuesResponse, summary="List & Search Open Issues")
async def list_issues(
    domain: Optional[IssueDomain] = Query(None, description="Filter by engineering domain"),
    difficulty: Optional[IssueDifficulty] = Query(None, description="Filter by difficulty tier"),
    tech_stack: Optional[str] = Query(None, description="Filter by tech stack tag (e.g. 'Python', 'React')"),
    has_bounty: Optional[bool] = Query(None, description="Filter for issues with funded bounties"),
    min_bounty: Optional[float] = Query(None, ge=0.0, description="Minimum bounty USD amount"),
    search: Optional[str] = Query(None, description="Keyword search in title, body, and repository name"),
    sort_by: Optional[str] = Query(
        "newest",
        description="Sort by: newest, oldest, hourly_roi, bounty_desc, comments",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search and filter live open unassigned GitHub issues indexed across 6 domains.
    """
    query = select(Issue).where(Issue.state == "open")

    # Domain filter
    if domain:
        query = query.where(Issue.domain == domain.value)

    # Difficulty filter
    if difficulty:
        query = query.where(Issue.difficulty == difficulty.value)

    # Bounty filter
    if has_bounty is not None:
        query = query.where(Issue.has_bounty == has_bounty)

    if min_bounty is not None and min_bounty > 0:
        query = query.where(Issue.bounty_amount_usd >= min_bounty)

    # Search keyword
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Issue.title.ilike(term),
                Issue.body.ilike(term),
                Issue.repo_owner.ilike(term),
                Issue.repo_name.ilike(term),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sorting
    if sort_by == "oldest":
        query = query.order_by(Issue.github_created_at.asc())
    elif sort_by == "hourly_roi":
        query = query.order_by(desc(Issue.hourly_roi), desc(Issue.bounty_amount_usd))
    elif sort_by == "bounty_desc":
        query = query.order_by(desc(Issue.bounty_amount_usd))
    elif sort_by == "comments":
        query = query.order_by(desc(Issue.comments_count))
    else:  # "newest" default
        query = query.order_by(desc(Issue.github_created_at))

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    issues = result.scalars().all()

    # Filter tech_stack in Python if specified (for JSON list column compatibility across DBs)
    if tech_stack:
        ts_lower = tech_stack.lower()
        filtered = [
            i for i in issues if any(ts_lower in s.lower() for s in (i.tech_stack or []))
        ]
        issues = filtered

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedIssuesResponse(
        items=[IssueResponse.model_validate(i.to_dict()) for i in issues],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/issues/{issue_id:path}", response_model=IssueResponse, summary="Get Issue by ID")
async def get_issue(issue_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve single issue by its composite ID (e.g. `fastapi/fastapi#12345`).
    """
    stmt = select(Issue).where(Issue.id == issue_id)
    result = await db.execute(stmt)
    issue = result.scalar_one_or_none()

    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found.")

    return IssueResponse.model_validate(issue.to_dict())


@router.post("/issues/prune", summary="Prune Closed & Assigned Issues")
async def prune_issues(db: AsyncSession = Depends(get_db)):
    """
    Scans the database and removes any issues that have been closed, merged, or assigned upstream.
    """
    from app.scrapers.orchestrator import ScraperOrchestrator
    orchestrator = ScraperOrchestrator()
    pruned_count = await orchestrator.prune_closed_issues(db)
    return {"status": "success", "pruned_count": pruned_count}

