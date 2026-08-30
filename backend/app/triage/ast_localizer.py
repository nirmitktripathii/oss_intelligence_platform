"""Multi-language AST Symbol Analyzer & Stack Trace Localizer."""

import ast
import re
from typing import Any, Dict, List, Optional, Tuple
from app.schemas.triage import LocalizedFile


# Regex patterns for stack traces across languages
STACK_PATTERNS = {
    "python": re.compile(r'File "([^"]+)", line (\d+)(?:, in (\w+))?'),
    "javascript": re.compile(r'at (?:[^\s]+ \()?([^:()]+):(\d+):(\d+)\)?'),
    "go": re.compile(r'\s+([^:\s]+\.go):(\d+)'),
    "rust": re.compile(r'at ([^:\s]+\.rs):(\d+)(?::(\d+))?'),
    "cpp": re.compile(r'([^:\s]+\.(?:cpp|cc|cxx|h|hpp)):(\d+):(?:\d+:)?\s+error'),
}

# Regex for file paths in markdown and text
FILE_PATH_PATTERN = re.compile(
    r'(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-]+\.(?:py|ts|tsx|js|jsx|go|rs|cpp|c|h|hpp|yaml|yml|json|md)',
    re.IGNORECASE,
)

# Code block extractor
CODE_BLOCK_PATTERN = re.compile(r"```([a-zA-Z0-9_\+\-]+)?\n(.*?)```", re.DOTALL)


class ASTLocalizer:
    """Analyzes issue reports to pinpoint affected files, stack frames, and AST symbols."""

    @classmethod
    def extract_stack_traces(cls, text: str) -> List[Dict[str, Any]]:
        """Parse stack traces across Python, TypeScript, Go, Rust, and C++."""
        frames = []
        for lang, pattern in STACK_PATTERNS.items():
            for match in pattern.finditer(text):
                if lang == "python":
                    file_path = match.group(1)
                    line_num = match.group(2)
                    func_name = match.group(3) or "unknown"
                    # Filter out standard library or virtualenv paths to focus on project files
                    clean_path = cls._clean_path(file_path)
                    frames.append({
                        "file_path": clean_path,
                        "line": int(line_num),
                        "function": func_name,
                        "language": "python",
                        "confidence": 0.92,
                        "rationale": f"Python traceback frame: {clean_path}:{line_num} in {func_name}()",
                    })
                elif lang in ("javascript", "go", "rust", "cpp"):
                    file_path = match.group(1)
                    line_num = match.group(2)
                    clean_path = cls._clean_path(file_path)
                    frames.append({
                        "file_path": clean_path,
                        "line": int(line_num),
                        "language": lang,
                        "confidence": 0.88,
                        "rationale": f"{lang.title()} error trace frame: {clean_path}:{line_num}",
                    })
        return frames

    @classmethod
    def extract_ast_symbols_python(cls, code_snippet: str) -> Dict[str, List[str]]:
        """Extract classes, functions, and exception references using standard Python AST."""
        symbols = {"classes": [], "functions": [], "imports": []}
        try:
            tree = ast.parse(code_snippet)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols["classes"].append(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols["functions"].append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        symbols["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        symbols["imports"].append(node.module)
        except SyntaxError:
            # Fallback regex extraction if snippet is incomplete
            classes = re.findall(r"class\s+([A-Za-z0-9_]+)", code_snippet)
            funcs = re.findall(r"def\s+([A-Za-z0-9_]+)", code_snippet)
            symbols["classes"].extend(classes)
            symbols["functions"].extend(funcs)
        return symbols

    @classmethod
    def _clean_path(cls, path_str: str) -> str:
        """Strip absolute host/virtualenv prefixes to yield repository-relative paths."""
        path = path_str.replace("\\", "/")
        for prefix in ["/site-packages/", "/dist-packages/", "/lib/python", "/node_modules/", "src/"]:
            if prefix in path:
                return path.split(prefix)[-1]
        # Keep relative path
        if path.startswith("/"):
            parts = path.strip("/").split("/")
            return "/".join(parts[-3:]) if len(parts) >= 3 else path.strip("/")
        return path

    @classmethod
    def localize(
        cls,
        repo_owner: str,
        repo_name: str,
        title: str,
        body: Optional[str],
    ) -> Tuple[List[LocalizedFile], str]:
        """
        Produce a list of candidate files with confidence scores and a root cause analysis summary.
        """
        full_text = f"{title}\n{body or ''}"
        localized: List[LocalizedFile] = []
        seen_paths = set()

        # 1. Stack trace extraction (highest confidence)
        trace_frames = cls.extract_stack_traces(full_text)
        for frame in trace_frames:
            fpath = frame["file_path"]
            if fpath not in seen_paths and not fpath.startswith("http"):
                seen_paths.add(fpath)
                line = frame.get("line")
                line_range = f"{max(1, line - 10)}-{line + 15}" if line else None
                localized.append(
                    LocalizedFile(
                        file_path=fpath,
                        line_range=line_range,
                        confidence=frame.get("confidence", 0.90),
                        rationale=frame["rationale"],
                    )
                )

        # 2. Extract code blocks and run AST analysis
        code_blocks = CODE_BLOCK_PATTERN.findall(full_text)
        ast_symbols: Dict[str, List[str]] = {"classes": [], "functions": [], "imports": []}
        for lang_tag, code_body in code_blocks:
            syms = cls.extract_ast_symbols_python(code_body)
            for k, v in syms.items():
                ast_symbols[k].extend(v)

        # 3. Path references mentioned in text
        for match in FILE_PATH_PATTERN.finditer(full_text):
            p = match.group(0).replace("\\", "/")
            if p not in seen_paths and not p.startswith("http") and not p.endswith(".md"):
                # Exclude URL-like patterns or generic file names
                if "/" in p or p.endswith((".py", ".ts", ".go", ".rs")):
                    seen_paths.add(p)
                    localized.append(
                        LocalizedFile(
                            file_path=p,
                            line_range=None,
                            confidence=0.75,
                            rationale=f"Referenced directly in problem description: `{p}`",
                        )
                    )

        # 4. Fallback: if no explicit file was detected, infer primary module target
        if not localized:
            default_file = f"{repo_name.lower().replace('-', '_')}/core.py"
            if repo_name.lower() in ("fastapi", "flask", "httpx", "pydantic", "langchain"):
                default_file = f"{repo_name.lower()}/main.py"
            localized.append(
                LocalizedFile(
                    file_path=default_file,
                    line_range="1-50",
                    confidence=0.45,
                    rationale=f"Inferred entrypoint for {repo_owner}/{repo_name}",
                )
            )

        # Generate Root Cause Analysis Summary
        symbols_desc = ""
        if ast_symbols["functions"] or ast_symbols["classes"]:
            symbols_desc = f" AST references detected: functions={ast_symbols['functions'][:3]}, classes={ast_symbols['classes'][:3]}."

        root_cause = (
            f"Issue involves behavior reported in '{title}'. "
            f"Identified {len(localized)} target candidate files.{symbols_desc} "
            f"Primary point of investigation is {localized[0].file_path}."
        )

        return localized[:5], root_cause
