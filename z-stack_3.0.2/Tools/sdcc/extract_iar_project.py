#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable


def norm_windows_path(path: str) -> str:
    return path.replace("\\", "/")


def resolve_iar_path(raw: str, project_dir: Path) -> str:
    value = norm_windows_path(raw.strip())
    if value == "$PROJ_DIR$":
        return str(project_dir)
    if value.startswith("$PROJ_DIR$/"):
        resolved = project_dir / value[len("$PROJ_DIR$/") :]
        return str(resolved.resolve())
    return value


def resolve_many(values: Iterable[str], project_dir: Path) -> list[str]:
    return [resolve_iar_path(v, project_dir) for v in values if v and v.strip()]


def option_states(settings: ET.Element, option_name: str) -> list[str]:
    for option in settings.findall("./data/option"):
        if option.findtext("name") == option_name:
            return [state.text or "" for state in option.findall("state")]
    return []


def find_tool_settings(config: ET.Element, tool_name: str) -> ET.Element | None:
    for settings in config.findall("./settings"):
        if settings.findtext("name") == tool_name:
            return settings
    return None


def iter_group_files(group: ET.Element) -> Iterable[str]:
    for file_node in group.findall("./file"):
        name = file_node.findtext("name")
        if name:
            yield name
    for subgroup in group.findall("./group"):
        yield from iter_group_files(subgroup)


def parse_cfg_extra_opts(extra_opts: list[str], project_dir: Path) -> list[str]:
    cfgs: list[str] = []
    for opt in extra_opts:
        match = re.fullmatch(r"-f\s+(.+)", opt.strip())
        if match:
            cfgs.append(resolve_iar_path(match.group(1), project_dir))
    return cfgs


def parse_preinclude_extra_opts(extra_opts: list[str], project_dir: Path) -> list[str]:
    headers: list[str] = []
    for opt in extra_opts:
        match = re.fullmatch(r"--preinclude=(.+)", opt.strip())
        if match:
            headers.append(resolve_iar_path(match.group(1), project_dir))
    return headers


def parse_cfg_preincludes(cfg_files: list[str]) -> list[str]:
    headers: list[str] = []
    for cfg in cfg_files:
        cfg_path = Path(cfg)
        for raw_line in cfg_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.split("//", 1)[0].strip()
            if not line.startswith("--preinclude="):
                continue
            headers.append(str((cfg_path.parent / line.split("=", 1)[1].strip()).resolve()))
    return headers


def parse_linker_libs(extra_opts: list[str], project_dir: Path) -> list[str]:
    libs: list[str] = []
    for opt in extra_opts:
        match = re.fullmatch(r"-C\s+(.+)", opt.strip())
        if match:
            libs.append(resolve_iar_path(match.group(1), project_dir))
    return libs


def parse_cfg_defines(cfg_files: list[str]) -> list[str]:
    defines: list[str] = []
    for cfg in cfg_files:
        for raw_line in Path(cfg).read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.split("//", 1)[0].strip()
            if not line.startswith("-D"):
                continue
            define = line[2:].strip()
            if define:
                defines.append(define)
    return defines


def split_define(raw: str) -> tuple[str, str | None]:
    if "=" not in raw:
        return raw, None
    name, value = raw.split("=", 1)
    return name.strip(), value.strip()


def normalize_sdcc_define(name: str, value: str | None) -> tuple[bool, str | None]:
    if value is None:
        return False, None

    if name == "GENERIC" and value == "__generic":
        return True, ""

    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return True, value[1:-1]

    if any(ch.isspace() for ch in value) or "{" in value or "}" in value:
        return True, value

    return False, value


