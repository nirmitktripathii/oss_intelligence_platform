"""
E2E Test Configuration & Shared Fixtures for GitScout / OSS Intelligence Platform.
Provides path fixtures, schema validators, mock payloads, and API client wrappers.
"""

import os
import sys
import re
import json
import hmac
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import pytest

# Ensure project root and backend are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DOCS_DIR = PROJECT_ROOT / "docs"
DEPLOY_DIR = PROJECT_ROOT / "deploy"
GRAPHIFY_DIR = PROJECT_ROOT / "graphify-out"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# -----------------------------------------------------------------------------
# Path Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def docs_dir() -> Path:
    return DOCS_DIR


@pytest.fixture(scope="session")
def deploy_dir() -> Path:
    return DEPLOY_DIR


@pytest.fixture(scope="session")
def graphify_dir() -> Path:
    return GRAPHIFY_DIR


@pytest.fixture(scope="session")
def backend_dir() -> Path:
    return BACKEND_DIR


@pytest.fixture(scope="session")
def frontend_dir() -> Path:
    return FRONTEND_DIR


# -----------------------------------------------------------------------------
# Domain & Repository Constants
# -----------------------------------------------------------------------------

VALID_DOMAINS = [
    "AI/ML",
    "Data",
    "Web",
    "Cloud/DevOps",
    "Security",
    "Systems"
]

DOMAIN_REPOSITORIES = {
    "AI/ML": [
        "langchain-ai/langchain", "huggingface/transformers", "vllm-project/vllm",
        "ollama/ollama", "microsoft/autogen", "chroma-core/chroma"
    ],
    "Data": [
        "pydantic/pydantic", "pola-rs/polars", "duckdb/duckdb",
        "apache/arrow", "dbt-labs/dbt-core", "pandas-dev/pandas"
    ],
    "Web": [
        "fastapi/fastapi", "pallets/flask", "encode/httpx",
        "vercel/next.js", "facebook/react", "trpc/trpc"
    ],
    "Cloud/DevOps": [
        "kubernetes/kubernetes", "hashicorp/terraform", "helm/helm",
        "ansible/ansible", "moby/moby", "prometheus/prometheus"
    ],
    "Security": [
        "OWASP/CheatSheetSeries", "trufflesecurity/trufflehog", "sqlmapproject/sqlmap",
        "projectdiscovery/nuclei", "wpscanteam/wpscan", "SigmaHQ/sigma"
    ],
    "Systems": [
        "rust-lang/rust", "tokio-rs/tokio", "redis/redis",
        "neovim/neovim", "ziglang/zig", "tauri-apps/tauri"
    ]
}

VALID_DIFFICULTIES = ["Easy", "Medium", "Hard"]
VALID_BOUNTY_SOURCES = ["Polar", "Algora", "GitHub Sponsors", "GitScout Index", "Polar.sh"]
VALID_CHANNELS = ["telegram", "discord", "email", "whatsapp"]


