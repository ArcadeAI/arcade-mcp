"""
Discovery utilities for Arcade Tools.

Provides modular, testable functions to discover toolkits and local tool files,
load modules, collect tools, and build a ToolCatalog.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from loguru import logger

from arcade_core.catalog import ToolCatalog
from arcade_core.parse import get_tools_from_file
from arcade_core.toolkit import Toolkit, ToolkitLoadError

DISCOVERY_PATTERNS = ["*.py", "tools/*.py", "arcade_tools/*.py", "tools/**/*.py"]
FILTER_PATTERNS = ["_test.py", "test_*.py", "__pycache__", "*.lock", "*.egg-info", "*.pyc"]


def normalize_package_name(package_name: str) -> str:
    """Normalize a package name for import resolution."""
    return package_name.lower().replace("-", "_")


def load_toolkit_from_package(package_name: str, show_packages: bool = False) -> Toolkit:
    """Attempt to load a Toolkit from an installed package name."""
    toolkit = Toolkit.from_package(package_name)
    if show_packages:
        logger.info(f"Loading package: {toolkit.name}")
    return toolkit


def load_package(package_name: str, show_packages: bool = False) -> Toolkit:
    """Load a toolkit for a specific package name.

    Raises ToolkitLoadError if the package is not found.
    """
    normalized = normalize_package_name(package_name)
    try:
        return load_toolkit_from_package(normalized, show_packages)
    except ToolkitLoadError:
        return load_toolkit_from_package(f"arcade_{normalized}", show_packages)


def find_candidate_tool_files(root: Path | None = None) -> list[Path]:
    """Find candidate Python files for auto-discovery in common locations."""
    cwd = root or Path.cwd()

    candidates: list[Path] = []
    for pattern in DISCOVERY_PATTERNS:
        candidates.extend(cwd.glob(pattern))
    # Deduplicate candidates (same file might match multiple patterns)
    unique_candidates = list(set(candidates))
    # Filter out private, cache, and tests
    return [
        p for p in unique_candidates if not any(p.match(pattern) for pattern in FILTER_PATTERNS)
    ]


def analyze_files_for_tools(files: list[Path]) -> list[tuple[Path, list[str]]]:
    """Parse files with a fast AST pass to find declared @tool function names."""
    results: list[tuple[Path, list[str]]] = []
    for file_path in files:
        try:
            names = get_tools_from_file(file_path)
            if names:
                logger.info(f"Found {len(names)} tool(s) in {file_path.name}: {', '.join(names)}")
                results.append((file_path, names))
        except Exception:
            logger.exception(f"Could not parse {file_path}")
    return results


def load_module_from_path(file_path: Path) -> ModuleType:
    """Dynamically import a Python module from a file path."""
    import sys

    # Add the directory containing the file to sys.path temporarily
    # This allows local imports to work
    file_dir = str(file_path.parent)
    path_added = False
    if file_dir not in sys.path:
        sys.path.insert(0, file_dir)
        path_added = True

    try:
        spec = importlib.util.spec_from_file_location(
            f"_tools_{file_path.stem}",
            file_path,
        )
        if not spec or not spec.loader:
            raise ToolkitLoadError(f"Unable to create import spec for {file_path}")

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            logger.exception(f"Failed to load {file_path}")
            raise ToolkitLoadError(f"Failed to load {file_path}")

        return module
    finally:
        # Remove the path we added
        if path_added and file_dir in sys.path:
            sys.path.remove(file_dir)


def collect_tools_from_modules(
    files_with_tools: list[tuple[Path, list[str]]],
) -> list[tuple[Any, ModuleType]]:
    """Load modules and collect the expected tool callables.

    Returns a list of (callable, module) pairs.
    """
    discovered: list[tuple[Any, ModuleType]] = []

    for file_path, expected_names in files_with_tools:
        logger.debug(f"Loading tools from {file_path}...")
        try:
            module = load_module_from_path(file_path)
        except ToolkitLoadError:
            continue

        for name in expected_names:
            if hasattr(module, name):
                attr = getattr(module, name)
                if callable(attr) and hasattr(attr, "__tool_name__"):
                    discovered.append((attr, module))
                else:
                    logger.warning(
                        f"Expected {name} to be a tool but it wasn't (missing __tool_name__)\n\n"
                    )
    return discovered


def build_minimal_toolkit(
    server_name: str | None,
    server_version: str | None,
    description: str | None = None,
) -> Toolkit:
    """Create a minimal Toolkit to host locally discovered tools."""
    name = server_name or "ArcadeMCP"
    version = server_version or "0.1.0dev"
    pkg = f"{name}.{Path.cwd().name}"
    desc = description or f"MCP Server for {name} version {version}"
    return Toolkit(name=name, package_name=pkg, version=version, description=desc)


def build_catalog_from_toolkits(toolkits: list[Toolkit]) -> ToolCatalog:
    """Create a ToolCatalog and add the provided toolkits."""
    catalog = ToolCatalog()
    for tk in toolkits:
        catalog.add_toolkit(tk)
    return catalog


def add_discovered_tools(
    catalog: ToolCatalog,
    toolkit: Toolkit,
    tools: list[tuple[Any, ModuleType]],
) -> None:
    """Add discovered local tools to the catalog, preserving module context."""
    for tool_func, module in tools:
        if module.__name__ not in __import__("sys").modules:
            __import__("sys").modules[module.__name__] = module
        catalog.add_tool(tool_func, toolkit, module)


def load_toolkits_for_option(tool_package: str, show_packages: bool = False) -> list[Toolkit]:
    """
    Load toolkits for a given package option.

    Args:
        tool_package: Package name or comma-separated list of package names
        show_packages: Whether to log loaded packages

    Returns:
        List of loaded toolkits
    """
    toolkits = []
    packages = [p.strip() for p in tool_package.split(",")]

    for package in packages:
        try:
            toolkit = load_package(package, show_packages)
            toolkits.append(toolkit)
        except ToolkitLoadError as e:
            logger.warning(f"Failed to load package '{package}': {e}")

    return toolkits


def load_all_installed_toolkits(show_packages: bool = False) -> list[Toolkit]:
    """
    Discover and load all installed arcade toolkits.

    Args:
        show_packages: Whether to log loaded packages

    Returns:
        List of all installed toolkits
    """
    toolkits = Toolkit.find_all_arcade_toolkits()

    if show_packages:
        for toolkit in toolkits:
            logger.info(f"Loading package: {toolkit.name}")

    return toolkits


def discover_tools(
    tool_package: str | None = None,
    show_packages: bool = False,
    discover_installed: bool = False,
    server_name: str | None = None,
    server_version: str | None = None,
) -> ToolCatalog:
    """High-level discovery that returns a ToolCatalog.

    This function is pure (does not sys.exit); callers should handle errors.
    """
    # 1) Package-based discovery
    if tool_package:
        toolkits = load_toolkits_for_option(tool_package, show_packages)
        return build_catalog_from_toolkits(toolkits)

    # 2) Discover all installed packages
    if discover_installed:
        toolkits = load_all_installed_toolkits(show_packages)
        return build_catalog_from_toolkits(toolkits)

    # 3) Local file discovery
    logger.info("Auto-discovering tools from current directory")
    files = find_candidate_tool_files()
    if not files:
        # Return empty catalog; caller can decide how to handle
        return ToolCatalog()

    files_with_tools = analyze_files_for_tools(files)
    if not files_with_tools:
        return ToolCatalog()

    discovered = collect_tools_from_modules(files_with_tools)
    catalog = ToolCatalog()
    toolkit = build_minimal_toolkit(server_name, server_version)
    add_discovered_tools(catalog, toolkit, discovered)
    return catalog
