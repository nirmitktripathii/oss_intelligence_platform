"""Curated Domain Registry of 36 high-velocity repositories across 6 core domains."""

from typing import Dict, List
from dataclasses import dataclass
from app.schemas.issue import IssueDomain


@dataclass(frozen=True)
class RepositoryTarget:
    owner: str
    repo: str
    domain: IssueDomain
    primary_language: str
    tech_stack: List[str]
    description: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


DOMAIN_REGISTRY: List[RepositoryTarget] = [
    # 1. AI / ML
    RepositoryTarget(
        owner="langchain-ai",
        repo="langchain",
        domain=IssueDomain.AI_ML,
        primary_language="Python",
        tech_stack=["Python", "LangChain", "LLM", "RAG"],
        description="Building applications with LLMs through composability",
    ),
    RepositoryTarget(
        owner="huggingface",
        repo="transformers",
        domain=IssueDomain.AI_ML,
        primary_language="Python",
        tech_stack=["Python", "PyTorch", "Transformers", "NLP"],
        description="State-of-the-art Machine Learning for Pytorch, TensorFlow, and JAX",
    ),
    RepositoryTarget(
        owner="vllm-project",
        repo="vllm",
        domain=IssueDomain.AI_ML,
        primary_language="Python",
        tech_stack=["Python", "C++", "CUDA", "LLM Serving"],
        description="A high-throughput and memory-efficient LLM inference engine",
    ),
    RepositoryTarget(
        owner="ollama",
        repo="ollama",
        domain=IssueDomain.AI_ML,
        primary_language="Go",
        tech_stack=["Go", "C++", "Llama", "CLI"],
        description="Get up and running with Llama 3, Mistral, and other large language models",
    ),
    RepositoryTarget(
        owner="microsoft",
        repo="autogen",
        domain=IssueDomain.AI_ML,
        primary_language="Python",
        tech_stack=["Python", "Multi-Agent", "AI Agents", "LLM"],
        description="A programming framework for agentic AI",
    ),
    RepositoryTarget(
        owner="chroma-core",
        repo="chroma",
        domain=IssueDomain.AI_ML,
        primary_language="Python",
        tech_stack=["Python", "Rust", "Vector DB", "Embeddings"],
        description="The AI-native open-source embedding database",
    ),

    # 2. Data
    RepositoryTarget(
        owner="pydantic",
        repo="pydantic",
        domain=IssueDomain.DATA,
        primary_language="Python",
        tech_stack=["Python", "Rust", "Validation", "Data Parsing"],
        description="Data validation using Python type hints",
    ),
    RepositoryTarget(
        owner="pola-rs",
        repo="polars",
        domain=IssueDomain.DATA,
        primary_language="Rust",
        tech_stack=["Rust", "Python", "DataFrames", "OLAP"],
        description="Fast multi-threaded, hybrid-streaming DataFrame library in Rust & Python",
    ),
    RepositoryTarget(
        owner="duckdb",
        repo="duckdb",
        domain=IssueDomain.DATA,
        primary_language="C++",
        tech_stack=["C++", "SQL", "Database", "Analytics"],
        description="An in-process SQL OLAP database management system",
    ),
    RepositoryTarget(
        owner="apache",
        repo="arrow",
        domain=IssueDomain.DATA,
        primary_language="C++",
        tech_stack=["C++", "Python", "Rust", "Columnar"],
        description="Apache Arrow is a multi-language toolbox for accelerated data interchange",
    ),
    RepositoryTarget(
        owner="dbt-labs",
        repo="dbt-core",
        domain=IssueDomain.DATA,
        primary_language="Python",
        tech_stack=["Python", "SQL", "Jinja", "Data Pipelines"],
        description="dbt enables data analysts and engineers to transform their data using SQL",
    ),
    RepositoryTarget(
        owner="pandas-dev",
        repo="pandas",
        domain=IssueDomain.DATA,
        primary_language="Python",
        tech_stack=["Python", "Cython", "Data Analysis", "NumPy"],
        description="Flexible and powerful data analysis / manipulation library for Python",
    ),

    # 3. Web
    RepositoryTarget(
        owner="fastapi",
        repo="fastapi",
        domain=IssueDomain.WEB,
        primary_language="Python",
        tech_stack=["Python", "FastAPI", "Starlette", "Pydantic", "AsyncIO"],
        description="FastAPI framework, high performance, easy to learn, fast to code, ready for production",
    ),
    RepositoryTarget(
        owner="pallets",
        repo="flask",
        domain=IssueDomain.WEB,
        primary_language="Python",
        tech_stack=["Python", "Flask", "WSGI", "Jinja2", "Werkzeug"],
        description="The Python micro framework for building web applications",
    ),
    RepositoryTarget(
        owner="encode",
        repo="httpx",
        domain=IssueDomain.WEB,
        primary_language="Python",
        tech_stack=["Python", "HTTPX", "HTTP/2", "AsyncIO", "Networking"],
        description="A next-generation HTTP client for Python with sync & async support",
    ),
    RepositoryTarget(
        owner="vercel",
        repo="next.js",
        domain=IssueDomain.WEB,
        primary_language="TypeScript",
        tech_stack=["TypeScript", "React", "Next.js", "Node.js", "SSR"],
        description="The React Framework for the Web",
    ),
    RepositoryTarget(
        owner="facebook",
        repo="react",
        domain=IssueDomain.WEB,
        primary_language="JavaScript",
        tech_stack=["JavaScript", "TypeScript", "React", "Frontend", "Virtual DOM"],
        description="The library for web and native user interfaces",
    ),
    RepositoryTarget(
        owner="trpc",
        repo="trpc",
        domain=IssueDomain.WEB,
        primary_language="TypeScript",
        tech_stack=["TypeScript", "tRPC", "RPC", "Full-Stack", "API"],
        description="Move Fast and Break Nothing. End-to-end typesafe APIs made easy",
    ),

    # 4. Cloud / DevOps
    RepositoryTarget(
        owner="kubernetes",
        repo="kubernetes",
        domain=IssueDomain.CLOUD_DEVOPS,
        primary_language="Go",
        tech_stack=["Go", "Kubernetes", "Containers", "Orchestration"],
        description="Production-Grade Container Scheduling and Management",
    ),
    RepositoryTarget(
        owner="hashicorp",
        repo="terraform",
        domain=IssueDomain.CLOUD_DEVOPS,
        primary_language="Go",
        tech_stack=["Go", "Terraform", "HCL", "IaC", "Cloud Infrastructure"],
        description="Terraform enables you to safely and predictably create, change, and improve infrastructure",
    ),
    RepositoryTarget(
        owner="helm",
        repo="helm",
        domain=IssueDomain.CLOUD_DEVOPS,
        primary_language="Go",
        tech_stack=["Go", "Kubernetes", "Helm", "Package Manager"],
        description="The Kubernetes Package Manager",
    ),
    RepositoryTarget(
        owner="ansible",
        repo="ansible",
        domain=IssueDomain.CLOUD_DEVOPS,
        primary_language="Python",
        tech_stack=["Python", "Ansible", "Automation", "DevOps"],
        description="Ansible is a radically simple IT automation platform",
    ),
    RepositoryTarget(
        owner="moby",
        repo="moby",
        domain=IssueDomain.CLOUD_DEVOPS,
        primary_language="Go",
        tech_stack=["Go", "Docker", "Containers", "Virtualization"],
        description="Moby Project - a collaborative project for the container ecosystem to assemble specialized container systems",
    ),
    RepositoryTarget(
        owner="prometheus",
        repo="prometheus",
        domain=IssueDomain.CLOUD_DEVOPS,
        primary_language="Go",
        tech_stack=["Go", "Prometheus", "Metrics", "Monitoring", "Time-Series"],
        description="The Prometheus monitoring system and time series database",
    ),

    # 5. Security
    RepositoryTarget(
        owner="OWASP",
        repo="CheatSheetSeries",
        domain=IssueDomain.SECURITY,
        primary_language="Markdown",
        tech_stack=["Security", "AppSec", "OWASP", "Vulnerabilities"],
        description="The OWASP Cheat Sheet Series was created to provide a concise collection of high value information",
    ),
    RepositoryTarget(
        owner="trufflesecurity",
        repo="trufflehog",
        domain=IssueDomain.SECURITY,
        primary_language="Go",
        tech_stack=["Go", "Secret Scanning", "Security", "AppSec"],
        description="Find, verify, and analyze leaked credentials across git repositories",
    ),
    RepositoryTarget(
        owner="sqlmapproject",
        repo="sqlmap",
        domain=IssueDomain.SECURITY,
        primary_language="Python",
        tech_stack=["Python", "SQL Injection", "Penetration Testing", "Security"],
        description="Automatic SQL injection and database takeover tool",
    ),
    RepositoryTarget(
        owner="projectdiscovery",
        repo="nuclei",
        domain=IssueDomain.SECURITY,
        primary_language="Go",
        tech_stack=["Go", "Vulnerability Scanner", "Templates", "InfraSec"],
        description="Fast and customizable vulnerability scanner based on simple YAML based DSL",
    ),
    RepositoryTarget(
        owner="wpscanteam",
        repo="wpscan",
        domain=IssueDomain.SECURITY,
        primary_language="Ruby",
        tech_stack=["Ruby", "WordPress", "Security Scanner", "Vulnerability Research"],
        description="WPScan WordPress Security Scanner",
    ),
    RepositoryTarget(
        owner="SigmaHQ",
        repo="sigma",
        domain=IssueDomain.SECURITY,
        primary_language="Python",
        tech_stack=["YAML", "Python", "SIEM", "Detection Engineering", "Threat Hunting"],
        description="Generic Signature Format for SIEM Systems",
    ),

    # 6. Systems
    RepositoryTarget(
        owner="rust-lang",
        repo="rust",
        domain=IssueDomain.SYSTEMS,
        primary_language="Rust",
        tech_stack=["Rust", "Compiler", "LLVM", "Memory Safety"],
        description="Empowering everyone to build reliable and efficient software",
    ),
    RepositoryTarget(
        owner="tokio-rs",
        repo="tokio",
        domain=IssueDomain.SYSTEMS,
        primary_language="Rust",
        tech_stack=["Rust", "Tokio", "Async", "Event Loop", "Networking"],
        description="A runtime for writing reliable, asynchronous, and slim applications with the Rust programming language",
    ),
    RepositoryTarget(
        owner="redis",
        repo="redis",
        domain=IssueDomain.SYSTEMS,
        primary_language="C",
        tech_stack=["C", "Redis", "In-Memory", "Cache", "Key-Value"],
        description="Redis is an in-memory database that persists on disk",
    ),
    RepositoryTarget(
        owner="neovim",
        repo="neovim",
        domain=IssueDomain.SYSTEMS,
        primary_language="C",
        tech_stack=["C", "Lua", "Vim", "Editor", "Terminal"],
        description="Vim-fork focused on extensibility and usability",
    ),
    RepositoryTarget(
        owner="ziglang",
        repo="zig",
        domain=IssueDomain.SYSTEMS,
        primary_language="Zig",
        tech_stack=["Zig", "C++", "Compiler", "Systems Programming"],
        description="General-purpose programming language and toolchain for maintaining robust, optimal, and reusable software",
    ),
    RepositoryTarget(
        owner="tauri-apps",
        repo="tauri",
        domain=IssueDomain.SYSTEMS,
        primary_language="Rust",
        tech_stack=["Rust", "TypeScript", "Desktop Apps", "Webview"],
        description="Build smaller, faster, and more secure desktop and mobile applications with a web frontend",
    ),
]


def get_repo_by_fullname(full_name: str) -> RepositoryTarget:
    """Find repository by owner/repo string."""
    for repo in DOMAIN_REGISTRY:
        if repo.full_name.lower() == full_name.lower():
            return repo
    # Default fallback target
    parts = full_name.split("/")
    owner = parts[0] if len(parts) > 0 else "unknown"
    repo_name = parts[1] if len(parts) > 1 else "unknown"
    return RepositoryTarget(
        owner=owner,
        repo=repo_name,
        domain=IssueDomain.WEB,
        primary_language="Generic",
        tech_stack=["Open Source"],
        description="Open source repository",
    )


def get_repos_by_domain(domain: IssueDomain) -> List[RepositoryTarget]:
    """Retrieve all repositories for a given domain."""
    return [repo for repo in DOMAIN_REGISTRY if repo.domain == domain]