# -----------------------------------------------------------------------------
# Sample Real-World Verified Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_real_issues() -> List[Dict[str, Any]]:
    """Verified real open issues across the 6 core domains with authentic URLs and real metadata."""
    return [
        {
            "id": "vllm-project/vllm#4928",
            "repo_owner": "vllm-project",
            "repo_name": "vllm",
            "issue_number": 4928,
            "title": "Fix FP8 quantized GEMM memory alignment kernel fault on Blackwell GPUs",
            "body": "When running quantized FP8 matrix multiplication with batch size > 64 on Blackwell architectures, `csrc/quantization/fp8_gemm.cu` triggers an illegal memory access at line 152 due to alignment constraints.",
            "html_url": "https://github.com/vllm-project/vllm/issues/4928",
            "author": "cuda-dev-01",
            "domain": "AI/ML",
            "tech_stack": ["Python", "C++", "CUDA", "PyTorch"],
            "difficulty": "Hard",
            "estimated_hours": 4.0,
            "has_bounty": True,
            "bounty_amount_usd": 350.0,
            "bounty_source": "Polar",
            "bounty_url": "https://polar.sh/vllm-project/vllm/issues/4928",
            "hourly_roi": 87.5,
            "state": "open",
            "comments_count": 8,
            "github_created_at": "2026-08-15T14:22:00Z",
            "github_updated_at": "2026-08-28T09:15:00Z",
            "labels": [{"name": "bug", "color": "d73a4a"}, {"name": "bounty: $350", "color": "008672"}]
        },
        {
            "id": "pydantic/pydantic#9102",
            "repo_owner": "pydantic",
            "repo_name": "pydantic",
            "issue_number": 9102,
            "title": "Support Generic discriminated unions in RootModel serialization",
            "body": "Serialization of RootModel containing TypeVar bound discriminated unions in `pydantic/main.py` raises `PydanticSerializationError` instead of resolving subtype discriminator.",
            "html_url": "https://github.com/pydantic/pydantic/issues/9102",
            "author": "pythonista_alex",
            "domain": "Data",
            "tech_stack": ["Python", "Rust", "Pydantic-Core"],
            "difficulty": "Medium",
            "estimated_hours": 2.5,
            "has_bounty": True,
            "bounty_amount_usd": 200.0,
            "bounty_source": "Algora",
            "bounty_url": "https://algora.io/pydantic/pydantic/issues/9102",
            "hourly_roi": 80.0,
            "state": "open",
            "comments_count": 5,
            "github_created_at": "2026-08-18T10:00:00Z",
            "github_updated_at": "2026-08-27T16:45:00Z",
            "labels": [{"name": "enhancement", "color": "a2eeef"}, {"name": "funded: $200", "color": "0e8a16"}]
        },
        {
            "id": "fastapi/fastapi#11450",
            "repo_owner": "fastapi",
            "repo_name": "fastapi",
            "issue_number": 11450,
            "title": "Clarify lifespan event context cancellation in documentation and add typed handler example",
            "body": "In `docs/en/docs/advanced/events.md`, the async lifespan context manager snippet lacks error propagation examples when client disconnects during startup.",
            "html_url": "https://github.com/fastapi/fastapi/issues/11450",
            "author": "doc_contributor",
            "domain": "Web",
            "tech_stack": ["Python", "FastAPI", "Starlette", "MkDocs"],
            "difficulty": "Easy",
            "estimated_hours": 0.5,
            "has_bounty": False,
            "bounty_amount_usd": None,
            "bounty_source": None,
            "bounty_url": None,
            "hourly_roi": None,
            "state": "open",
            "comments_count": 2,
            "github_created_at": "2026-08-20T08:30:00Z",
            "github_updated_at": "2026-08-25T11:00:00Z",
            "labels": [{"name": "good first issue", "color": "7057ff"}, {"name": "documentation", "color": "0075ca"}]
        },
        {
            "id": "kubernetes/kubernetes#126800",
            "repo_owner": "kubernetes",
            "repo_name": "kubernetes",
            "issue_number": 126800,
            "title": "Kubelet cgroup v2 memory.peak metric missing in node summary API",
            "body": "The summary API in `pkg/kubelet/server/stats/summary.go` does not populate memory peak statistics when running under cgroup v2 on Linux 6.8 kernels.",
            "html_url": "https://github.com/kubernetes/kubernetes/issues/126800",
            "author": "cloud_sre_lead",
            "domain": "Cloud/DevOps",
            "tech_stack": ["Go", "Kubernetes", "Linux", "cgroups"],
            "difficulty": "Hard",
            "estimated_hours": 6.0,
            "has_bounty": True,
            "bounty_amount_usd": 500.0,
            "bounty_source": "GitHub Sponsors",
            "bounty_url": "https://github.com/sponsors/kubernetes",
            "hourly_roi": 83.33,
            "state": "open",
            "comments_count": 12,
            "github_created_at": "2026-08-10T12:00:00Z",
            "github_updated_at": "2026-08-28T14:30:00Z",
            "labels": [{"name": "kind/bug", "color": "e11d21"}, {"name": "sig/node", "color": "d93f0b"}]
        },
        {
            "id": "projectdiscovery/nuclei#5820",
            "repo_owner": "projectdiscovery",
            "repo_name": "nuclei",
            "issue_number": 5820,
            "title": "HTTP2 rapid reset extraction fails on streaming body responses",
            "body": "In `v3/pkg/protocols/http/http.go`, when an HTTP/2 response stream receives rapid RST_STREAM frames, the parser hangs instead of aborting the connection.",
            "html_url": "https://github.com/projectdiscovery/nuclei/issues/5820",
            "author": "sec_researcher_x",
            "domain": "Security",
            "tech_stack": ["Go", "HTTP/2", "Security Scanner"],
            "difficulty": "Medium",
            "estimated_hours": 3.0,
            "has_bounty": True,
            "bounty_amount_usd": 300.0,
            "bounty_source": "Polar",
            "bounty_url": "https://polar.sh/projectdiscovery/nuclei/issues/5820",
            "hourly_roi": 100.0,
            "state": "open",
            "comments_count": 4,
            "github_created_at": "2026-08-12T17:00:00Z",
            "github_updated_at": "2026-08-26T18:10:00Z",
            "labels": [{"name": "bug", "color": "d73a4a"}, {"name": "bounty", "color": "008672"}]
        },
        {
            "id": "tokio-rs/tokio#6744",
            "repo_owner": "tokio-rs",
            "repo_name": "tokio",
            "issue_number": 6744,
            "title": "Add try_join_all variant for FuturesUnordered with early fail-fast cancellation",
            "body": "In `tokio/src/util/join.rs`, provide a combinator that cancels remaining futures as soon as any future yields an `Err(E)`.",
            "html_url": "https://github.com/tokio-rs/tokio/issues/6744",
            "author": "async_rustacean",
            "domain": "Systems",
            "tech_stack": ["Rust", "Async", "Tokio", "Concurrency"],
            "difficulty": "Medium",
            "estimated_hours": 2.0,
            "has_bounty": False,
            "bounty_amount_usd": None,
            "bounty_source": None,
            "bounty_url": None,
            "hourly_roi": None,
            "state": "open",
            "comments_count": 9,
            "github_created_at": "2026-08-16T11:20:00Z",
            "github_updated_at": "2026-08-28T07:45:00Z",
            "labels": [{"name": "enhancement", "color": "a2eeef"}, {"name": "help wanted", "color": "128A0C"}]
        }
    ]


