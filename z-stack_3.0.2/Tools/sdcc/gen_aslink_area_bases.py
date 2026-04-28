#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PLACEMENT_RE = re.compile(
    r"^-(?P<mode>[PZ])\((?P<memory>[^)]+)\)(?P<areas>[^=]+)=(?P<ranges>.+)$"
)
DEFINE_RE = re.compile(r"^-D(?P<name>[A-Za-z0-9_]+)=(?P<expr>.+)$")


def _parse_int(value: str) -> int:
    return int(value, 0)


def _normalize_xcl_lines(text: str) -> list[str]:
    lines: list[str] = []
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        if line.endswith("\\"):
            current += line[:-1].strip()
            continue
        current += line
        lines.append(current)
        current = ""
    if current:
        lines.append(current)
    return lines


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _split_top_level_range(expr: str) -> tuple[str, str] | None:
    depth = 0
    for index, char in enumerate(expr):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "-" and depth == 0:
            return expr[:index].strip(), expr[index + 1 :].strip()
    return None


def _resolve_token(token: str, variables: dict[str, int]) -> int | None:
    token = token.strip()
    while token.startswith("(") and token.endswith(")"):
        token = token[1:-1].strip()
    if token in variables:
        return variables[token]
    if token.startswith(("0x", "0X")):
        try:
            return int(token, 16)
        except ValueError:
            pass
    if token.isdigit():
        return int(token, 10)
    for operator in ("+", "-"):
        if operator not in token:
            continue
        left, right = token.rsplit(operator, 1)
        left_value = _resolve_token(left, variables)
        right_value = _resolve_token(right, variables)
        if left_value is None or right_value is None:
            continue
        if operator == "+":
            return left_value + right_value
        return left_value - right_value
    return None


def _parse_range(expr: str, variables: dict[str, int]) -> tuple[int, int] | None:
    expr = expr.strip()
    range_tokens = _split_top_level_range(expr)
    if range_tokens is not None:
        start_token, end_token = range_tokens
        start = _resolve_token(start_token, variables)
        end = _resolve_token(end_token, variables)
        if start is None or end is None:
            return None
        return start, end
    value = _resolve_token(expr, variables)
    if value is None:
        return None
    return value, value


def _parse_xcl(path: Path, variables: dict[str, int]) -> dict[str, dict[str, object]]:
    placements: dict[str, dict[str, object]] = {}
    for line in _normalize_xcl_lines(path.read_text(encoding="utf-8", errors="ignore")):
        define_match = DEFINE_RE.match(line)
        if define_match:
            value = _resolve_token(define_match.group("expr"), variables)
            if value is not None:
                variables[define_match.group("name")] = value
            continue
        match = PLACEMENT_RE.match(line)
        if not match:
            continue
        mode = match.group("mode")
        memory = match.group("memory").strip()
        areas = _split_csv(match.group("areas"))
        ranges = []
        for expr in _split_csv(match.group("ranges")):
            parsed = _parse_range(expr, variables)
            if parsed is None:
                continue
            ranges.append(parsed)
        for area in areas:
            placements[area] = {
                "mode": mode,
                "memory": memory,
                "ranges": ranges,
            }
    return placements


def _discover_xcl(manifest: dict[str, object], manifest_path: Path) -> Path | None:
    for key in ("xcl_path", "xcl_file", "linker_script", "iar_xcl"):
        value = manifest.get(key)
        if isinstance(value, str) and value.endswith(".xcl"):
            candidate = Path(value)
            if candidate.exists():
                return candidate
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, str) or not item.endswith(".xcl"):
                    continue
                candidate = Path(item)
                if candidate.exists():
                    return candidate
    for value in manifest.get("source_files", []):
        if not isinstance(value, str) or not value.endswith(".xcl"):
            continue
        candidate = Path(value)
        if candidate.exists():
            return candidate
    project_dir = manifest_path.parent
    for candidate in project_dir.rglob("*.xcl"):
        return candidate
    return None


def _collect_section_maps(
    converted_manifest_path: Path,
) -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    payload = json.loads(converted_manifest_path.read_text(encoding="utf-8"))
    metadata_files: list[Path] = []
    for artifact in payload.get("emitted_artifacts", []):
        if not isinstance(artifact, str) or not artifact.endswith(".rel"):
            continue
        candidate = Path(artifact).with_suffix(".convert.json")
        if candidate.exists():
            metadata_files.append(candidate)
    present_areas: dict[str, dict[str, object]] = {}
    metadata_payloads: list[dict[str, object]] = []
    for metadata_file in metadata_files:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        metadata_payloads.append(metadata)
        section_map = metadata.get("area_plan", {}).get("section_area_map", {})
        for source_section, descriptor in section_map.items():
            present_areas[str(source_section)] = dict(descriptor)
    return present_areas, metadata_payloads


