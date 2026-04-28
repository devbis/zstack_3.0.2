#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from extract_iar_project import classify_sdcc_defines, collect_manifest, write_sdcc_header


SCRIPT_DIR = Path(__file__).resolve().parent
ZSTACK_DIR = SCRIPT_DIR.parent.parent
PROJECT_FILE = ZSTACK_DIR / "Projects" / "zstack" / "ZNP" / "CC253x" / "CC2530.ewp"
CONFIG_NAME = "ZNP-with-SBL"
DEVICE_DEFINE = "FIRMWARE_CC2530"
FULL_PROFILE = "full"
BALANCED_PROFILE = "balanced"
LEAN_PROFILE = "lean"
VOLATILE_NV_SHIM = str((SCRIPT_DIR / "shims" / "OSAL_Nv_volatile.c").resolve())
MT_AF_BALANCED_SHIM = str((SCRIPT_DIR / "shims" / "MT_AF_balanced.c").resolve())
MT_AF_LEAN_SHIM = str((SCRIPT_DIR / "shims" / "MT_AF_lean.c").resolve())
COMMON_HEADER_LINES = (
    "/* SDCC ZNP profile: rely on linker/code window, do not emit flash reservation sentinels. */",
    "#define SDCC_SKIP_FLASH_RESERVATION_SENTINELS 1",
)

BALANCED_EXCLUDED_SOURCES = (
    "Components/stack/zcl/zcl_key_establish.c",
    "Components/stack/bdb/bdb_touchlink.c",
    "Components/stack/bdb/bdb_touchlink_initiator.c",
    "Components/stack/bdb/bdb_touchlink_target.c",
    "Components/stack/bdb/bdb_FindingAndBinding.c",
    "Components/stack/sapi/sapi.c",
    "Components/mt/MT_SAPI.c",
    "Components/mt/MT_GP.c",
    "Components/mt/MT_APP_CONFIG.c",
)
BALANCED_REPLACED_SOURCES = {
    "Components/mt/MT_AF.c": MT_AF_BALANCED_SHIM,
    "Components/osal/mcu/cc2530/OSAL_Nv.c": VOLATILE_NV_SHIM,
}

BALANCED_HEADER_LINES = (
    "/* SDCC balanced profile: keep core ZNP paths, trim oversized ZigBee 3.0 optionals. */",
    "#define SDCC_VOLATILE_NV_SHIM 1",
    "#undef INTER_PAN",
    "#undef ZCL_KEY_ESTABLISH",
    "#undef TC_LINKKEY_JOIN",
    "#undef FEATURE_SYSTEM_STATS",
    "#undef NV_RESTORE",
    "#undef NV_INIT",
    "#undef MT_GP_CB_FUNC",
    "#undef MT_APP_CNF_FUNC",
    "#undef MT_APP_FUNC",
    "#undef MT_UTIL_FUNC",
    "#undef MT_SAPI_FUNC",
    "#undef MT_SAPI_CB_FUNC",
    "#undef MT_ZDO_MGMT",
    "#undef MT_ZDO_EXTENSIONS",
    "#undef MT_SYS_KEY_MANAGEMENT",
    "#define MT_SYS_KEY_MANAGEMENT 0",
    "#undef ZSTACK_DEVICE_BUILD",
    "#define ZSTACK_DEVICE_BUILD DEVICE_BUILD_COORDINATOR",
)

LEAN_EXCLUDED_SOURCES = (
    "Components/stack/zcl/zcl_key_establish.c",
    "Components/stack/bdb/bdb_touchlink.c",
    "Components/stack/bdb/bdb_touchlink_initiator.c",
    "Components/stack/bdb/bdb_touchlink_target.c",
    "Components/stack/bdb/bdb_FindingAndBinding.c",
    "Components/stack/sapi/sapi.c",
    "Components/mt/MT_SAPI.c",
    "Components/mt/MT_GP.c",
    "Components/mt/MT_APP_CONFIG.c",
)
LEAN_REPLACED_SOURCES = {
    "Components/mt/MT_AF.c": MT_AF_LEAN_SHIM,
    "Components/osal/mcu/cc2530/OSAL_Nv.c": VOLATILE_NV_SHIM,
}

LEAN_HEADER_LINES = (
    "/* SDCC lean profile: trade optional ZNP features for smaller code/XDATA. */",
    "#define SDCC_VOLATILE_NV_SHIM 1",
    "#undef AMI_PROFILE",
    "#undef SE_PROFILE",
    "#undef TC_LINKKEY_JOIN",
    "#undef FEATURE_SYSTEM_STATS",
    "#undef INTER_PAN",
    "#undef NV_RESTORE",
    "#undef NV_INIT",
    "#undef REFLECTOR",
    "#undef MT_GP_CB_FUNC",
    "#undef MT_AF_FUNC",
    "#undef MT_SAPI_FUNC",
    "#undef MT_SAPI_CB_FUNC",
    "#undef MT_APP_CNF_FUNC",
    "#undef MT_UTIL_FUNC",
    "#undef MT_ZDO_MGMT",
    "#undef MT_ZDO_EXTENSIONS",
    "#undef MT_SYS_KEY_MANAGEMENT",
    "#define MT_SYS_KEY_MANAGEMENT 0",
    "#undef ZIGBEE_FRAGMENTATION",
    "#undef MT_APP_FUNC",
    "#undef ZCL_KEY_ESTABLISH",
    "#undef ZDSECMGR_TC_DEVICE_MAX",
    "#define ZDSECMGR_TC_DEVICE_MAX 1",
    "#undef ZSTACK_DEVICE_BUILD",
    "#define ZSTACK_DEVICE_BUILD DEVICE_BUILD_COORDINATOR",
)


