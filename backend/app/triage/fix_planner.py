"""Actionable CONTRIBUTING.md-compliant PR fix blueprint generator."""

from typing import List, Optional, Tuple
from app.schemas.triage import FixPlanStep, LocalizedFile


class FixPlanner:
    """Generates structured, step-by-step contribution plans adhering to OSS standards."""

    @classmethod
    def generate_plan(
        cls,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        title: str,
        localized_files: List[LocalizedFile],
    ) -> Tuple[List[FixPlanStep], str]:
        """
        Builds a 4-step actionable plan:
        1. Fork, Clone & Branching
        2. Code Modification & Logic Correction
        3. Local Verification & Test Suite Run
        4. PR Creation & Commit Message Formatting
        """
        primary_file = localized_files[0].file_path if localized_files else f"{repo_name}/core.py"
        branch_name = f"fix/issue-{issue_number}-{repo_name.lower()}"

        steps = [
            FixPlanStep(
                step_number=1,
                title="Branch Setup & Environment Initialization",
                description=f"Create a fresh working branch isolated from the main/master branch of `{repo_owner}/{repo_name}`.",
                code_snippet=f"git fetch origin\ngit checkout -b {branch_name} origin/main",
                verification_command=f"git branch --show-current",
            ),
            FixPlanStep(
                step_number=2,
                title=f"Locate and Patch Target File: {primary_file}",
                description=(
                    f"Open `{primary_file}` and inspect the logic surrounding the reported behavior. "
                    f"Apply defensive validation checks or fix condition handling."
                ),
                code_snippet=(
                    f"# In {primary_file}\n"
                    f"# Check inputs and guard against edge cases described in '{title}'\n"
                    f"if param is None:\n"
                    f"    return default_fallback_behavior()\n"
                ),
                verification_command=f"git diff {primary_file}",
            ),
            FixPlanStep(
                step_number=3,
                title="Execute Targeted Automated Test Suite",
                description=f"Run the repository's test runner to ensure the fix resolves the problem without regression.",
                code_snippet=f"pytest tests/ -k '{repo_name.lower()}' -v",
                verification_command=f"pytest tests/ --tb=short",
            ),
            FixPlanStep(
                step_number=4,
                title="Commit with Semantic Message & Submit Pull Request",
                description=(
                    f"Format commit following Conventional Commits specification. "
                    f"Link the issue in your PR body with `Fixes #{issue_number}`."
                ),
                code_snippet=(
                    f"git add {primary_file}\n"
                    f'git commit -m "fix({repo_name.lower()}): resolve {title[:50].strip()} (fixes #{issue_number})"\n'
                    f"git push -u origin {branch_name}"
                ),
                verification_command="git status",
            ),
        ]

        contributing_summary = (
            f"### Contribution Guidelines for {repo_owner}/{repo_name}\n"
            f"- **Branching**: Always branch off the latest upstream `main` branch.\n"
            f"- **Formatting**: Ensure code passes formatters (`ruff format`, `black`, `prettier`).\n"
            f"- **Testing**: All existing and newly added regression tests must pass cleanly.\n"
            f"- **PR Linking**: Mention `Fixes #{issue_number}` in PR description for automated closing."
        )

        return steps, contributing_summary
