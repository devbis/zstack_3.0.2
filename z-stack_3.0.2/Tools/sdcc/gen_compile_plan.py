#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUBSTITUTIONS = {
    "Components/hal/target/CC2530EB/hal_sleep.c": {
        "prepare": "cc2530-hal-sleep",
    },
    "Components/hal/target/CC2530EB/hal_startup.c": {
        "prepare": "cc2530-hal-startup",
    },
    "Components/osal/mcu/cc2530/OSAL_Nv.c": {
        "prepare": "cc2530-osal-nv",
    },
    "Components/osal/mcu/cc2530/OSAL_Math.s51": {
        "compile_source": "Components/osal/mcu/cc2530/OSAL_Math.c",
        "prepare": "cc2530-osal-math",
    },
    "Projects/zstack/ZMain/TI2530DB/OnBoard.c": {
        "prepare": "cc2530-onboard",
    },
    "Projects/zstack/ZMain/TI2530DB/ZMain.c": {
        "prepare": "cc2530-zmain",
    },
    "Components/hal/target/CC2530EB/hal_lcd.c": {
        "prepare": "cc2530-hal-lcd",
    },
    "Components/mt/MT_AF.c": {
        "prepare": "cc2530-mt-af",
    },
    "Components/stack/sapi/sapi.c": {
        "prepare": "cc2530-sapi",
    },
    "Projects/zstack/HomeAutomation/SampleLight/Source/zcl_samplelight.c": {
        "prepare": "cc2530-zcl-samplelight",
    },
    "Projects/zstack/HomeAutomation/SampleLight/Source/zcl_samplelight_data.c": {
        "prepare": "cc2530-zcl-samplelight-data",
    },
}

COPY_PREPARE_PREFIXES = (
    "Components/hal/target/CC2530EB/",
    "Projects/zstack/HomeAutomation/Source/",
)

CHIPCON_CSTARTUP_SUBSTITUTION = {
    "skip": True,
    "skip_reason": "replaced by SDCC startup plus __sdcc_external_startup()",
}


def _default_substitution(source_rel: str) -> dict[str, Any]:
    if source_rel.startswith("Projects/zstack/ZMain/") and source_rel.endswith("/chipcon_cstartup.s51"):
        return CHIPCON_CSTARTUP_SUBSTITUTION
    if not source_rel.endswith(".c"):
        return {}
    for prefix in COPY_PREPARE_PREFIXES:
        if source_rel.startswith(prefix):
            return {"prepare": "copy"}
    return {}


def _override_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for item in manifest.get("sdcc_compile_overrides", []):
        source = item.get("source")
        if isinstance(source, str):
            mapping[source] = item
    return mapping


def _match_override(
    overrides: dict[str, dict[str, Any]],
    original_source: str,
    compile_source: str,
) -> dict[str, Any]:
    return overrides.get(original_source) or overrides.get(compile_source) or {}


def _build_entry(
    *,
    source_path: Path,
    compile_source: Path,
    substitution: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    entry = {
        "source": str(source_path),
        "compile_source": str(compile_source),
        "codeseg": override.get("codeseg"),
        "constseg": override.get("constseg"),
        "prepare": substitution.get("prepare"),
        "skip": bool(substitution.get("skip", False)),
        "skip_reason": substitution.get("skip_reason"),
    }

    if compile_source.suffix == ".s51" and not substitution:
        entry["error"] = f"Unsupported IAR assembler source: {source_path}"

    return entry


def _extra_source_entries(
    manifest: dict[str, Any],
    overrides: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    extra_entries: list[dict[str, Any]] = []
    for item in manifest.get("sdcc_extra_sources", []):
        substitution: dict[str, Any] = {}
        if isinstance(item, str):
            source_path = Path(item)
            compile_source = source_path
        elif isinstance(item, dict):
            source = item.get("source")
            if not isinstance(source, str):
                continue
            source_path = Path(source)
            compile_source = Path(item.get("compile_source", source))
            substitution = {
                "prepare": item.get("prepare"),
                "skip": item.get("skip"),
                "skip_reason": item.get("skip_reason"),
            }
        else:
            continue

        override = _match_override(overrides, str(source_path), str(compile_source))
        extra_entries.append(
            _build_entry(
                source_path=source_path,
                compile_source=compile_source,
                substitution=substitution,
                override=override,
            )
        )
    return extra_entries


def build_compile_plan(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    repo_root = Path(manifest["repo_root"])
    overrides = _override_map(manifest)
    plan: list[dict[str, Any]] = []

    for source in manifest.get("source_files", []):
        source_path = Path(source)
        try:
            source_rel = source_path.relative_to(repo_root).as_posix()
        except ValueError:
            source_rel = source_path.as_posix()

        substitution = SUBSTITUTIONS.get(source_rel, _default_substitution(source_rel))
        compile_source = source_path
        if "compile_source" in substitution:
            compile_source = repo_root / substitution["compile_source"]

        override = _match_override(overrides, str(source_path), str(compile_source))
        plan.append(
            _build_entry(
                source_path=source_path,
                compile_source=compile_source,
                substitution=substitution,
                override=override,
            )
        )

    plan.extend(_extra_source_entries(manifest, overrides))
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the per-source SDCC compile plan for a Z-Stack manifest.")
    parser.add_argument("--manifest", required=True, type=Path, help="Input manifest path")
    parser.add_argument("--output", required=True, type=Path, help="Output compile-plan JSON path")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    plan = build_compile_plan(manifest)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
