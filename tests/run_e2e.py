#!/usr/bin/env python3
"""
CLI Test Runner for GitScout / OSS Terminal E2E Test Suite.
Executes 4 tiers of opaque-box tests and forensic integrity checks with formatted reporting.
Windows-safe: uses ASCII markers ([OK], [FAIL], [INFO], [WARN]) to prevent CP1252 UnicodeEncodeError.
"""

import os
import sys
import time
import argparse
import unittest
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))


def run_with_pytest(test_files: list, verbose: bool = False) -> int:
    """Run specified test files using pytest."""
    try:
        import pytest
        args = ["-v" if verbose else "-q", "--tb=short"] + test_files
        print(f"[RUN] Executing pytest with arguments: {' '.join(args)}")
        return pytest.main(args)
    except ImportError:
        print("[WARN] pytest not installed in active environment. Falling back to built-in runner...")
        return run_with_builtin(test_files, verbose)


def run_with_builtin(test_files: list, verbose: bool = False) -> int:
    """Fallback runner using standard Python unittest loader."""
    import importlib.util
    
    total_run = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    
    start_time = time.time()
    
    for file_path in test_files:
        module_path = Path(file_path).resolve()
        if not module_path.exists():
            print(f"[ERROR] Test file not found: {file_path}")
            continue
            
        module_name = module_path.stem
        spec = importlib.util.spec_from_file_location(module_name, str(module_path))
        if spec is None or spec.loader is None:
            print(f"[ERROR] Could not load spec for: {file_path}")
            continue
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        print(f"\n[TIER] Executing {module_name}...")
        
        # Discover test classes and functions
        test_classes = [
            getattr(module, attr) for attr in dir(module) 
            if attr.startswith("Test") and isinstance(getattr(module, attr), type)
        ]
        
        # Default fixture data providers
        from tests.e2e.conftest import (
            sample_real_issues as get_sample_issues,
            sample_triage_report as get_sample_triage,
            docs_dir as get_docs_dir,
            deploy_dir as get_deploy_dir,
            graphify_dir as get_graphify_dir
        )
        
        fixtures = {
            "sample_real_issues": get_sample_issues(),
            "sample_triage_report": get_sample_triage(),
            "docs_dir": get_docs_dir(),
            "deploy_dir": get_deploy_dir(),
            "graphify_dir": get_graphify_dir()
        }
        
        for cls in test_classes:
            instance = cls()
            methods = [m for m in dir(cls) if m.startswith("test_")]
            for method_name in methods:
                method = getattr(instance, method_name)
                total_run += 1
                try:
                    # Inspect method arguments to inject fixtures if needed
                    import inspect
                    sig = inspect.signature(method)
                    kwargs = {}
                    for param in sig.parameters.values():
                        if param.name in fixtures:
                            kwargs[param.name] = fixtures[param.name]
                            
                    method(**kwargs)
                    total_passed += 1
                    if verbose:
                        print(f"  [OK] {cls.__name__}.{method_name}")
                    else:
                        print(".", end="", flush=True)
                except AssertionError as ae:
                    total_failed += 1
                    print(f"\n  [FAIL] {cls.__name__}.{method_name}: {ae}")
                except Exception as ex:
                    total_errors += 1
                    print(f"\n  [ERROR] {cls.__name__}.{method_name}: {ex}")

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"[SUMMARY] Total Tests: {total_run} | Passed: {total_passed} | Failed: {total_failed} | Errors: {total_errors}")
    print(f"[TIME] Elapsed: {elapsed:.2f}s")
    print("=" * 70)
    
    return 0 if (total_failed == 0 and total_errors == 0) else 1


def main():
    parser = argparse.ArgumentParser(description="GitScout / OSS Terminal E2E Test Suite Runner")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "audit", "all"], default="all",
                        help="Select specific test tier to run (1, 2, 3, 4, audit, or all)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose test output")
    
    args = parser.parse_args()
    
    tier_map = {
        "1": ["tests/e2e/test_tier1_features.py"],
        "2": ["tests/e2e/test_tier2_boundaries.py"],
        "3": ["tests/e2e/test_tier3_pairwise.py"],
        "4": ["tests/e2e/test_tier4_scenarios.py"],
        "audit": ["tests/e2e/test_audit_integrity.py"],
        "all": [
            "tests/e2e/test_tier1_features.py",
            "tests/e2e/test_tier2_boundaries.py",
            "tests/e2e/test_tier3_pairwise.py",
            "tests/e2e/test_tier4_scenarios.py",
            "tests/e2e/test_audit_integrity.py"
        ]
    }
    
    target_files = tier_map[args.tier]
    
    print("=" * 70)
    print(f"GitScout / OSS Intelligence Platform - E2E Test Runner")
    print(f"Mode: Tier '{args.tier.upper()}' | Target Files: {len(target_files)}")
    print("=" * 70)
    
    exit_code = run_with_pytest(target_files, verbose=args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
