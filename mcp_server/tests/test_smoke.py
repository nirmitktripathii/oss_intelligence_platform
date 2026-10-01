"""Offline smoke tests: the server imports and registers its tools.

These do not touch the network or the GitScout backend — they verify the MCP
tool surface is wired correctly. Run: `pytest mcp_server/tests`.
"""

import asyncio

from gitscout_mcp.server import mcp


def test_expected_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    expected = {
        "search_issues",
        "get_issue",
        "analyze_issue",
        "analyze_issue_text",
        "gitscout_health",
    }
    missing = expected - names
    assert not missing, f"MCP tools not registered: {missing}"


def test_tools_have_descriptions():
    tools = asyncio.run(mcp.list_tools())
    for t in tools:
        assert t.description and t.description.strip(), f"{t.name} is missing a description"


def test_filter_values_are_normalised_to_backend_enums():
    from gitscout_mcp.server import _DIFFICULTIES, _DOMAINS, _canon

    for given in ("ai_ml", "AI/ML", "ai", "ML", "ai-ml"):
        assert _canon(given, _DOMAINS) == "AI/ML"
    assert _canon("cloud/devops", _DOMAINS) == "Cloud/DevOps"
    assert _canon("beginner", _DIFFICULTIES) == "Easy"
    assert _canon("Hard", _DIFFICULTIES) == "Hard"
    assert _canon(None, _DOMAINS) is None
    assert _canon("nonsense", _DOMAINS) == "nonsense"
