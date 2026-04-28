#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from gen_aslink_area_bases import _discover_xcl, _parse_xcl


def _load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _code_windows(manifest_path: Path) -> tuple[int, list[tuple[int, int]]]:
    manifest = _load_manifest(manifest_path)
    xcl_path = _discover_xcl(manifest, manifest_path)
    if xcl_path is None:
        return 0x7FFF, []

    variables = {
        "_CODE_START": 0x0000,
        "_CODE_END": 0x7FFF,
        "_XDATA_START": 0x0001,
        "_XDATA_END": 0x1EFF,
    }
    placements = _parse_xcl(xcl_path, variables)
    root_end = variables.get("_CODE_END", 0x7FFF)

    windows: set[tuple[int, int]] = set()
    for placement in placements.values():
        if str(placement.get("memory")) != "CODE":
            continue
        for start, end in placement.get("ranges", []):
            if int(start) > root_end:
                windows.add((int(start), int(end)))

    return root_end, sorted(windows)


def _uses_contiguous_banked_layout(
    memory: dict[int, int],
    root_end: int,
    windows: list[tuple[int, int]],
) -> bool:
    if not windows:
        return False
    for address in memory:
        if address <= root_end:
            continue
        if any(start <= address <= end for start, end in windows):
            continue
        return True
    return False


def _remap_address(
    address: int,
    root_end: int,
    windows: list[tuple[int, int]],
    *,
    contiguous_banked: bool,
) -> int:
    if address <= root_end:
        return address

    if contiguous_banked and windows:
        banked_start = windows[0][0]
        if address >= banked_start:
            return (root_end + 1) + (address - banked_start)

    physical_base = root_end + 1
    for start, end in windows:
        size = end - start + 1
        if start <= address <= end:
            return physical_base + (address - start)
        physical_base += size
    return address


def _parse_ihex(path: Path) -> dict[int, int]:
    memory: dict[int, int] = {}
    upper = 0
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith(":"):
            raise ValueError(f"Unsupported HEX line: {raw_line}")
        count = int(line[1:3], 16)
        address = int(line[3:7], 16)
        record_type = int(line[7:9], 16)
        data = bytes.fromhex(line[9 : 9 + count * 2])
        if record_type == 0x00:
            absolute = upper + address
            for offset, byte in enumerate(data):
                memory[absolute + offset] = byte
        elif record_type == 0x04:
            upper = int.from_bytes(data, "big") << 16
        elif record_type == 0x01:
            break
    return memory


def _checksum(payload: Iterable[int]) -> int:
    total = sum(payload) & 0xFF
    return (-total) & 0xFF


def _record(record_type: int, address: int, data: bytes) -> str:
    payload = bytes([len(data), (address >> 8) & 0xFF, address & 0xFF, record_type]) + data
    return ":" + payload.hex().upper() + f"{_checksum(payload):02X}"


def _emit_ihex(path: Path, memory: dict[int, int]) -> None:
    lines: list[str] = []
    current_upper: int | None = None
    addresses = sorted(memory)
    index = 0
    while index < len(addresses):
        start = addresses[index]
        chunk = bytearray([memory[start]])
        end = start
        index += 1
        while index < len(addresses):
            candidate = addresses[index]
            same_upper = (candidate >> 16) == (start >> 16)
            if not same_upper or candidate != end + 1 or len(chunk) >= 16:
                break
            chunk.append(memory[candidate])
            end = candidate
            index += 1

        upper = start >> 16
        if current_upper != upper:
            current_upper = upper
            lines.append(_record(0x04, 0, upper.to_bytes(2, "big")))
        lines.append(_record(0x00, start & 0xFFFF, bytes(chunk)))

    lines.append(":00000001FF")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def remap_hex(manifest_path: Path, input_hex: Path, output_hex: Path) -> dict[str, object]:
    root_end, windows = _code_windows(manifest_path)
    logical_memory = _parse_ihex(input_hex)
    contiguous_banked = _uses_contiguous_banked_layout(logical_memory, root_end, windows)
    physical_memory = {
        _remap_address(
            address,
            root_end,
            windows,
            contiguous_banked=contiguous_banked,
        ): byte
        for address, byte in logical_memory.items()
    }
    _emit_ihex(output_hex, physical_memory)
    return {
        "root_end": root_end,
        "windows": windows,
        "contiguous_banked": contiguous_banked,
        "input_max_address": max(logical_memory, default=0),
        "output_max_address": max(physical_memory, default=0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Remap SDCC banked logical Intel HEX addresses into physical flash addresses.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--input-hex", required=True, type=Path)
    parser.add_argument("--output-hex", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = remap_hex(args.manifest, args.input_hex, args.output_hex)
    if args.json:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
