"""Unit tests for AST Localization, Repro Generator, and Fix Planner."""

from app.triage.ast_localizer import ASTLocalizer
from app.triage.fix_planner import FixPlanner
from app.triage.repro_generator import ReproGenerator


def test_python_stack_trace_extraction():
    """Verify parsing Python traceback frames."""
    text = (
        "Got this error when running server:\n"
        "Traceback (most recent call last):\n"
        '  File "/site-packages/fastapi/applications.py", line 120, in setup\n'
        '  File "/home/user/project/fastapi/routing.py", line 45, in add_api_route\n'
        "ValueError: Invalid path"
    )
    frames = ASTLocalizer.extract_stack_traces(text)
    assert len(frames) == 2
    assert "fastapi/applications.py" in frames[0]["file_path"]
    assert frames[0]["line"] == 120
    assert frames[0]["function"] == "setup"
    assert "fastapi/routing.py" in frames[1]["file_path"]
    assert frames[1]["line"] == 45


def test_multi_lang_stack_trace_extraction():
    """Verify parsing Go and Rust error traces."""
    # Go
    go_text = "panic: runtime error\n\tpkg/kubelet/volumemanager.go:142 +0x1a"
    go_frames = ASTLocalizer.extract_stack_traces(go_text)
    assert len(go_frames) >= 1
    assert "volumemanager.go" in go_frames[0]["file_path"]

    # Rust
    rust_text = "thread 'main' panicked at polars-core/src/frame/join.rs:210:9"
    rust_frames = ASTLocalizer.extract_stack_traces(rust_text)
    assert len(rust_frames) >= 1
    assert "join.rs" in rust_frames[0]["file_path"]


def test_ast_symbols_python():
    """Verify extracting Python symbols via AST module."""
    code = (
        "import os\n"
        "from fastapi import APIRouter\n\n"
        "class CustomHandler:\n"
        "    def handle_request(self, req):\n"
        "        pass\n"
    )
    symbols = ASTLocalizer.extract_ast_symbols_python(code)
    assert "CustomHandler" in symbols["classes"]
    assert "handle_request" in symbols["functions"]
    assert "os" in symbols["imports"] or "fastapi" in symbols["imports"]


def test_repro_generator_python():
    """Verify minimal reproduction script creation."""
    snippet = "app = FastAPI()\napp.include_router(None)"
    code, lang, inst = ReproGenerator.generate(
        repo_owner="fastapi",
        repo_name="fastapi",
        title="Router inclusion error",
        body=f"```python\n{snippet}\n```",
    )
    assert lang == "python"
    assert "def run_repro():" in code
    assert "app.include_router(None)" in code
    assert "reproduce_fastapi_issue.py" in inst


def test_fix_planner_steps():
    """Verify 4-step actionable fix blueprint generation."""
    localized, _ = ASTLocalizer.localize("fastapi", "fastapi", "Bug in routing", "File \"fastapi/routing.py\", line 50")
    steps, summary = FixPlanner.generate_plan("fastapi", "fastapi", 101, "Bug in routing", localized)

    assert len(steps) == 4
    assert steps[0].step_number == 1
    assert "git checkout -b fix/issue-101-fastapi" in steps[0].code_snippet
    assert "fastapi/routing.py" in steps[1].title
    assert "fixes #101" in steps[3].code_snippet.lower()
    assert "Contribution Guidelines" in summary
