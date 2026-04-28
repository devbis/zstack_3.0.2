#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    PACKAGE_ROOT = Path(__file__).resolve().parent
    if str(PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_ROOT))

    from extract_iar_project import collect_manifest, find_zstack_root, write_sdcc_header
    from gen_aslink_area_bases import _discover_xcl, _parse_xcl
    from gen_compile_plan import build_compile_plan
else:
    from .extract_iar_project import collect_manifest, find_zstack_root, write_sdcc_header
    from .gen_aslink_area_bases import _discover_xcl, _parse_xcl
    from .gen_compile_plan import build_compile_plan


ZNP_RELATIVE_PROJECT = Path("Projects/zstack/ZNP/CC253x/CC2530.ewp")
ZNP_CONFIG_NAME = "ZNP-with-SBL"
ZNP_PROJECT_NAME = "CC2530ZNP-with-SBL"
DEFAULT_ZNP_PATCH = "firmware_CC2531_CC2530.patch"

HEADER_OVERLAYS = (
    ("cc2530-hal-mcu-h", "Components/hal/target/CC2530ZNP/hal_mcu.h", "Components/hal/target/CC2530EB/hal_mcu.h"),
    ("cc2530-hal-types-h", "Components/hal/target/CC2530ZNP/hal_types.h", "Components/hal/target/CC2530EB/hal_types.h"),
    ("cc2530-hal-board-cfg-h", "Components/hal/target/CC2530ZNP/hal_board_cfg.h", "Components/hal/target/CC2530EB/hal_board_cfg.h"),
    ("cc2530-zcl-sampleapps-ui-h", "Projects/zstack/HomeAutomation/Source/zcl_sampleapps_ui.h"),
    ("cc2530-onboard-h", "Projects/zstack/ZMain/TI2530ZNP/OnBoard.h", "Projects/zstack/ZMain/TI2530DB/OnBoard.h"),
)

HEADER_ALIASES = (
    ("Components/stack/af/af.h", "Components/stack/af/AF.h"),
    ("Components/osal/include/OSAL_NV.h", "Components/osal/include/OSAL_Nv.h"),
    ("Components/osal/include/osal_nv.h", "Components/osal/include/OSAL_Nv.h"),
    ("Components/osal/include/osal.h", "Components/osal/include/OSAL.h"),
    ("Projects/zstack/ZMain/TI2530ZNP/Onboard.h", "Projects/zstack/ZMain/TI2530ZNP/OnBoard.h"),
    ("Projects/zstack/ZMain/TI2530DB/Onboard.h", "Projects/zstack/ZMain/TI2530DB/OnBoard.h"),
    ("Components/zmac/ZMac.h", "Components/zmac/ZMAC.h"),
    ("Components/mt/mt_uart.h", "Components/mt/MT_UART.h"),
    ("Components/stack/gp/gp_common.h", "Components/stack/GP/gp_common.h"),
    ("Components/stack/gp/gp_interface.h", "Components/stack/GP/gp_interface.h"),
    ("Components/stack/gp/cGP_stub.h", "Components/stack/GP/cGP_stub.h"),
    ("Components/stack/gp/dgp_stub.h", "Components/stack/GP/dGP_stub.h"),
)

KNOWN_ZNP_LAYOUT = {
    "project_name": ZNP_PROJECT_NAME,
    "sdcc_model": "large",
    "sdcc_abi": "iar",
    "sdcc_stack_mode": "stack-auto-xstack",
    "sdcc_code_loc": "0x2000",
    "sdcc_code_size": "0x3c800",
    "sdcc_xram_loc": "0x0001",
    "sdcc_xram_size": "0x1AFF",
    "sdcc_xstack_loc": "0x1B00",
    "flash_limit_hex": "0x3c800",
    "code_floor_hex": "0x2000",
}


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def _is_known_znp_project(project_file: Path, config_name: str) -> bool:
    try:
        rel = project_file.resolve().relative_to(find_zstack_root(project_file).resolve())
    except ValueError:
        return False
    return rel == ZNP_RELATIVE_PROJECT and config_name == ZNP_CONFIG_NAME


