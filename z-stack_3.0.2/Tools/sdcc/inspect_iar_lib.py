#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


def extract_strings(data: bytes, min_len: int = 4) -> list[str]:
    out: list[str] = []
    buf = bytearray()
    for b in data:
        if 32 <= b <= 126:
            buf.append(b)
            continue
        if len(buf) >= min_len:
            out.append(buf.decode("ascii", errors="ignore"))
        buf.clear()
    if len(buf) >= min_len:
        out.append(buf.decode("ascii", errors="ignore"))
    return out


def next_value(strings: list[str], key: str) -> str | None:
    for idx, value in enumerate(strings):
        if value != key:
            continue
        if idx + 1 < len(strings):
            return strings[idx + 1]
    return None


def summarize(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    strings = extract_strings(data)
    return {
        "path": str(path),
        "size": len(data),
        "module_name": strings[0] if strings else None,
        "calling_convention": next_value(strings, "__calling_convention"),
        "code_model": next_value(strings, "__code_model"),
        "data_model": next_value(strings, "__data_model"),
        "uses_banked_runtime": any(
            token in strings
            for token in ("?BDISPATCH", "?BRET", "?BANKED_ENTER_XDATA", "?BANKED_LEAVE_XDATA")
        ),
        "sample_symbols": [s for s in strings if s and s[0].isalpha()][:12],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect basic metadata from an IAR 8051 .lib binary.")
    parser.add_argument("library", type=Path, nargs="+", help="Path(s) to IAR .lib files")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    summaries = [summarize(path.resolve()) for path in args.library]

    if args.json:
        print(json.dumps(summaries, indent=2))
        return 0

    for summary in summaries:
        print(f"Library: {summary['path']}")
        print(f"  module: {summary['module_name'] or 'unknown'}")
        print(f"  calling convention: {summary['calling_convention'] or 'unknown'}")
        print(f"  code model: {summary['code_model'] or 'unknown'}")
        print(f"  data model: {summary['data_model'] or 'unknown'}")
        print(f"  banked runtime markers: {'yes' if summary['uses_banked_runtime'] else 'no'}")
        sample_symbols = summary["sample_symbols"]
        if sample_symbols:
            print(f"  sample symbols: {', '.join(sample_symbols[:8])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
