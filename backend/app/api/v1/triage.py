"""AI Triage, AST File Localization & Reproduction endpoints."""

import hashlib
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.issue import Issue
from app.models.triage import TriageReport
from app.schemas.triage import TriageResponse
from app.triage.ast_localizer import ASTLocalizer
from app.triage.enhancer import compute_triage_confidence, derive_language, semantic_enhance
from app.triage.fix_planner import FixPlanner
from app.triage.llm_engine import LLMTriageEngine
from app.triage.repro_generator import ReproGenerator

router = APIRouter(tags=["Triage & Diagnostics"])


class OnDemandTriageRequest(BaseModel):
    repo_owner: str = Field(..., example="fastapi")
    repo_name: str = Field(..., example="fastapi")
    issue_number: int = Field(1, example=101)
    title: str = Field(..., example="TypeError when parsing nested JSON body with None values")
    body: Optional[str] = Field("", example="Traceback (most recent call last):\n  File \"fastapi/routing.py\", line 150, in get_request_handler\n    result = parse_body(body)")
    primary_language: str = Field("Python", example="Python")


@router.get("/triage/{issue_id:path}", response_model=TriageResponse, summary="Get Issue AI Triage & Localization")
async def get_triage(issue_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve AI triage report, localized files, reproduction script, and fix plan for an issue.
    If triage has not been generated yet, automatically generates and persists it.
    """
    # Eager-load the parent issue so we can surface its optional body_summary without a
    # lazy relationship load (which would fire outside the greenlet and raise MissingGreenlet).
    stmt = (
        select(TriageReport)
        .where(TriageReport.issue_id == issue_id)
        .options(selectinload(TriageReport.issue))
    )
    result = await db.execute(stmt)
    triage = result.scalar_one_or_none()

    if triage:
        # Lazy self-heal: a report persisted before a working LLM provider was configured is
        # frozen AST-only (llm_enhanced=False) and would otherwise show "0% / Deterministic"
        # forever, because this row is returned verbatim on every read. If a provider is now
        # available, attempt one enrichment and persist the upgrade; on a miss we simply return
        # the AST floor unchanged (never fabricated).
        if not triage.llm_enhanced and triage.issue is not None and LLMTriageEngine.resolve_chain():
            issue = triage.issue
            localized_dicts = triage.localized_files or []
            enrichment = await semantic_enhance(
                cache_key=f"gitscout:triage:llm:{issue.id}",
                repo_owner=issue.repo_owner,
                repo_name=issue.repo_name,
                issue_number=issue.issue_number,
                title=issue.title,
                body=issue.body,
                body_summary=issue.body_summary,
                language=derive_language(issue.tech_stack, issue.domain),
                tech_stack=issue.tech_stack or [],
                localized_files=localized_dicts,
            )
            if enrichment is not None:
                triage.llm_enhanced = True
                triage.llm_analysis = enrichment
                triage.triage_confidence = compute_triage_confidence(enrichment, localized_dicts)
                triage.updated_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(triage)

        payload = triage.to_dict()
        payload["body_summary"] = triage.issue.body_summary if triage.issue else None
        return TriageResponse.model_validate(payload)

    # Fallback: check if issue exists to generate triage dynamically
    issue_stmt = select(Issue).where(Issue.id == issue_id)
    issue_res = await db.execute(issue_stmt)
    issue = issue_res.scalar_one_or_none()

    if not issue:
        raise HTTPException(status_code=404, detail=f"Triage report or issue '{issue_id}' not found.")

    # 1. Deterministic AST floor (always runs, free).
    localized_files, root_cause = ASTLocalizer.localize(
        issue.repo_owner, issue.repo_name, issue.title, issue.body
    )
    repro_code, repro_lang, repro_inst = ReproGenerator.generate(
        issue.repo_owner, issue.repo_name, issue.title, issue.body
    )
    fix_steps, contrib_summary = FixPlanner.generate_plan(
        issue.repo_owner, issue.repo_name, issue.issue_number, issue.title, localized_files
    )
    localized_dicts = [f.model_dump() for f in localized_files]

    # 2. Optional AI enhancement layer. Returns None (AST-only) when no provider is
    #    configured or the model returns nothing usable — never fabricates.
    enrichment = await semantic_enhance(
        cache_key=f"gitscout:triage:llm:{issue.id}",
        repo_owner=issue.repo_owner,
        repo_name=issue.repo_name,
        issue_number=issue.issue_number,
        title=issue.title,
        body=issue.body,
        body_summary=issue.body_summary,
        language=derive_language(issue.tech_stack, issue.domain),
        tech_stack=issue.tech_stack or [],
        localized_files=localized_dicts,
    )
    triage_confidence = compute_triage_confidence(enrichment, localized_dicts)

    triage_obj = TriageReport(
        issue_id=issue.id,
        summary=f"Automated AI Triage for #{issue.issue_number} in {issue.repo_owner}/{issue.repo_name}: {issue.title}",
        root_cause_analysis=root_cause,
        localized_files=localized_dicts,
        reproduction_code=repro_code,
        reproduction_lang=repro_lang,
        reproduction_instructions=repro_inst,
        fix_plan_steps=[s.model_dump() for s in fix_steps],
        contributing_guidelines_summary=contrib_summary,
        llm_enhanced=enrichment is not None,
        llm_analysis=enrichment,
        triage_confidence=triage_confidence,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(triage_obj)
    await db.commit()
    await db.refresh(triage_obj)

    payload = triage_obj.to_dict()
    payload["body_summary"] = issue.body_summary  # issue already loaded above
    return TriageResponse.model_validate(payload)


@router.post("/triage/generate", response_model=TriageResponse, summary="On-Demand AI Triage Generation")
async def generate_on_demand_triage(req: OnDemandTriageRequest):
    """
    Generate an AST localization, minimal reproduction snippet, and step-by-step fix blueprint for arbitrary issue text.
    """
    localized_files, root_cause = ASTLocalizer.localize(
        req.repo_owner, req.repo_name, req.title, req.body
    )
    repro_code, repro_lang, repro_inst = ReproGenerator.generate(
        req.repo_owner, req.repo_name, req.title, req.body, req.primary_language
    )
    fix_steps, contrib_summary = FixPlanner.generate_plan(
        req.repo_owner, req.repo_name, req.issue_number, req.title, localized_files
    )
    localized_dicts = [f.model_dump() for f in localized_files]

    # Cache the enrichment by content hash so identical ad-hoc requests reuse the quota.
    content_hash = hashlib.sha256(
        f"{req.repo_owner}/{req.repo_name}#{req.issue_number}|{req.title}|{req.body or ''}".encode("utf-8")
    ).hexdigest()[:16]
    enrichment = await semantic_enhance(
        cache_key=f"gitscout:triage:llm:ondemand:{content_hash}",
        repo_owner=req.repo_owner,
        repo_name=req.repo_name,
        issue_number=req.issue_number,
        title=req.title,
        body=req.body,
        language=req.primary_language or "Python",
        tech_stack=[req.primary_language] if req.primary_language else [],
        localized_files=localized_dicts,
    )
    triage_confidence = compute_triage_confidence(enrichment, localized_dicts)

    return TriageResponse(
        issue_id=f"{req.repo_owner}/{req.repo_name}#{req.issue_number}",
        summary=f"On-demand AI Triage for {req.repo_owner}/{req.repo_name}: {req.title}",
        root_cause_analysis=root_cause,
        localized_files=localized_files,
        reproduction_code=repro_code,
        reproduction_lang=repro_lang,
        reproduction_instructions=repro_inst,
        fix_plan_steps=fix_steps,
        contributing_guidelines_summary=contrib_summary,
        llm_enhanced=enrichment is not None,
        llm_analysis=enrichment,
        triage_confidence=triage_confidence,
        created_at=datetime.now(timezone.utc),
    )