def _default_patch_path(project_file: Path) -> Path | None:
    sdk_root = find_zstack_root(project_file)
    candidate = sdk_root.parent / DEFAULT_ZNP_PATCH
    return candidate if candidate.exists() else None


def _apply_patch(staged_root: Path, patch_file: Path) -> None:
    result = subprocess.run(
        ["patch", "-d", str(staged_root), "--forward", "-p1", "-i", str(patch_file)],
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        return
    combined = f"{result.stdout}\n{result.stderr}"
    if "Reversed (or previously applied) patch detected" in combined:
        return
    raise SystemExit(f"Failed to apply patch {patch_file}:\n{combined}")


def _copy_sdk_tree(source_root: Path, staged_root: Path) -> None:
    if staged_root.exists():
        shutil.rmtree(staged_root)
    shutil.copytree(source_root, staged_root)


def _prepare_source_file(prepare_script: Path, mode: str, path: Path, *, output_path: Path | None = None) -> None:
    destination = output_path if output_path is not None else path
    _run(
        [
            sys.executable,
            str(prepare_script),
            "--mode",
            mode,
            "--input",
            str(path),
            "--output",
            str(destination),
        ]
    )


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _copy_library_tree(library_paths: list[str], source_root: Path, bundle_lib_root: Path) -> list[str]:
    copied: list[str] = []
    for library in library_paths:
        lib_path = Path(library)
        try:
            rel = lib_path.relative_to(source_root)
        except ValueError:
            rel = Path(lib_path.name)
        destination = bundle_lib_root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lib_path, destination)
        copied.append(str(destination.resolve()))
    return copied


def _generate_manifest_for_bundle(
    staged_root: Path,
    project_rel: Path,
    config_name: str,
    profile: str,
    manifest_path: Path,
    cfg_header_path: Path,
) -> dict[str, Any]:
    project_file = staged_root / project_rel
    if _is_known_znp_project(project_file, config_name):
        prepare_script = staged_root / "Tools" / "sdcc" / "prepare_znp_cc2530_with_sbl.py"
        _run(
            [
                sys.executable,
                str(prepare_script),
                "--profile",
                profile,
                "--output-manifest",
                str(manifest_path),
                "--output-header",
                str(cfg_header_path),
            ],
            cwd=staged_root,
        )
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    if profile != "full":
        raise SystemExit("Non-ZNP imports currently support only --profile full")

    manifest = collect_manifest(project_file, config_name)
    _write_json(manifest_path, manifest)
    write_sdcc_header(cfg_header_path, manifest["sdcc_header_defines"])
    return manifest


def _apply_compile_plan_sources(
    compile_plan: list[dict[str, Any]],
    source_root: Path,
    prepare_script: Path,
) -> int:
    prepared = 0
    for entry in compile_plan:
        if entry.get("skip"):
            continue
        mode = entry.get("prepare")
        if not isinstance(mode, str) or not mode:
            continue
        compile_source = Path(entry["compile_source"])
        if not compile_source.exists():
            continue
        try:
            compile_source.relative_to(source_root)
        except ValueError:
            continue
        _prepare_source_file(prepare_script, mode, compile_source)
        prepared += 1
    return prepared


def _materialize_header_overlays(
    source_root: Path,
    include_root: Path,
    prepare_script: Path,
) -> int:
    produced = 0
    for entry in HEADER_OVERLAYS:
        mode = entry[0]
        selected: Path | None = None
        rel_path: Path | None = None
        for candidate in entry[1:]:
            candidate_path = source_root / candidate
            if candidate_path.exists():
                selected = candidate_path
                rel_path = Path(candidate)
                break
        if selected is None or rel_path is None:
            continue
        _prepare_source_file(prepare_script, mode, selected)
        include_path = include_root / rel_path
        _prepare_source_file(prepare_script, "copy", selected, output_path=include_path)
        produced += 1
    return produced