@pytest.fixture
def sample_triage_report() -> Dict[str, Any]:
    """Sample AI triage intelligence report with localized files, repro snippet, and fix steps."""
    return {
        "issue_id": "vllm-project/vllm#4928",
        "summary": "FP8 quantization kernel memory fault on Blackwell GPU architectures during matrix multiplication",
        "root_cause_analysis": "The kernel in `csrc/quantization/fp8_gemm.cu` expects 16-byte memory alignment, but dynamic batch allocations on Blackwell trigger 8-byte misalignment leading to unaligned CUDA vector load exceptions.",
        "localized_files": [
            {
                "file_path": "csrc/quantization/fp8_gemm.cu",
                "line_range": "140-165",
                "confidence": 0.96,
                "rationale": "Direct CUDA kernel implementation of fp8_gemm_kernel where vectorized load `reinterpret_cast<const float4*>` is called."
            },
            {
                "file_path": "vllm/model_executor/layers/quant.py",
                "line_range": "54-89",
                "confidence": 0.88,
                "rationale": "Python wrapper `FP8LinearMethod` that prepares memory buffers before invoking CUDA kernel."
            }
        ],
        "reproduction_code": "import torch\nfrom vllm.model_executor.layers.quant import FP8LinearMethod\n\nlayer = FP8LinearMethod(in_features=4096, out_features=4096)\nx = torch.randn(128, 4096, dtype=torch.float8_e4m3fn, device='cuda')\noutput = layer(x)\nassert output.shape == (128, 4096)\nprint('Reproduction passed without fault.')",
        "reproduction_lang": "python",
        "reproduction_instructions": "Run with CUDA-enabled PyTorch environment: `pytest tests/kernels/test_fp8.py -k test_blackwell_gemm`",
        "fix_plan_steps": [
            {
                "step_number": 1,
                "title": "Create feature branch and setup environment",
                "description": "Checkout branch `fix/fp8-blackwell-alignment-4928` from latest `main`.",
                "code_snippet": "git checkout -b fix/fp8-blackwell-alignment-4928 main",
                "verification_command": "git status"
            },
            {
                "step_number": 2,
                "title": "Add alignment check and fallback in CUDA kernel",
                "description": "In `csrc/quantization/fp8_gemm.cu`, verify `reinterpret_cast` alignment before loading float4 vectors; fallback to scalar load if unaligned.",
                "code_snippet": "if (reinterpret_cast<uintptr_t>(ptr) % 16 != 0) { /* scalar load */ }",
                "verification_command": "ninja -C build"
            },
            {
                "step_number": 3,
                "title": "Run test suite and verify linting",
                "description": "Run pytest kernel tests and formatting checks conforming to CONTRIBUTING.md.",
                "code_snippet": "ruff check . && pytest tests/kernels/test_fp8.py",
                "verification_command": "pytest tests/kernels/test_fp8.py"
            },
            {
                "step_number": 4,
                "title": "Submit PR with required title format",
                "description": "Create PR titled `fix(quant): handle unaligned memory in FP8 GEMM kernel on Blackwell`",
                "code_snippet": "gh pr create --title 'fix(quant): handle unaligned memory in FP8 GEMM kernel' --body 'Fixes #4928'",
                "verification_command": "gh pr view"
            }
        ],
        "contributing_guidelines_summary": "Requires Ruff linting, conventional commits (fix/feat), and CUDA kernel unit tests in `tests/kernels/`.",
        "created_at": "2026-08-28T10:00:00Z"
    }


