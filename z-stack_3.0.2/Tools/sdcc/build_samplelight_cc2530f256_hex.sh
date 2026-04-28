#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ZSTACK_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
WORKSPACE_DIR=$(cd "$ZSTACK_DIR/.." && pwd)
SDCC_BUILD_DIR="$WORKSPACE_DIR/sdcc-build"

BASE_MANIFEST="$SCRIPT_DIR/manifests/samplelight-cc2530db-coordinator.json"
CFG_HEADER="$SCRIPT_DIR/manifests/samplelight-cc2530db-coordinator-sdcc-cfg.h"
OUT_DIR=${1:-"$SDCC_BUILD_DIR/zstack-samplelight-cc2530db-coordinator-stackauto-f256-hex"}
GENERATED_MANIFEST="$OUT_DIR/samplelight-cc2530db-coordinator-f256-manifest.json"
MEM_FILE="$OUT_DIR/samplelight-cc2530db-coordinator.mem"
FLASH_LIMIT_HEX=0x3c800

mkdir -p "$OUT_DIR"

python3 - "$BASE_MANIFEST" "$GENERATED_MANIFEST" "$ZSTACK_DIR" "$SCRIPT_DIR" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
out = Path(sys.argv[2])
zstack_dir = Path(sys.argv[3])
script_dir = Path(sys.argv[4])
sys.path.insert(0, str(script_dir))

from manifest_paths import rebase_manifest_paths

data = rebase_manifest_paths(
    json.loads(src.read_text(encoding="utf-8")),
    zstack_dir,
)

remove_defs = {
    "BDB_REPORTING",
    "LCD_SUPPORTED=DEBUG",
    "ZCL_SCENES",
    "ZCL_GROUPS",
    "xZTOOL_P1",
}
data["sdcc_cli_defines"] = [
    d for d in data["sdcc_cli_defines"]
    if d not in remove_defs and not d.startswith("xMT_")
]
if "DISABLE_GREENPOWER_BASIC_PROXY" not in data["sdcc_cli_defines"]:
    data["sdcc_cli_defines"].append("DISABLE_GREENPOWER_BASIC_PROXY")
if "BDB_FINDING_BINDING_CAPABILITY_ENABLED=0" not in data["sdcc_cli_defines"]:
    data["sdcc_cli_defines"].append("BDB_FINDING_BINDING_CAPABILITY_ENABLED=0")
if "HAL_UART=FALSE" not in data["sdcc_cli_defines"]:
    data["sdcc_cli_defines"].append("HAL_UART=FALSE")
if "HAL_KEY=FALSE" not in data["sdcc_cli_defines"]:
    data["sdcc_cli_defines"].append("HAL_KEY=FALSE")

ui_src = str(zstack_dir / "Projects/zstack/HomeAutomation/Source/zcl_sampleapps_ui.c")
ui_shim = str(script_dir / "shims/zcl_sampleapps_ui_minimal.c")
lcd_src = str(zstack_dir / "Components/hal/target/CC2530EB/hal_lcd.c")
lcd_shim = str(script_dir / "shims/hal_lcd_home.c")
led_src = str(zstack_dir / "Components/hal/target/CC2530EB/hal_led.c")
led_shim = str(script_dir / "shims/hal_led_home.c")
remove_sources = {
    str(zstack_dir / "Components/stack/nwk/stub_aps.c"),
    str(zstack_dir / "Components/stack/bdb/bdb_FindingAndBinding.c"),
    str(zstack_dir / "Components/stack/bdb/bdb_touchlink.c"),
    str(zstack_dir / "Components/stack/bdb/bdb_touchlink_initiator.c"),
    str(zstack_dir / "Components/stack/bdb/bdb_touchlink_target.c"),
}

new_sources = []
for src_path in data["source_files"]:
    if src_path == ui_src:
        src_path = ui_shim
    elif src_path == lcd_src:
        src_path = lcd_shim
    elif src_path == led_src:
        src_path = led_shim
    if "/Components/mt/" in src_path:
        continue
    if src_path in remove_sources:
        continue
    new_sources.append(src_path)
data["source_files"] = new_sources

override_map = {entry["source"]: entry for entry in data.get("sdcc_compile_overrides", [])}
for shim_path in (lcd_shim, led_shim):
    override_map[shim_path] = {"source": shim_path, "codeseg": "HOME"}
data["sdcc_compile_overrides"] = list(override_map.values())

out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

env \
  MANIFEST="$GENERATED_MANIFEST" \
  CFG_HEADER="$CFG_HEADER" \
  SDCC_MODEL=huge \
  SDCC_STACK_MODE=stack-auto \
  RELAX_MEMORY=0 \
  bash "$SCRIPT_DIR/build_samplelight.sh" "$OUT_DIR"

python3 - "$OUT_DIR/samplelight-cc2530db-coordinator.hex" "$FLASH_LIMIT_HEX" <<'PY'
import sys
from pathlib import Path

hex_path = Path(sys.argv[1])
flash_limit = int(sys.argv[2], 16)
base = 0
flash_end = 0

for line in hex_path.read_text(encoding="utf-8").splitlines():
    if not line.startswith(":"):
        continue
    count = int(line[1:3], 16)
    address = int(line[3:7], 16)
    record_type = int(line[7:9], 16)
    if record_type == 0x00 and count:
        flash_end = max(flash_end, base + address + count - 1)
    elif record_type == 0x04:
        base = int(line[9:13], 16) << 16

if flash_end >= flash_limit:
    raise SystemExit(
        f"Flash end 0x{flash_end:05x} exceeds reserved ceiling 0x{flash_limit:05x}"
    )
print(f"Validated flash end 0x{flash_end:05x} < 0x{flash_limit:05x}")
PY

echo "Manifest: $GENERATED_MANIFEST"
echo "IHX: $OUT_DIR/samplelight-cc2530db-coordinator.ihx"
echo "HEX: $OUT_DIR/samplelight-cc2530db-coordinator.hex"