def _materialize_header_aliases(
    source_root: Path,
    include_root: Path,
    prepare_script: Path,
) -> int:
    produced = 0
    for alias_rel, source_rel in HEADER_ALIASES:
        source_path = source_root / source_rel
        if not source_path.exists():
            continue
        alias_path = source_root / alias_rel
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        _prepare_source_file(prepare_script, "copy", source_path, output_path=alias_path)
        include_alias = include_root / alias_rel
        _prepare_source_file(prepare_script, "copy", source_path, output_path=include_alias)
        produced += 1
    return produced


def _xcl_placements_from_manifest(manifest: dict[str, Any], manifest_path: Path) -> tuple[str | None, dict[str, Any]]:
    xcl_path = _discover_xcl(manifest, manifest_path)
    if xcl_path is None:
        return None, {}
    placements = _parse_xcl(
        xcl_path,
        {
            "_CODE_START": int(KNOWN_ZNP_LAYOUT["sdcc_code_loc"], 0),
            "_CODE_END": int(KNOWN_ZNP_LAYOUT["sdcc_code_loc"], 0)
            + int(KNOWN_ZNP_LAYOUT["sdcc_code_size"], 0)
            - 1,
            "_XDATA_START": int(KNOWN_ZNP_LAYOUT["sdcc_xram_loc"], 0),
            "_XDATA_END": int(KNOWN_ZNP_LAYOUT["sdcc_xram_loc"], 0)
            + int(KNOWN_ZNP_LAYOUT["sdcc_xram_size"], 0)
            - 1,
        },
    )
    return str(xcl_path), placements


def build_layout_metadata(
    manifest: dict[str, Any],
    manifest_path: Path,
    *,
    project_file: Path,
    config_name: str,
    profile: str,
) -> dict[str, Any]:
    xcl_path, placements = _xcl_placements_from_manifest(manifest, manifest_path)
    payload: dict[str, Any] = {
        "project_file": str(project_file),
        "configuration": config_name,
        "profile": profile,
        "xcl_path": xcl_path,
        "placements": placements,
    }
    if _is_known_znp_project(project_file, config_name):
        payload.update(KNOWN_ZNP_LAYOUT)
        payload["validation"] = {
            "flash_limit_hex": KNOWN_ZNP_LAYOUT["flash_limit_hex"],
            "code_floor_hex": KNOWN_ZNP_LAYOUT["code_floor_hex"],
        }
    return payload


