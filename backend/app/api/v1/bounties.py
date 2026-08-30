"""Funded bounties aggregation and ROI leaderboards endpoint."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.issue import Issue
from app.schemas.bounty import BountyListResponse, BountyResponse
from app.schemas.issue import IssueDomain

router = APIRouter(tags=["Bounties & ROI"])


@router.get("/bounties", response_model=BountyListResponse, summary="List Funded Bounties & ROI Rankings")
async def list_bounties(
    min_amount: Optional[float] = Query(0.0, ge=0.0, description="Minimum bounty USD threshold"),
    domain: Optional[IssueDomain] = Query(None, description="Filter by domain"),
    sort_by: Optional[str] = Query("hourly_roi", description="Sort by: hourly_roi, amount_desc, newest"),
    limit: int = Query(50, ge=1, le=100, description="Limit results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve open funded bounties across Polar, Algora, and GitHub Sponsors ranked by Hourly ROI ($/hr).
    """
    query = select(Issue).where(
        Issue.state == "open",
        Issue.has_bounty.is_(True),
        Issue.bounty_amount_usd >= (min_amount or 0.0),
    )

    if domain:
        query = query.where(Issue.domain == domain.value)

    if sort_by == "amount_desc":
        query = query.order_by(desc(Issue.bounty_amount_usd))
    elif sort_by == "newest":
        query = query.order_by(desc(Issue.github_created_at))
    else:  # "hourly_roi" default
        query = query.order_by(desc(Issue.hourly_roi), desc(Issue.bounty_amount_usd))

    query = query.limit(limit)
    result = await db.execute(query)
    bounty_issues = result.scalars().all()

    items = []
    total_usd = 0.0
    total_roi = 0.0

    for issue in bounty_issues:
        amount = issue.bounty_amount_usd or 0.0
        roi = issue.hourly_roi or (amount / issue.estimated_hours if issue.estimated_hours > 0 else 0.0)
        total_usd += amount
        total_roi += roi

        items.append(
            BountyResponse(
                issue_id=issue.id,
                repo_owner=issue.repo_owner,
                repo_name=issue.repo_name,
                issue_number=issue.issue_number,
                title=issue.title,
                html_url=issue.html_url,
                domain=issue.domain,
                tech_stack=issue.tech_stack or [],
                difficulty=issue.difficulty,
                estimated_hours=issue.estimated_hours,
                bounty_amount_usd=amount,
                bounty_source=issue.bounty_source or "GitScout Index",
                bounty_url=issue.bounty_url or issue.html_url,
                hourly_roi=roi,
                github_created_at=issue.github_created_at,
            )
        )

    avg_roi = round(total_roi / len(items), 2) if items else 0.0

    return BountyListResponse(
        items=items,
        total=len(items),
        total_bounty_usd=round(total_usd, 2),
        average_hourly_roi=avg_roi,
    )
