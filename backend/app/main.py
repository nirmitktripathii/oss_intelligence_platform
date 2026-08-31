"""FastAPI Main Application Entrypoint for GitScout / OSS Terminal."""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from app.api.v1.router import api_router
from app.config import settings
from app.database import close_db, init_db
from app.security.headers import SecurityHeadersMiddleware
from app.security.rate_limiter import custom_rate_limit_exceeded_handler, limiter

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gitscout")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context managing database schema creation, background crawler, and shutdown."""
    logger.info("[*] Starting GitScout backend service...")
    await init_db()
    logger.info("[OK] Database initialized successfully.")

    if settings.ENABLE_BACKGROUND_CRAWLER:
        from app.scheduler.task_scheduler import background_scheduler
        background_scheduler.start()

    yield

    if settings.ENABLE_BACKGROUND_CRAWLER:
        from app.scheduler.task_scheduler import background_scheduler
        await background_scheduler.stop()

    logger.info("[*] Shutting down GitScout backend service...")
    await close_db()
    logger.info("[OK] Database connection pool closed.")


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    application = FastAPI(
        title=f"⚡ {settings.PROJECT_NAME} API Terminal",
        version=settings.VERSION,
        description="""
### 🌐 GitScout / OSS Terminal Backend API
High-Throughput Open-Source Issue Intelligence, Triage & Contribution Web Platform.

* **Live Issues Stream**: Zero-mock filtered GitHub & bounty data.
* **AI Triage & Localization**: AST file prediction & reproduction generator.
* **Multi-Channel Dispatch**: Telegram, Discord, Resend Email, and WhatsApp.
* **Micro-SaaS Billing**: Dodo Payments & Lemon Squeezy integration.
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        swagger_ui_parameters={
            "syntaxHighlight.theme": "monokai",
            "docExpansion": "list",
            "defaultModelsExpandDepth": 2,
            "displayRequestDuration": True,
            "filter": True,
        },
        lifespan=lifespan,
    )

    # Attach SlowAPI Rate Limiter state
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

    # 1. OWASP Security Headers Middleware
    application.add_middleware(SecurityHeadersMiddleware)

    # 2. CORS Middleware (Supports all Vercel domains, previews, and vercel.live)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=86400,
    )

    # 3. Mount API v1 Router
    application.include_router(api_router, prefix=settings.API_V1_STR)

    # 4. Root Welcome / Telemetry Route
    @application.get("/", tags=["Root"])
    async def root_index():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "operational",
            "docs": "/docs",
            "api_v1": settings.API_V1_STR,
        }

    # 5. Global Exception Handler
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while processing the request.",
            },
        )

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
