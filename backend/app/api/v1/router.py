"""Unified API v1 Router."""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.issues import router as issues_router
from app.api.v1.triage import router as triage_router
from app.api.v1.bounties import router as bounties_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.billing import router as billing_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(issues_router)
api_router.include_router(triage_router)
api_router.include_router(bounties_router)
api_router.include_router(notifications_router)
api_router.include_router(billing_router)