def classify_sdcc_defines(defines: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    cli_defines: list[str] = []
    header_defines: list[dict[str, str]] = []

    for raw in defines:
        name, value = split_define(raw)
        use_header, normalized = normalize_sdcc_define(name, value)
        if use_header:
            entry = {"name": name}
            if normalized is not None:
                entry["value"] = normalized
            header_defines.append(entry)
        else:
            cli_defines.append(raw)

    return cli_defines, header_defines


def write_sdcc_header(path: Path, header_defines: list[dict[str, str]]) -> None:
    lines = [
        "/* Auto-generated from IAR project settings for SDCC. */",
        "#ifndef ZSTACK_SDCC_CFG_H",
        "#define ZSTACK_SDCC_CFG_H",
        "",
    ]

    for define in header_defines:
        value = define.get("value")
        if value is None or value == "":
            lines.append(f"#define {define['name']}")
        else:
            lines.append(f"#define {define['name']} {value}")

    lines.extend(["", "#endif /* ZSTACK_SDCC_CFG_H */", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def find_zstack_root(project_file: Path) -> Path:
    for candidate in [project_file.resolve(), *project_file.resolve().parents]:
        if (candidate / "Projects").is_dir() and (candidate / "Components").is_dir():
            return candidate
    raise SystemExit(f"Unable to locate Z-Stack root for {project_file}")


def collect_manifest(project_file: Path, config_name: str) -> dict:
    root = ET.parse(project_file).getroot()
    config = next(
        (cfg for cfg in root.findall("./configuration") if cfg.findtext("name") == config_name),
        None,
    )
    if config is None:
        raise SystemExit(f"Configuration not found: {config_name}")

    project_dir = project_file.parent.resolve()
    repo_root = find_zstack_root(project_file)

    icc = find_tool_settings(config, "ICC8051")
    xlink = find_tool_settings(config, "XLINK")
    general = find_tool_settings(config, "General")
    if icc is None or xlink is None or general is None:
        raise SystemExit("Expected General/ICC8051/XLINK settings in project file")

    raw_files = list(iter_group_files(root))
    source_files = [f for f in raw_files if f.lower().endswith((".c", ".s51"))]
    header_files = [f for f in raw_files if f.lower().endswith(".h")]

    compiler_extra = option_states(icc, "Compiler Extra Options Edit")
    include_dirs = option_states(icc, "CCIncludePath2")
    defines = option_states(icc, "CCDefines")
    linker_extra = option_states(xlink, "Linker Extra Options Edit")
    xcl_file = option_states(xlink, "XclFile")
    cfg_files = parse_cfg_extra_opts(compiler_extra, project_dir)
    preinclude_files = list(
        dict.fromkeys(
            parse_preinclude_extra_opts(compiler_extra, project_dir)
            + parse_cfg_preincludes(cfg_files)
        )
    )
    cfg_defines = parse_cfg_defines(cfg_files)
    all_defines = defines + cfg_defines
    sdcc_cli_defines, sdcc_header_defines = classify_sdcc_defines(all_defines)

    manifest = {
        "project_file": str(project_file.resolve()),
        "project_dir": str(project_dir),
        "repo_root": str(repo_root.resolve()),
        "configuration": config_name,
        "chip": option_states(general, "OGChipSelectMenu"),
        "calling_convention_state": option_states(general, "Calling convention"),
        "code_model_state": option_states(general, "Code Memory Model"),
        "data_model_state": option_states(general, "Data Memory Model"),
        "defines": defines,
        "cfg_defines": cfg_defines,
        "all_defines": all_defines,
        "sdcc_cli_defines": sdcc_cli_defines,
        "sdcc_header_defines": sdcc_header_defines,
        "include_dirs": resolve_many(include_dirs, project_dir),
        "source_files": resolve_many(source_files, project_dir),
        "header_files": resolve_many(header_files, project_dir),
        "compiler_extra_options": compiler_extra,
        "cfg_files": cfg_files,
        "preinclude_files": preinclude_files,
        "xcl_file": resolve_many(xcl_file, project_dir),
        "linker_extra_options": linker_extra,
        "iar_libraries": parse_linker_libs(linker_extra, project_dir),
        "all_project_files": resolve_many(raw_files, project_dir),
    }
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract build metadata from an IAR .ewp project.")
    parser.add_argument("project", type=Path, help="Path to .ewp project file")
    parser.add_argument("--config", required=True, help="IAR configuration name, e.g. CoordinatorEB")
    parser.add_argument("--output", type=Path, help="Output JSON path")
    parser.add_argument("--sdcc-header-output", type=Path, help="Optional output path for SDCC preinclude header")
    args = parser.parse_args()

    manifest = collect_manifest(args.project, args.config)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    else:
        json.dump(manifest, sys.stdout, indent=2)
        sys.stdout.write("\n")

    if args.sdcc_header_output:
        write_sdcc_header(args.sdcc_header_output, manifest["sdcc_header_defines"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