def write_project_cmake(
    path: Path,
    *,
    profile: str,
    project_name: str,
    manifest_path: Path,
    layout_path: Path,
    include_root: Path,
    source_root: Path,
    converted_lib_dir: Path,
    generated_cfg_header: Path,
    compile_plan_path: Path,
) -> None:
    content = f"""# Auto-generated by Tools/sdcc/iar_import.py
set(ZSTACK_IMPORTED_PROFILE "{profile}")
set(ZSTACK_IMPORTED_PROJECT_NAME "{project_name}")
set(ZSTACK_IMPORTED_BUNDLE_ROOT "${{CMAKE_CURRENT_LIST_DIR}}/..")
set(ZSTACK_IMPORTED_SOURCE_ROOT "${{ZSTACK_IMPORTED_BUNDLE_ROOT}}/src")
set(ZSTACK_IMPORTED_INCLUDE_ROOT "${{ZSTACK_IMPORTED_BUNDLE_ROOT}}/include")
set(ZSTACK_IMPORTED_METADATA_DIR "${{ZSTACK_IMPORTED_BUNDLE_ROOT}}/metadata")
set(ZSTACK_IMPORTED_LIB_ROOT "${{ZSTACK_IMPORTED_BUNDLE_ROOT}}/libs")
set(ZSTACK_IMPORTED_MANIFEST "${{ZSTACK_IMPORTED_METADATA_DIR}}/{manifest_path.name}")
set(ZSTACK_IMPORTED_LAYOUT "${{ZSTACK_IMPORTED_BUNDLE_ROOT}}/{layout_path.name}")
set(ZSTACK_IMPORTED_COMPILE_PLAN "${{ZSTACK_IMPORTED_BUNDLE_ROOT}}/{compile_plan_path.name}")
set(ZSTACK_IMPORTED_GENERATED_CFG_HEADER "${{ZSTACK_IMPORTED_INCLUDE_ROOT}}/{generated_cfg_header.name}")
set(ZSTACK_IMPORTED_CONVERTED_LIB_DIR "${{ZSTACK_IMPORTED_LIB_ROOT}}/converted")
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_report(
    report_json: Path,
    report_txt: Path,
    *,
    project_name: str,
    profile: str,
    source_files: int,
    prepared_entries: int,
    header_overlays: int,
    header_aliases: int,
    libraries: int,
    converter_manifest: dict[str, Any] | None,
) -> None:
    converter_emitted = 0
    converter_unresolved = 0
    if converter_manifest is not None:
        converter_emitted = len(converter_manifest.get("emitted_artifacts", []))
        converter_unresolved = len(converter_manifest.get("unresolved_symbols", []))
    payload = {
        "project_name": project_name,
        "profile": profile,
        "source_files": source_files,
        "prepared_entries": prepared_entries,
        "header_overlays": header_overlays,
        "header_aliases": header_aliases,
        "libraries": libraries,
        "converter_emitted_artifacts": converter_emitted,
        "converter_unresolved_symbols": converter_unresolved,
    }
    _write_json(report_json, payload)
    lines = [
        "iar import staged",
        f"project={project_name}",
        f"profile={profile}",
        f"source_files={source_files}",
        f"prepared_entries={prepared_entries}",
        f"header_overlays={header_overlays}",
        f"header_aliases={header_aliases}",
        f"libraries={libraries}",
        f"converter_emitted_artifacts={converter_emitted}",
        f"converter_unresolved_symbols={converter_unresolved}",
    ]
    report_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy_override_file(source_root: Path, manifest_name: str, overrides_dir: Path) -> None:
    source_override = source_root / "Tools" / "sdcc" / "overrides" / f"{manifest_name}.yaml"
    if not source_override.exists():
        return
    overrides_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_override, overrides_dir / source_override.name)


def _import_project(args: argparse.Namespace) -> None:
    project_file = args.project.resolve()
    sdk_root = find_zstack_root(project_file)
    source_project_rel = project_file.relative_to(sdk_root)
    patch_file = args.patch.resolve() if args.patch else _default_patch_path(project_file)

    out_dir = args.out_dir.resolve()
    source_root = out_dir / "src"
    include_root = out_dir / "include"
    metadata_dir = out_dir / "metadata"
    libs_original_root = out_dir / "libs" / "original"
    libs_converted_root = out_dir / "libs" / "converted"
    cmake_dir = out_dir / "cmake"

    manifest_path = metadata_dir / "manifest.json"
    raw_manifest_path = metadata_dir / "manifest.raw.json"
    cfg_header_path = include_root / f"{project_file.stem.lower()}-{args.config.lower()}-sdcc-cfg.h"
    compile_plan_path = out_dir / "compile-plan.json"
    layout_path = out_dir / "layout.json"
    project_cmake_path = cmake_dir / "project.cmake"
    report_json_path = out_dir / "report.json"
    report_txt_path = out_dir / "report.txt"

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _copy_sdk_tree(sdk_root, source_root)
    if patch_file is not None:
        _apply_patch(source_root, patch_file)

    prepare_script = source_root / "Tools" / "sdcc" / "prepare_source.py"
    manifest = _generate_manifest_for_bundle(
        source_root,
        source_project_rel,
        args.config,
        args.profile,
        raw_manifest_path,
        cfg_header_path,
    )

    libraries = _copy_library_tree(manifest.get("iar_libraries", []), source_root, libs_original_root)
    manifest["iar_libraries"] = libraries
    manifest["import_bundle_root"] = str(out_dir)
    manifest["generated_include_dirs"] = [str(include_root)]
    manifest["sdcc_generated_cfg_header"] = str(cfg_header_path)
    manifest["profile"] = args.profile

    _write_json(manifest_path, manifest)

    compile_plan = build_compile_plan(manifest)
    _write_json(compile_plan_path, compile_plan)

    prepared_entries = _apply_compile_plan_sources(compile_plan, source_root, prepare_script)
    header_overlays = _materialize_header_overlays(source_root, include_root, prepare_script)
    header_aliases = _materialize_header_aliases(source_root, include_root, prepare_script)

    layout = build_layout_metadata(
        manifest,
        manifest_path,
        project_file=source_root / source_project_rel,
        config_name=args.config,
        profile=args.profile,
    )
    _write_json(layout_path, layout)

    _copy_override_file(source_root, manifest_path.stem, out_dir / "overrides")

    converter_manifest_payload: dict[str, Any] | None = None
    converter_cli = source_root / "Tools" / "sdcc" / "iar2sdcc" / "cli.py"
    if manifest.get("iar_libraries"):
        converter_env = os.environ.copy()
        if args.sdcc_toolchain_root:
            toolchain_root = args.sdcc_toolchain_root.resolve()
            converter_env["IAR2SDCC_SDCC_BIN"] = str(toolchain_root / "bin" / "sdcc")
            converter_env["IAR2SDCC_SDAS_BIN"] = str(toolchain_root / "bin" / "sdas8051")
        _run(
            [
                sys.executable,
                str(converter_cli),
                "convert",
                "--manifest",
                str(manifest_path),
                "--out-dir",
                str(libs_converted_root),
            ],
            env=converter_env,
        )
        converted_manifest = libs_converted_root / "manifest.json"
        if converted_manifest.exists():
            converter_manifest_payload = json.loads(converted_manifest.read_text(encoding="utf-8"))
            manifest["converted_library_manifest"] = str(converted_manifest)
            _write_json(manifest_path, manifest)

    project_name = layout.get("project_name") or args.config
    write_project_cmake(
        project_cmake_path,
        profile=args.profile,
        project_name=str(project_name),
        manifest_path=manifest_path,
        layout_path=layout_path,
        include_root=include_root,
        source_root=source_root,
        converted_lib_dir=libs_converted_root,
        generated_cfg_header=cfg_header_path,
        compile_plan_path=compile_plan_path,
    )

    top_level_manifest = out_dir / "manifest.json"
    top_level_manifest.write_text(manifest_path.read_text(encoding="utf-8"), encoding="utf-8")

    _write_report(
        report_json_path,
        report_txt_path,
        project_name=str(project_name),
        profile=args.profile,
        source_files=len(manifest.get("source_files", [])),
        prepared_entries=prepared_entries,
        header_overlays=header_overlays,
        header_aliases=header_aliases,
        libraries=len(libraries),
        converter_manifest=converter_manifest_payload,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import an IAR Z-Stack project into a self-contained SDCC/CMake-ready bundle.")
    parser.add_argument("--project", type=Path, required=True, help="Path to the IAR .ewp project file")
    parser.add_argument("--config", required=True, help="IAR configuration name")
    parser.add_argument("--profile", default="full", choices=("full", "balanced", "lean"))
    parser.add_argument("--out-dir", type=Path, required=True, help="Output bundle directory")
    parser.add_argument("--patch", type=Path, help="Optional patch applied after staging the SDK tree")
    parser.add_argument(
        "--sdcc-toolchain-root",
        type=Path,
        help="Optional SDCC toolchain root used by iar2sdcc to emit real .rel artifacts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _import_project(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
