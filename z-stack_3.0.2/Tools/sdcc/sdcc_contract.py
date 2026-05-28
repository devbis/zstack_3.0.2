from __future__ import annotations

from pathlib import Path
from typing import Iterable


_ASM_DIR = Path(__file__).resolve().parent / "asm"


def sdcc_sleep_entry_sources() -> list[str]:
    """Return the SDCC-only source(s) that provide halSetSleepMode()."""
    return []


def sdcc_flash_reservation_sources(profile: str) -> list[str]:
    """Return SDCC-only assembler sources that reserve required flash windows."""
    sources: list[str] = []
    if profile.lower() == "full":
        sources.append(str((_ASM_DIR / "cc2530_full_nv_reservation.asm").resolve()))
    return sources


def sdcc_required_areas(profile: str) -> list[str]:
    """Return the SDCC flash areas that must exist for the active profile."""
    areas = [
        "SLEEP_CODE",
        "CRC_SHDW",
        "LOCK_BITS_ADDRESS_SPACE",
        "IEEE_ADDRESS_SPACE",
        "RESERVED_ADDRESS_SPACE",
    ]
    if profile.lower() == "full":
        areas.append("ZIGNV_ADDRESS_SPACE")
    return areas


def merge_sdcc_extra_sources(existing: Iterable[object], additions: Iterable[str]) -> list[object]:
    """Append SDCC extra sources while preserving order and avoiding duplicates.

    Existing manifests can carry plain strings today and may carry dict-style
    source descriptors in the future. Treat those shapes as already present if
    they point at the same source path.
    """

    merged: list[object] = list(existing)

    def _matches(item: object, candidate: str) -> bool:
        if isinstance(item, str):
            return item == candidate
        if isinstance(item, dict):
            for key in ("source", "compile_source"):
                value = item.get(key)
                if isinstance(value, str) and value == candidate:
                    return True
        return False

    for candidate in additions:
        if any(_matches(item, candidate) for item in merged):
            continue
        merged.append(candidate)
    return merged
