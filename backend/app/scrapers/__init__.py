"""Scrapers and classifiers package."""

from app.scrapers.domain_registry import DOMAIN_REGISTRY, RepositoryTarget, get_repo_by_fullname, get_repos_by_domain
from app.scrapers.github_client import GitHubClient
from app.scrapers.bounty_extractor import BountyExtractor
from app.scrapers.classifier import IssueClassifier
from app.scrapers.orchestrator import ScraperOrchestrator

__all__ = [
    "DOMAIN_REGISTRY",
    "RepositoryTarget",
    "get_repo_by_fullname",
    "get_repos_by_domain",
    "GitHubClient",
    "BountyExtractor",
    "IssueClassifier",
    "ScraperOrchestrator",
]
