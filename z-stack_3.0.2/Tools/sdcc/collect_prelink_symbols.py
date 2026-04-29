from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from iar2sdcc.archive import normalize_symbol
from iar2sdcc.heuristics import is_noise_symbol


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect unresolved symbols from compiled SDCC objects before the first link pass."
    )
    parser.add_argument("--sdnm", type=Path, required=True, help="Path to the sdnm binary")
    parser.add_argument("--consumer", type=Path, action="append", default=[], help="Object or rel file that may reference undefined symbols")
    parser.add_argument("--provider", type=Path, action="append", default=[], help="Object, rel, or library file that may define symbols")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path")
    return parser


def _parse_sdnm_line(line: str) -> tuple[str, str, str] | None:
    if ":" not in line:
        return None
    origin, rest = line.rsplit(":", 1)
    fields = rest.strip().split()
    if len(fields) < 2:
        return None
    if len(fields) == 2:
        sym_type, symbol = fields
    else:
        sym_type, symbol = fields[-2], fields[-1]
    return origin, sym_type, symbol


def _collect_defined_symbols(sdnm: Path, providers: list[Path]) -> set[str]:
    defined: set[str] = set()
    if not providers:
        return defined
    cmd = [str(sdnm), "-U", "-A", *[str(path) for path in providers]]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    for raw_line in result.stdout.splitlines():
        parsed = _parse_sdnm_line(raw_line)
        if parsed is None:
            continue
        _, _, raw_symbol = parsed
        symbol = normalize_symbol(raw_symbol)
        if not symbol or is_noise_symbol(symbol) or symbol == ".__.ABS.":
            continue
        defined.add(symbol)
    return defined


def _collect_undefined_references(sdnm: Path, consumers: list[Path]) -> dict[str, list[str]]:
    references: dict[str, list[str]] = {}
    if not consumers:
        return references
    cmd = [str(sdnm), "-u", "-A", *[str(path) for path in consumers]]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    for raw_line in result.stdout.splitlines():
        parsed = _parse_sdnm_line(raw_line)
        if parsed is None:
            continue
        origin, sym_type, raw_symbol = parsed
        if sym_type != "U":
            continue
        symbol = normalize_symbol(raw_symbol)
        if not symbol or is_noise_symbol(symbol):
            continue
        modules = references.setdefault(symbol, [])
        if origin not in modules:
            modules.append(origin)
    return {
        symbol: sorted(modules)
        for symbol, modules in sorted(references.items())
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    defined = _collect_defined_symbols(args.sdnm, [path.resolve() for path in args.provider if path.exists()])
    references = _collect_undefined_references(args.sdnm, [path.resolve() for path in args.consumer if path.exists()])
    unresolved = sorted(symbol for symbol in references if symbol not in defined)
    payload = {
        "kind": "prelink",
        "sdnm": str(args.sdnm.resolve()),
        "consumers": [str(path.resolve()) for path in args.consumer if path.exists()],
        "providers": [str(path.resolve()) for path in args.provider if path.exists()],
        "defined_symbol_count": len(defined),
        "defined_symbols": sorted(defined),
        "undefined_symbol_count": len(references),
        "unresolved_symbol_count": len(unresolved),
        "undefined_symbols": unresolved,
        "references": {symbol: references[symbol] for symbol in unresolved},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
