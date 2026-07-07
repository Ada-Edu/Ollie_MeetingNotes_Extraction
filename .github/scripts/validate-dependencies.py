#!/usr/bin/env python3
"""
Dependency Validation Script

This script validates that:
1. Frontend package-lock.json is in sync with package.json
2. Backend pyproject.toml includes all dependencies used in test files
3. GitHub Actions workflows install dependencies correctly

Usage: python validate-dependencies.py
Exit code: 0 if all checks pass, 1 if any check fails
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Set, List, Tuple


def check_frontend_lockfile_sync() -> bool:
    """Check if package-lock.json is in sync with package.json"""
    print("🔍 Checking frontend package-lock.json sync...")

    frontend_dir = Path("frontend")
    package_json = frontend_dir / "package.json"
    package_lock = frontend_dir / "package-lock.json"

    if not package_json.exists():
        print(f"  ⚠️  Warning: {package_json} not found")
        return True

    if not package_lock.exists():
        print(f"  ❌ Error: {package_lock} not found")
        print(f"  💡 Run: cd frontend && npm install")
        return False

    # Read package.json to get dependencies
    with open(package_json) as f:
        pkg_data = json.load(f)

    all_deps = {}
    all_deps.update(pkg_data.get("dependencies", {}))
    all_deps.update(pkg_data.get("devDependencies", {}))

    # Read package-lock.json
    with open(package_lock) as f:
        lock_data = json.load(f)

    # Check for version mismatches (basic check)
    # A more thorough check would require npm ci dry-run
    lock_packages = lock_data.get("packages", {}).get("", {})
    lock_deps = {}
    lock_deps.update(lock_packages.get("dependencies", {}))
    lock_deps.update(lock_packages.get("devDependencies", {}))

    if set(all_deps.keys()) != set(lock_deps.keys()):
        print(f"  ❌ Error: package.json and package-lock.json have different dependencies")
        print(f"  💡 Run: cd frontend && npm install")
        return False

    print("  ✅ Frontend lockfile appears in sync")
    return True


def extract_python_imports(file_path: Path) -> Set[str]:
    """Extract top-level module names from Python imports"""
    imports = set()

    with open(file_path) as f:
        for line in f:
            line = line.strip()
            # Match: import module or from module import ...
            if line.startswith("import "):
                module = line[7:].split()[0].split(".")[0].split(" as ")[0]
                imports.add(module)
            elif line.startswith("from "):
                module = line[5:].split()[0].split(".")[0]
                imports.add(module)

    return imports


def get_package_name_from_import(import_name: str) -> str:
    """Map import name to likely package name"""
    # Common mappings
    mappings = {
        "fastapi": "fastapi",
        "sqlalchemy": "sqlalchemy",
        "azure": "azure-core",
        "supabase": "supabase",
        "pytest": "pytest",
        "httpx": "httpx",
        "temporalio": "temporalio",
        "pydantic": "pydantic",
        "boto3": "boto3",
        "botocore": "boto3",
        "openai": "openai",
        "faker": "faker",
        "freezegun": "freezegun",
    }
    return mappings.get(import_name, import_name)


def check_backend_dependencies() -> bool:
    """Check if all imported modules are in pyproject.toml"""
    print("🔍 Checking backend Python dependencies...")

    temporal_dir = Path("temporal")
    pyproject = temporal_dir / "pyproject.toml"
    tests_dir = temporal_dir / "tests"

    if not pyproject.exists():
        print(f"  ⚠️  Warning: {pyproject} not found")
        return True

    if not tests_dir.exists():
        print(f"  ⚠️  Warning: {tests_dir} not found")
        return True

    # Read pyproject.toml to extract dependencies
    with open(pyproject) as f:
        content = f.read()

    # Extract dependencies from pyproject.toml (simple regex approach)
    deps_section = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
    dev_deps_section = re.search(r'\[project\.optional-dependencies\].*?dev\s*=\s*\[(.*?)\]', content, re.DOTALL)

    declared_packages = set()

    if deps_section:
        for line in deps_section.group(1).split('\n'):
            match = re.search(r'"([^"=<>]+)', line)
            if match:
                declared_packages.add(match.group(1))

    if dev_deps_section:
        for line in dev_deps_section.group(1).split('\n'):
            match = re.search(r'"([^"=<>]+)', line)
            if match:
                declared_packages.add(match.group(1))

    # Scan all test files for imports
    all_imports = set()
    for test_file in tests_dir.rglob("*.py"):
        if test_file.name.startswith("test_") or test_file.name.endswith("_test.py"):
            imports = extract_python_imports(test_file)
            all_imports.update(imports)

    # Filter to external packages (exclude stdlib and local modules)
    stdlib_modules = {
        "sys", "os", "pathlib", "unittest", "asyncio", "datetime", "typing",
        "uuid", "json", "time", "re", "collections", "functools", "io",
        "contextlib", "warnings", "importlib"
    }
    local_modules = {
        "src", "workflows", "activities", "models", "database", "api",
        "temporal", "supabase_client", "tests"
    }

    external_imports = all_imports - stdlib_modules - local_modules

    # Map imports to package names
    required_packages = {get_package_name_from_import(imp) for imp in external_imports}

    # Check for missing packages
    missing_packages = required_packages - declared_packages

    # Filter out packages that might be sub-imports of declared packages
    actually_missing = set()
    for pkg in missing_packages:
        # Check if any declared package is a prefix (e.g., azure-core covers azure.*)
        if not any(pkg.startswith(declared.split("-")[0]) for declared in declared_packages):
            actually_missing.add(pkg)

    if actually_missing:
        print(f"  ❌ Error: Test files import packages not in pyproject.toml:")
        for pkg in sorted(actually_missing):
            print(f"     - {pkg}")
        print(f"  💡 Add these to [project.optional-dependencies].dev in temporal/pyproject.toml")
        return False

    print("  ✅ All test imports are declared in pyproject.toml")
    return True


def check_github_workflows() -> bool:
    """Check that GitHub workflows install dependencies correctly"""
    print("🔍 Checking GitHub Actions workflows...")

    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print(f"  ⚠️  Warning: {workflows_dir} not found")
        return True

    issues = []

    for workflow_file in workflows_dir.glob("*.yml"):
        with open(workflow_file) as f:
            content = f.read()

        # Check for manual pip install instead of using pyproject.toml
        if "pip install pytest" in content and 'pip install -e ".[dev]"' not in content:
            # Check if this is in a Python test job
            if "pytest" in content or "python" in content.lower():
                issues.append(
                    f"  ⚠️  {workflow_file.name}: Uses manual 'pip install pytest...' instead of 'pip install -e \".[dev]\"'"
                )

        # Check for npm ci usage (good practice)
        if "npm install" in content and "frontend" in content and "npm ci" not in content:
            issues.append(
                f"  ℹ️  {workflow_file.name}: Uses 'npm install' - consider 'npm ci' for reproducible builds"
            )

    if issues:
        for issue in issues:
            print(issue)
        print(f"  💡 Workflows should use 'pip install -e \".[dev]\"' to install all dev dependencies")
        return False

    print("  ✅ GitHub workflows use proper dependency installation")
    return True


def main():
    """Run all validation checks"""
    print("=" * 60)
    print("🚀 Dependency Validation")
    print("=" * 60)

    checks = [
        ("Frontend lockfile sync", check_frontend_lockfile_sync),
        ("Backend dependencies", check_backend_dependencies),
        ("GitHub workflows", check_github_workflows),
    ]

    results = []
    for name, check_func in checks:
        try:
            results.append(check_func())
        except Exception as e:
            print(f"  ❌ Error running check '{name}': {e}")
            results.append(False)
        print()

    print("=" * 60)
    if all(results):
        print("✅ All dependency checks passed!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some dependency checks failed!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
