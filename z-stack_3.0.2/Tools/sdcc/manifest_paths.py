#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PATH_KEYS = (
    "project_file",
    "project_dir",
)

PATH_LIST_KEYS = (
    "include_dirs",
    "source_files",
    "header_files",
    "cfg_files",
    "preinclude_files",
    "xcl_file",
    "iar_libraries",
    "all_project_files",
)


def _rebase_path(value: str, old_root: Path, new_root: Path) -> str:
    try:
        relative = Path(value).relative_to(old_root)
    except ValueError:
        return value
    return str(new_root / relative)


def _rebase_compile_overrides(
    values: list[Any],
    old_root: Path,
    new_root: Path,
) -> list[Any]:
    rebased: list[Any] = []
    for item in values:
        if not isinstance(item, dict):
            rebased.append(item)
            continue
        rewritten = dict(item)
        source = item.get("source")
        if isinstance(source, str):
            rewritten["source"] = _rebase_path(source, old_root, new_root)
        rebased.append(rewritten)
    return rebased


def _rebase_source_entries(
    values: list[Any],
    old_root: Path,
    new_root: Path,
) -> list[Any]:
    rebased: list[Any] = []
    for item in values:
        if isinstance(item, str):
            rebased.append(_rebase_path(item, old_root, new_root))
            continue
        if not isinstance(item, dict):
            rebased.append(item)
            continue
        rewritten = dict(item)
        for key in ("source", "compile_source"):
            value = item.get(key)
            if isinstance(value, str):
                rewritten[key] = _rebase_path(value, old_root, new_root)
        rebased.append(rewritten)
    return rebased


def rebase_manifest_paths(manifest: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    rebased = dict(manifest)
    old_root_value = manifest.get("repo_root")
    if not old_root_value:
        rebased["repo_root"] = str(repo_root)
        return rebased

    old_root = Path(old_root_value)
    new_root = Path(repo_root)

    rebased["repo_root"] = str(new_root)

    for key in PATH_KEYS:
        value = manifest.get(key)
        if isinstance(value, str):
            rebased[key] = _rebase_path(value, old_root, new_root)

    for key in PATH_LIST_KEYS:
        values = manifest.get(key)
        if isinstance(values, list):
            rebased[key] = [
                _rebase_path(value, old_root, new_root) if isinstance(value, str) else value
                for value in values
            ]

    overrides = manifest.get("sdcc_compile_overrides")
    if isinstance(overrides, list):
        rebased["sdcc_compile_overrides"] = _rebase_compile_overrides(overrides, old_root, new_root)

    extra_sources = manifest.get("sdcc_extra_sources")
    if isinstance(extra_sources, list):
        rebased["sdcc_extra_sources"] = _rebase_source_entries(extra_sources, old_root, new_root)

    return rebased


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize Z-Stack manifest paths for the current checkout.")
    parser.add_argument("--manifest", required=True, type=Path, help="Input manifest path")
    parser.add_argument("--output", required=True, type=Path, help="Output manifest path")
    parser.add_argument(
        "--repo-root",
        required=True,
        type=Path,
        help="Current Z-Stack repository root used to rewrite absolute paths",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rebased = rebase_manifest_paths(manifest, args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rebased, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
