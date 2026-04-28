#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ZSTACK_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
WORKSPACE_DIR=$(cd "$ZSTACK_DIR/.." && pwd)
SDCC_BUILD_DIR=${SDCC_BUILD_DIR:-"$WORKSPACE_DIR/sdcc-build"}
PYTHON_BIN=${PYTHON_BIN:-python3}
BUILD_SAMPLELIGHT_MODE=${BUILD_SAMPLELIGHT_MODE:-full}
ENTRY_JSON_FILE=${ENTRY_JSON_FILE:-}

PROJECT_NAME="CC2530ZNP-with-SBL"
ZNP_SDCC_PROFILE=${ZNP_SDCC_PROFILE:-full}
PROFILE_SUFFIX=""
if [ "$ZNP_SDCC_PROFILE" != "full" ]; then
  PROFILE_SUFFIX="-$ZNP_SDCC_PROFILE"
fi

OUT_DIR=${1:-"$SDCC_BUILD_DIR/zstack-znp-cc2530-with-sbl$PROFILE_SUFFIX"}
GENERATED_MANIFEST=${MANIFEST:-"$OUT_DIR/znp-cc2530-with-sbl.manifest.json"}
GENERATED_CFG_HEADER=${CFG_HEADER:-"$OUT_DIR/znp-cc2530-with-sbl-sdcc-cfg.h"}
MEM_FILE="$OUT_DIR/$PROJECT_NAME.mem"
IHX_FILE="$OUT_DIR/$PROJECT_NAME.ihx"
HEX_FILE="$OUT_DIR/$PROJECT_NAME.hex"
FLASH_LIMIT_HEX=0x3c800
CODE_FLOOR_HEX=0x2000

mkdir -p "$OUT_DIR"

if [ ! -f "$GENERATED_MANIFEST" ] || [ ! -f "$GENERATED_CFG_HEADER" ]; then
  "$PYTHON_BIN" "$SCRIPT_DIR/prepare_znp_cc2530_with_sbl.py" \
    --profile "$ZNP_SDCC_PROFILE" \
    --output-manifest "$GENERATED_MANIFEST" \
    --output-header "$GENERATED_CFG_HEADER"
fi

env \
  PROJECT_NAME="$PROJECT_NAME" \
  MANIFEST="$GENERATED_MANIFEST" \
  CFG_HEADER="$GENERATED_CFG_HEADER" \
  BUILD_SAMPLELIGHT_MODE="$BUILD_SAMPLELIGHT_MODE" \
  ENTRY_JSON_FILE="$ENTRY_JSON_FILE" \
  SDCC_STACK_MODE=stack-auto-xstack \
  SDCC_CODE_LOC=0x2000 \
  SDCC_CODE_SIZE=0x3c800 \
  SDCC_XRAM_LOC=0x0001 \
  SDCC_XRAM_SIZE=0x1AFF \
  SDCC_XSTACK_LOC=0x1B00 \
  CONVERTED_DIR="$SDCC_BUILD_DIR/iar-converted/znp-cc2530-with-sbl$PROFILE_SUFFIX" \
  RELAX_MEMORY=0 \
  bash "$SCRIPT_DIR/build_samplelight.sh" "$OUT_DIR"

case "$BUILD_SAMPLELIGHT_MODE" in
  prepare-native|compile-entry)
    exit 0
    ;;
  link-only|full)
    ;;
  *)
    echo "Unsupported BUILD_SAMPLELIGHT_MODE: $BUILD_SAMPLELIGHT_MODE" >&2
    exit 1
    ;;
esac

"$PYTHON_BIN" - "$MEM_FILE" "$IHX_FILE" "$FLASH_LIMIT_HEX" "$CODE_FLOOR_HEX" <<'PY'
import re
import sys
from pathlib import Path

mem_path = Path(sys.argv[1])
ihx_path = Path(sys.argv[2])
flash_limit = int(sys.argv[3], 16)
code_floor = int(sys.argv[4], 16)
match = re.search(
    r"ROM/EPROM/FLASH\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)\s+(\d+)\s+(\d+)",
    mem_path.read_text(encoding="utf-8"),
)
if not match:
    raise SystemExit(f"Unable to parse flash usage from {mem_path}")
flash_end = int(match.group(2), 16)
if flash_end >= flash_limit:
    raise SystemExit(
        f"Flash end 0x{flash_end:05x} exceeds reserved ceiling 0x{flash_limit:05x}"
    )

linear_base = 0
segment_base = 0
for raw_line in ihx_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or not line.startswith(":"):
        continue
    count = int(line[1:3], 16)
    address = int(line[3:7], 16)
    rectype = int(line[7:9], 16)
    data = line[9 : 9 + count * 2]
    if rectype == 0x00 and count:
        absolute = linear_base + segment_base + address
        if absolute < code_floor:
            raise SystemExit(
                f"IHX contains data record below SBL floor: 0x{absolute:04x} < 0x{code_floor:04x}"
            )
    elif rectype == 0x02:
        segment_base = int(data, 16) << 4
        linear_base = 0
    elif rectype == 0x04:
        linear_base = int(data, 16) << 16
        segment_base = 0

print(f"Validated flash end 0x{flash_end:05x} < 0x{flash_limit:05x}")
print(f"Validated IHX data starts at or above 0x{code_floor:04x}")
PY

echo "Manifest: $GENERATED_MANIFEST"
echo "IHX: $IHX_FILE"
echo "HEX: $HEX_FILE"