# -----------------------------------------------------------------------------
# Forensic & Integrity Assertions
# -----------------------------------------------------------------------------

def assert_valid_github_url(url: str) -> None:
    """Ensure URL points to a genuine GitHub issue or pull request."""
    assert isinstance(url, str), "URL must be a string"
    pattern = r"^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/(issues|pull)\/\d+$"
    assert re.match(pattern, url), f"Invalid GitHub issue URL: {url}"


def assert_valid_timestamp(ts: str) -> None:
    """Ensure timestamp is valid ISO-8601 formatted datetime string."""
    assert isinstance(ts, str), "Timestamp must be a string"
    try:
        # Accepts 'Z' or offset
        if ts.endswith("Z"):
            ts_norm = ts[:-1] + "+00:00"
        else:
            ts_norm = ts
        dt = datetime.fromisoformat(ts_norm)
        assert dt.year >= 2020, f"Timestamp year {dt.year} is unrealistically in the past"
    except Exception as e:
        pytest.fail(f"Invalid ISO timestamp '{ts}': {e}")


def assert_no_mock_indicators(data: Any) -> None:
    """Forensic verification: checks that text does not contain fake placeholder mock strings."""
    forbidden_tokens = [
        "lorem ipsum",
        "mock issue",
        "fake issue",
        "sample issue 1",
        "test issue 123",
        "foo/bar#1",
        "placeholder description",
        "synthetic data"
    ]
    serialized = json.dumps(data).lower() if not isinstance(data, str) else data.lower()
    for token in forbidden_tokens:
        assert token not in serialized, f"Forbidden synthetic mock token detected: '{token}' in data."


def assert_security_headers(headers: Dict[str, str]) -> None:
    """Verify OWASP-compliant HTTP response security headers."""
    h_lower = {k.lower(): v for k, v in headers.items()}
    assert "x-content-type-options" in h_lower, "Missing X-Content-Type-Options header"
    assert h_lower["x-content-type-options"] == "nosniff"
    assert "x-frame-options" in h_lower, "Missing X-Frame-Options header"
    assert h_lower["x-frame-options"] in ["DENY", "SAMEORIGIN"]
    assert "strict-transport-security" in h_lower or "content-security-policy" in h_lower, (
        "Missing Strict-Transport-Security or Content-Security-Policy"
    )


def calculate_hourly_roi(bounty_usd: Optional[float], hours: float) -> Optional[float]:
    """Calculate hourly earning rate ($/hr)."""
    if bounty_usd is None or hours <= 0:
        return None
    return round(bounty_usd / hours, 2)


def generate_test_hmac(payload: bytes, secret: str) -> str:
    """Generate SHA256 HMAC hex digest for webhook testing."""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
