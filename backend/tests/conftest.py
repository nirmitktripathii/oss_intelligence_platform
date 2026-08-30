"""Pytest configuration and async fixtures for GitScout backend tests."""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.database import Base, get_db
from app.main import create_app
from app.models.billing import BillingSubscription
from app.models.issue import Issue
from app.models.subscription import NotificationSubscription
from app.models.triage import TriageReport

# Use an in-memory SQLite database for hermetic fast testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine: AsyncEngine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a clean database session for each test function."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async HTTP test client with database dependency override."""
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def seed_sample_issues(db_session: AsyncSession) -> None:
    """Seed realistic test issues across multiple domains."""
    sample_issues = [
        Issue(
            id="fastapi/fastapi#1001",
            repo_owner="fastapi",
            repo_name="fastapi",
            issue_number=1001,
            title="Async generator dependency cleanup failure in BackgroundTasks",
            body="When using BackgroundTasks with async generator dependencies, the cleanup block is not awaited.\n\nTraceback (most recent call last):\n  File \"fastapi/dependencies/utils.py\", line 245, in solve_dependencies\n    await cm.__aexit__()",
            html_url="https://github.com/fastapi/fastapi/issues/1001",
            author="tiangolo",
            domain="Web",
            tech_stack=["Python", "FastAPI", "AsyncIO", "Starlette"],
            difficulty="Medium",
            estimated_hours=2.5,
            has_bounty=True,
            bounty_amount_usd=250.0,
            bounty_source="Polar",
            bounty_url="https://polar.sh/fastapi/fastapi/issues/1001",
            hourly_roi=100.0,
            state="open",
            comments_count=4,
            labels=[{"name": "bug", "color": "d73a4a"}, {"name": "bounty: $250", "color": "008672"}],
            github_created_at=datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc),
            github_updated_at=datetime(2026, 8, 2, 14, 0, 0, tzinfo=timezone.utc),
            indexed_at=datetime.now(timezone.utc),
        ),
        Issue(
            id="langchain-ai/langchain#2002",
            repo_owner="langchain-ai",
            repo_name="langchain",
            issue_number=2002,
            title="ChatPromptTemplate variable substitution fails on None values",
            body="Passing None in variables dict raises AttributeError instead of rendering empty string.\n\n```python\nprompt = ChatPromptTemplate.from_template('Hello {name}')\nprompt.format_messages(name=None)\n```",
            html_url="https://github.com/langchain-ai/langchain/issues/2002",
            author="hwchase17",
            domain="AI/ML",
            tech_stack=["Python", "LangChain", "LLM", "Prompt"],
            difficulty="Easy",
            estimated_hours=0.75,
            has_bounty=False,
            bounty_amount_usd=None,
            bounty_source=None,
            bounty_url=None,
            hourly_roi=None,
            state="open",
            comments_count=2,
            labels=[{"name": "good first issue", "color": "7057ff"}],
            github_created_at=datetime(2026, 8, 5, 10, 0, 0, tzinfo=timezone.utc),
            github_updated_at=datetime(2026, 8, 6, 11, 0, 0, tzinfo=timezone.utc),
            indexed_at=datetime.now(timezone.utc),
        ),
        Issue(
            id="pola-rs/polars#3003",
            repo_owner="pola-rs",
            repo_name="polars",
            issue_number=3003,
            title="Panic on parallel join with duplicate null keys in streaming mode",
            body="When performing an outer join on large streaming dataframes, a thread panics at polars-core/src/frame/join.rs:412.",
            html_url="https://github.com/pola-rs/polars/issues/3003",
            author="ritchie46",
            domain="Data",
            tech_stack=["Rust", "Polars", "DataFrames", "OLAP"],
            difficulty="Hard",
            estimated_hours=8.0,
            has_bounty=True,
            bounty_amount_usd=500.0,
            bounty_source="Algora",
            bounty_url="https://algora.io/bounties/3003",
            hourly_roi=62.5,
            state="open",
            comments_count=7,
            labels=[{"name": "bug", "color": "d73a4a"}, {"name": "algora", "color": "0052cc"}],
            github_created_at=datetime(2026, 8, 10, 8, 0, 0, tzinfo=timezone.utc),
            github_updated_at=datetime(2026, 8, 11, 9, 0, 0, tzinfo=timezone.utc),
            indexed_at=datetime.now(timezone.utc),
        ),
        Issue(
            id="kubernetes/kubernetes#4004",
            repo_owner="kubernetes",
            repo_name="kubernetes",
            issue_number=4004,
            title="Kubelet fails to unmount CSI volume when pod terminates abruptly",
            body="Goroutine trace:\n  pkg/kubelet/volumemanager/reconciler/reconciler.go:189",
            html_url="https://github.com/kubernetes/kubernetes/issues/4004",
            author="k8s-maintainer",
            domain="Cloud/DevOps",
            tech_stack=["Go", "Kubernetes", "Containers"],
            difficulty="Medium",
            estimated_hours=3.0,
            has_bounty=False,
            state="open",
            comments_count=1,
            labels=[{"name": "sig/storage", "color": "ededed"}],
            github_created_at=datetime(2026, 8, 12, 15, 0, 0, tzinfo=timezone.utc),
            github_updated_at=datetime(2026, 8, 13, 16, 0, 0, tzinfo=timezone.utc),
            indexed_at=datetime.now(timezone.utc),
        ),
    ]

    for issue in sample_issues:
        db_session.add(issue)

    # Seed a triage report for the first issue
    triage = TriageReport(
        issue_id="fastapi/fastapi#1001",
        summary="Automated AI Triage for #1001 in fastapi/fastapi",
        root_cause_analysis="Async generator dependency cleanup context manager is bypassed when BackgroundTasks execution fails.",
        localized_files=[
            {
                "file_path": "fastapi/dependencies/utils.py",
                "line_range": "240-260",
                "confidence": 0.94,
                "rationale": "Direct traceback match in solve_dependencies",
            }
        ],
        reproduction_code="# Repro code\nimport asyncio\nprint('repro')",
        reproduction_lang="python",
        reproduction_instructions="Run python repro.py",
        fix_plan_steps=[
            {
                "step_number": 1,
                "title": "Branch Setup",
                "description": "git checkout -b fix/issue-1001",
                "code_snippet": "git checkout -b fix/1001",
                "verification_command": "git branch",
            }
        ],
        contributing_guidelines_summary="Standard contribution rules.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(triage)

    # Seed a subscription
    sub = NotificationSubscription(
        channel="telegram",
        destination="123456789",
        domains=["AI/ML", "Web"],
        min_bounty=50.0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(sub)

    # Seed a billing subscription
    bill_sub = BillingSubscription(
        customer_email="pro_user@example.com",
        plan_id="pro_monthly",
        provider="dodopayments",
        provider_subscription_id="sub_test_123",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(bill_sub)

    await db_session.commit()