def _required_areas(manifest: dict[str, object]) -> list[str]:
    return [
        area
        for area in manifest.get("sdcc_required_areas", [])
        if isinstance(area, str) and area
    ]


def _select_base(
    area: str,
    placement: dict[str, object],
    variables: dict[str, int],
    descriptor: dict[str, object] | None,
) -> int | None:
    ranges = placement.get("ranges", [])
    if not ranges:
        return None
    first_start = int(ranges[0][0])
    descriptor = descriptor or {}
    role = str(descriptor.get("role", ""))
    memory = str(descriptor.get("memory", ""))
    if area == "XDATA_ROM_C" or role == "xdata_rom_alias":
        return 0x8000
    if role.startswith("xdata_") or memory == "XDATA":
        return variables["_XDATA_START"]
    if area == "BANKED_CODE":
        root_start = variables["_CODE_START"]
        for start, _ in ranges:
            if start != root_start:
                return int(start)
        return first_start
    return first_start


def build_plan(
    manifest_path: Path,
    converted_manifest_path: Path,
    *,
    code_loc: int,
    code_size: int,
    xram_loc: int,
    xram_size: int,
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    xcl_path = _discover_xcl(manifest, manifest_path)
    variables = {
        "_CODE_START": code_loc,
        "_CODE_END": code_loc + code_size - 1,
        "_XDATA_START": xram_loc,
        "_XDATA_END": xram_loc + xram_size - 1,
    }
    if xcl_path is None:
        return {
            "xcl_path": None,
            "base_directives": [],
            "warnings": ["No .xcl file found in manifest."],
        }

    xcl_placements = _parse_xcl(xcl_path, variables)
    present_areas, metadata_payloads = _collect_section_maps(converted_manifest_path)
    required_areas = _required_areas(manifest)
    base_directives: list[dict[str, object]] = []
    seen: set[str] = set()
    for area, descriptor in sorted(present_areas.items()):
        placement = xcl_placements.get(area)
        if placement is None:
            continue
        base = _select_base(area, placement, variables, descriptor)
        if base is None or area in seen:
            continue
        seen.add(area)
        base_directives.append(
            {
                "area": area,
                "base": base,
                "memory": placement["memory"],
                "mode": placement["mode"],
                "ranges": placement["ranges"],
            }
        )

    for area in required_areas:
        if area in seen:
            continue
        placement = xcl_placements.get(area)
        if placement is None:
            continue
        base = _select_base(area, placement, variables, None)
        if base is None:
            continue
        seen.add(area)
        base_directives.append(
            {
                "area": area,
                "base": base,
                "memory": placement["memory"],
                "mode": placement["mode"],
                "ranges": placement["ranges"],
            }
        )

    warnings: list[str] = []
    if not base_directives:
        warnings.append("No matching named areas found between xcl placements and converted metadata.")
    if any(metadata.get("area_plan", {}).get("banked_code_areas") for metadata in metadata_payloads):
        warnings.append(
            "BANKED_CODE base can be emitted, but it will only take effect once native SDCC code stops filling bank windows via CSEG."
        )

    return {
        "xcl_path": str(xcl_path),
        "base_directives": base_directives,
        "warnings": warnings,
    }


def _emit_lk(plan: dict[str, object], stream: object) -> None:
    for warning in plan.get("warnings", []):
        print(f"; {warning}", file=stream)
    for directive in plan.get("base_directives", []):
        print(
            f"-b {directive['area']} = 0x{int(directive['base']):X}",
            file=stream,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate aslink base directives from an IAR xcl + converter metadata.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--converted-manifest", type=Path, required=True)
    parser.add_argument("--code-loc", required=True)
    parser.add_argument("--code-size", required=True)
    parser.add_argument("--xram-loc", required=True)
    parser.add_argument("--xram-size", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    plan = build_plan(
        args.manifest,
        args.converted_manifest,
        code_loc=_parse_int(args.code_loc),
        code_size=_parse_int(args.code_size),
        xram_loc=_parse_int(args.xram_loc),
        xram_size=_parse_int(args.xram_size),
    )
    if args.json:
        json.dump(plan, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    _emit_lk(plan, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