def _exclude_sources(source_files: Iterable[str], suffixes: Iterable[str]) -> list[str]:
    excluded = tuple(suffixes)
    return [path for path in source_files if not path.endswith(excluded)]


def _replace_sources(source_files: Iterable[str], replacements: dict[str, str]) -> list[str]:
    updated: list[str] = []
    for path in source_files:
        replacement = next((dst for suffix, dst in replacements.items() if path.endswith(suffix)), None)
        updated.append(replacement if replacement is not None else path)
    return updated


def apply_profile(manifest: dict[str, object], profile: str) -> tuple[dict[str, object], list[str]]:
    profile = profile.lower()
    manifest["profile"] = profile

    if profile == FULL_PROFILE:
        return manifest, list(COMMON_HEADER_LINES)

    if profile == BALANCED_PROFILE:
        manifest["source_files"] = _exclude_sources(
            manifest["source_files"],
            BALANCED_EXCLUDED_SOURCES,
        )
        manifest["source_files"] = _replace_sources(
            manifest["source_files"],
            BALANCED_REPLACED_SOURCES,
        )
        manifest["profile_notes"] = [
            "balanced profile disables inter-PAN, touchlink, CBKE/key-establishment and SAPI paths",
            "balanced profile keeps a reduced MT AF command path, but disables MT app/util, MT ZDO management/extensions, MT key-management commands and system stats",
            "balanced profile replaces flash-backed OSAL NV with a volatile shim",
            "balanced profile constrains ZNP to coordinator-only stack build",
        ]
        return manifest, [*COMMON_HEADER_LINES, *BALANCED_HEADER_LINES]

    if profile != LEAN_PROFILE:
        raise ValueError(f"Unsupported profile: {profile}")

    manifest["source_files"] = _exclude_sources(
        manifest["source_files"],
        LEAN_EXCLUDED_SOURCES,
    )
    manifest["source_files"] = _replace_sources(
        manifest["source_files"],
        LEAN_REPLACED_SOURCES,
    )
    manifest["profile_notes"] = [
        "lean profile disables optional MT/SAPI/inter-PAN/key-establishment sources",
        "lean profile constrains ZNP to coordinator-only stack build",
        "lean profile replaces MT AF callback machinery with no-op stubs",
        "lean profile replaces flash-backed OSAL NV with a volatile in-RAM shim",
    ]
    return manifest, [*COMMON_HEADER_LINES, *LEAN_HEADER_LINES]


def prepare_manifest(profile: str = FULL_PROFILE) -> tuple[dict[str, object], list[str]]:
    manifest = collect_manifest(PROJECT_FILE, CONFIG_NAME)
    preinclude_files = manifest.get("preinclude_files", [])
    if not preinclude_files:
        raise SystemExit(
            "Patched ZNP preinclude was not found. Apply firmware_CC2531_CC2530.patch first."
        )

    missing = [path for path in preinclude_files if not Path(path).is_file()]
    if missing:
        raise SystemExit(
            "Missing patched preinclude files:\n" + "\n".join(f"  {path}" for path in missing)
        )

    derived_defines = [*manifest["cfg_defines"], DEVICE_DEFINE]
    sdcc_cli_defines, sdcc_header_defines = classify_sdcc_defines(derived_defines)

    manifest["defines"] = [DEVICE_DEFINE]
    manifest["all_defines"] = derived_defines
    manifest["sdcc_cli_defines"] = sdcc_cli_defines
    manifest["sdcc_header_defines"] = sdcc_header_defines
    manifest["device_define"] = DEVICE_DEFINE
    return apply_profile(manifest, profile)


def write_profile_header(output_path: Path, manifest: dict[str, object], extra_lines: list[str]) -> None:
    write_sdcc_header(output_path, manifest["sdcc_header_defines"])
    if not extra_lines:
        return

    with output_path.open("a", encoding="utf-8") as fp:
        fp.write("\n")
        for line in extra_lines:
            fp.write(f"{line}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a derived SDCC manifest for patched Z-Stack CC2530 ZNP-with-SBL."
    )
    parser.add_argument("--output-manifest", required=True, type=Path)
    parser.add_argument("--output-header", required=True, type=Path)
    parser.add_argument(
        "--profile",
        choices=(FULL_PROFILE, BALANCED_PROFILE, LEAN_PROFILE),
        default=FULL_PROFILE,
        help="Select the SDCC-oriented ZNP profile to derive from the IAR project.",
    )
    args = parser.parse_args()

    manifest, extra_header_lines = prepare_manifest(args.profile)
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_profile_header(args.output_header, manifest, extra_header_lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
