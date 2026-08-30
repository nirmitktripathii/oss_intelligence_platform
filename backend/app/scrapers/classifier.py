"""Tech stack tagger, difficulty scoring, time-to-solve estimation and hourly ROI calculator."""

import re
from typing import Any, Dict, List, Optional
from app.schemas.issue import IssueDifficulty
from app.scrapers.domain_registry import RepositoryTarget


# Keyword dictionaries for tech stack tagging
TECH_KEYWORDS = {
    "Python": ["python", "py", "pytest", "pydantic", "pip", "asyncio", "numpy"],
    "TypeScript": ["typescript", "ts", "tsx", "next.js", "nextjs", "trpc", "react"],
    "JavaScript": ["javascript", "js", "jsx", "node", "npm", "express"],
    "Rust": ["rust", "cargo", "tokio", "serde", "polars", "tauri"],
    "Go": ["golang", "goroutine", "k8s", "kubernetes", "docker", "helm"],
    "C++": ["c++", "cpp", "cmake", "cuda", "duckdb", "arrow"],
    "C": ["ansi c", "redis", "neovim", "malloc"],
    "FastAPI": ["fastapi", "starlette", "apiroute", "uvicorn"],
    "Flask": ["flask", "werkzeug", "jinja"],
    "React": ["react", "useeffect", "usestate", "jsx", "virtual dom"],
    "Next.js": ["next.js", "nextjs", "app router", "server components", "ssr"],
    "PyTorch": ["pytorch", "torch", "cuda", "tensor", "nn.module"],
    "LangChain": ["langchain", "llm", "rag", "prompt", "agent"],
    "Docker": ["docker", "container", "dockerfile", "moby"],
    "Kubernetes": ["kubernetes", "k8s", "pod", "deployment", "crd", "helm"],
    "Terraform": ["terraform", "hcl", "iac", "provider"],
    "SQL": ["sql", "postgres", "sqlite", "query", "select", "join"],
    "Security": ["vulnerability", "cve", "injection", "owasp", "secret", "auth", "token"],
}

# Label patterns for difficulty estimation
EASY_LABELS = {
    "good first issue",
    "good-first-issue",
    "beginner",
    "beginner-friendly",
    "easy",
    "starter",
    "documentation",
    "docs",
    "typo",
    "quick-fix",
    "help wanted: beginner",
    "level: easy",
    "exp: beginner",
    "first-timers-only",
    "e-easy",
}

HARD_LABELS = {
    "hard",
    "complex",
    "architecture",
    "rfc",
    "performance",
    "memory-leak",
    "concurrency",
    "breaking change",
    "level: hard",
    "advanced",
    "critical",
    "security",
    "optimization",
    "redesign",
    "e-hard",
}


class IssueClassifier:
    """Classifies issues into tech stack tags, difficulty tiers, effort hours, and ROI."""

    @classmethod
    def classify_tech_stack(
        cls,
        repo_target: Optional[RepositoryTarget],
        title: str,
        body: Optional[str],
        labels: List[Dict[str, Any]],
    ) -> List[str]:
        """Combine repo default tech stack with detected keywords and labels."""
        tags = set()

        if repo_target:
            tags.update(repo_target.tech_stack)
            if repo_target.primary_language:
                tags.add(repo_target.primary_language)

        text = f"{title}\n{body or ''}".lower()

        # Check label names
        for label_obj in labels:
            label_name = label_obj.get("name", "") if isinstance(label_obj, dict) else str(label_obj)
            l_lower = label_name.lower()
            for tech, keywords in TECH_KEYWORDS.items():
                if any(kw in l_lower for kw in keywords):
                    tags.add(tech)

        # Check text body
        for tech, keywords in TECH_KEYWORDS.items():
            if any(re.search(rf"\b{re.escape(kw)}\b", text) for kw in keywords):
                tags.add(tech)

        # Ensure at least 1 tag
        if not tags:
            tags.add("Open Source")

        # Return sorted list (max 6 tags for UI cleanliness)
        return sorted(list(tags))[:6]

    @classmethod
    def classify_difficulty(
        cls,
        labels: List[Dict[str, Any]],
        title: str,
        body: Optional[str],
    ) -> IssueDifficulty:
        """Determine issue difficulty based on labels, text length, and complexity markers."""
        label_names = [
            (l.get("name", "") if isinstance(l, dict) else str(l)).lower().strip()
            for l in labels
        ]

        # 1. Direct label check
        for name in label_names:
            if any(easy_l in name for easy_l in EASY_LABELS):
                return IssueDifficulty.EASY
            if any(hard_l in name for hard_l in HARD_LABELS):
                return IssueDifficulty.HARD

        # 2. Text heuristics
        title_lower = title.lower()
        body_text = (body or "").lower()

        if any(w in title_lower for w in ["typo", "doc", "docs", "readme", "fix link", "spelling"]):
            return IssueDifficulty.EASY

        if any(w in title_lower for w in ["refactor", "deadlock", "memory leak", "race condition", "rfc:", "redesign", "segfault"]):
            return IssueDifficulty.HARD

        # Long complex body with multiple stack traces indicates harder investigation
        if len(body_text) > 4000 and body_text.count("traceback") > 1:
            return IssueDifficulty.HARD

        return IssueDifficulty.MEDIUM

    @classmethod
    def estimate_hours(
        cls,
        difficulty: IssueDifficulty,
        body: Optional[str] = None,
        labels: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        """Estimate hours to solve based on difficulty tier and content length."""
        body_len = len(body or "")

        if difficulty == IssueDifficulty.EASY:
            return 0.5 if body_len < 500 else 1.0
        elif difficulty == IssueDifficulty.HARD:
            return 8.0 if body_len < 2000 else 12.0
        else:  # MEDIUM
            return 2.0 if body_len < 1000 else 3.5

    @classmethod
    def calculate_hourly_roi(
        cls,
        bounty_amount_usd: Optional[float],
        estimated_hours: float,
    ) -> Optional[float]:
        """Calculate $/hr expected value for bounty hunters."""
        if bounty_amount_usd is not None and bounty_amount_usd > 0 and estimated_hours > 0:
            return round(bounty_amount_usd / estimated_hours, 2)
        return None
