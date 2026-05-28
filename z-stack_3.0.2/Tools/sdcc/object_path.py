#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def compute_object_relpath(compile_source: Path, workspace_root: Path) -> Path:
    resolved_source = compile_source.resolve()
    try:
        rel_path = resolved_source.relative_to(workspace_root.resolve())
    except ValueError:
        digest = hashlib.sha1(str(resolved_source).encode("utf-8")).hexdigest()[:12]
        rel_path = Path("external") / digest / resolved_source.name
    if compile_source.suffix == ".c":
        return rel_path.with_suffix(".rel")
    if compile_source.suffix == ".asm":
        return rel_path.with_suffix(".rel")
    raise ValueError(f"Unsupported compile source type: {compile_source}")


def compute_object_path(*, compile_source: Path, workspace_root: Path, obj_dir: Path) -> Path:
    return obj_dir / compute_object_relpath(compile_source, workspace_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute the SDCC object path for a compile source.")
    parser.add_argument("--compile-source", required=True, type=Path)
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--obj-dir", required=True, type=Path)
    args = parser.parse_args()

    print(
        compute_object_path(
            compile_source=args.compile_source,
            workspace_root=args.workspace_root,
            obj_dir=args.obj_dir,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
