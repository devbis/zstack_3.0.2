#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ZSTACK_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)
WORKSPACE_DIR=$(cd "$ZSTACK_DIR/.." && pwd)
SDCC_BUILD_DIR=${SDCC_BUILD_DIR:-"$WORKSPACE_DIR/sdcc-build"}
SDCC_TOOLCHAIN_DIR=${SDCC_TOOLCHAIN_DIR:-"$SDCC_BUILD_DIR"}
PROJECT_NAME=${PROJECT_NAME:-samplelight-cc2530db-coordinator}

MANIFEST=${MANIFEST:-"$SCRIPT_DIR/manifests/${PROJECT_NAME}.json"}
CFG_HEADER=${CFG_HEADER:-"$SCRIPT_DIR/manifests/${PROJECT_NAME}-sdcc-cfg.h"}
OUT_DIR=${1:-"$SDCC_BUILD_DIR/zstack-$PROJECT_NAME"}
SDCC_MODEL=${SDCC_MODEL:-large}
SDCC_ABI=${SDCC_ABI:-iar}
SDCC_STACK_MODE=${SDCC_STACK_MODE:-default}
SDCC_CODE_LOC=${SDCC_CODE_LOC:-0x0000}
SDCC_CODE_SIZE=${SDCC_CODE_SIZE:-}
SDCC_XRAM_LOC=${SDCC_XRAM_LOC:-0x0001}
SDCC_XRAM_SIZE=${SDCC_XRAM_SIZE:-0x1EFF}
SDCC_XSTACK_LOC=${SDCC_XSTACK_LOC:-}
SDCC_EXTRA_ARGS=${SDCC_EXTRA_ARGS:-}
REUSE_OBJECTS=${REUSE_OBJECTS:-0}
SDCC_DEFAULT_CODESEG=${SDCC_DEFAULT_CODESEG:-}
SDCC_PORT_INC_DIR=${SDCC_PORT_INC_DIR:-}
PYTHON_BIN=${PYTHON_BIN:-python3}
BUILD_SAMPLELIGHT_MODE=${BUILD_SAMPLELIGHT_MODE:-full}
ENTRY_JSON_FILE=${ENTRY_JSON_FILE:-}

SDCC_BIN="$SDCC_TOOLCHAIN_DIR/bin/sdcc"
PACKIHX_BIN="$SDCC_TOOLCHAIN_DIR/bin/packihx"
SDLD_BIN="$SDCC_TOOLCHAIN_DIR/bin/sdld"
SDAS8051_BIN="$SDCC_TOOLCHAIN_DIR/bin/sdas8051"
MODEL_FLAG="--model-$SDCC_MODEL"
IAR_LIB_INSPECTOR="$SCRIPT_DIR/inspect_iar_lib.py"
CONVERTER_CLI="$SCRIPT_DIR/iar2sdcc/cli.py"
CONVERTED_DIR="${CONVERTED_DIR:-$OUT_DIR/iar-converted}"
RELAX_MEMORY="${RELAX_MEMORY:-auto}"
CONVERTED_MANIFEST="$CONVERTED_DIR/manifest.json"
CONVERTED_MODULE_PLAN="$CONVERTED_DIR/module-plan.json"
ASLINK_AREA_BASES_SCRIPT="$SCRIPT_DIR/gen_aslink_area_bases.py"
COMPILE_PLAN_SCRIPT="$SCRIPT_DIR/gen_compile_plan.py"
PREPARE_SOURCE_SCRIPT="$SCRIPT_DIR/prepare_source.py"
REMAP_BANKED_HEX_SCRIPT="$SCRIPT_DIR/remap_banked_hex.py"
ASLINK_AREA_BASES_LK="$OUT_DIR/aslink-area-bases.lk"
LINK_LOG="$OUT_DIR/link.log"
LINK_REPORT_JSON="$OUT_DIR/unresolved-libraries.json"
FIRST_PASS_LINK_LOG="$OUT_DIR/first-pass.link.log"
FIRST_PASS_REPORT_JSON="$OUT_DIR/first-pass-unresolved-libraries.json"
SECOND_PASS_STRICT_LOG="$OUT_DIR/second-pass-strict.link.log"
SECOND_PASS_RELAXED_LOG="$OUT_DIR/second-pass-relaxed.link.log"
FINAL_LINK_REPORT_JSON="$OUT_DIR/final-link-unresolved-libraries.json"
NORMALIZED_MANIFEST="$OUT_DIR/manifest.normalized.json"
COMPILE_PLAN_JSON="$OUT_DIR/compile-plan.json"
RUNTIME_ROOT_DIR="$SCRIPT_DIR/runtime"
TOOLCHAIN_SHARE_DIR="$SDCC_TOOLCHAIN_DIR/share/sdcc"
DEVICE_LIB_DIR=""
BASE_RUNTIME_LIB_DIR=""
PORT_INC_DIR=""
RUNTIME_BUILD_CAPABLE=0

OBJ_DIR="$OUT_DIR/obj"
GENERATED_SRC_DIR="$OUT_DIR/generated-src"
ARTIFACT_BASE="$OUT_DIR/$PROJECT_NAME"
IHX_FILE="$ARTIFACT_BASE.ihx"
HEX_FILE="$ARTIFACT_BASE.hex"
LOGICAL_HEX_FILE="$ARTIFACT_BASE.logical.hex"
HEADER_OVERLAYS=(
  "cc2530-hal-mcu-h:Components/hal/target/CC2530ZNP/hal_mcu.h|Components/hal/target/CC2530EB/hal_mcu.h"
  "cc2530-hal-types-h:Components/hal/target/CC2530ZNP/hal_types.h|Components/hal/target/CC2530EB/hal_types.h"
  "cc2530-hal-board-cfg-h:Components/hal/target/CC2530ZNP/hal_board_cfg.h|Components/hal/target/CC2530EB/hal_board_cfg.h"
  "cc2530-zcl-sampleapps-ui-h:Projects/zstack/HomeAutomation/Source/zcl_sampleapps_ui.h"
  "cc2530-onboard-h:Projects/zstack/ZMain/TI2530ZNP/OnBoard.h|Projects/zstack/ZMain/TI2530DB/OnBoard.h"
)
HEADER_ALIASES=(
  "Components/stack/af/af.h|Components/stack/af/AF.h"
  "Components/osal/include/OSAL_NV.h|Components/osal/include/OSAL_Nv.h"
  "Components/osal/include/osal_nv.h|Components/osal/include/OSAL_Nv.h"
  "Components/osal/include/osal.h|Components/osal/include/OSAL.h"
  "Projects/zstack/ZMain/TI2530ZNP/Onboard.h|Projects/zstack/ZMain/TI2530ZNP/OnBoard.h"
  "Projects/zstack/ZMain/TI2530DB/Onboard.h|Projects/zstack/ZMain/TI2530DB/OnBoard.h"
  "Components/zmac/ZMac.h|Components/zmac/ZMAC.h"
  "Components/mt/mt_uart.h|Components/mt/MT_UART.h"
  "Components/stack/gp/gp_common.h|Components/stack/GP/gp_common.h"
  "Components/stack/gp/gp_interface.h|Components/stack/GP/gp_interface.h"
  "Components/stack/gp/cGP_stub.h|Components/stack/GP/cGP_stub.h"
  "Components/stack/gp/dgp_stub.h|Components/stack/GP/dGP_stub.h"
)

if [ -d "$SDCC_TOOLCHAIN_DIR/device/lib" ]; then
  DEVICE_LIB_DIR="$SDCC_TOOLCHAIN_DIR/device/lib"
  BASE_RUNTIME_LIB_DIR="$DEVICE_LIB_DIR/build/$SDCC_MODEL"
  if [ -f "$DEVICE_LIB_DIR/Makefile" ] && [ -f "$SDCC_TOOLCHAIN_DIR/config.status" ]; then
    RUNTIME_BUILD_CAPABLE=1
  fi
elif [ -d "$TOOLCHAIN_SHARE_DIR/lib" ]; then
  DEVICE_LIB_DIR="$TOOLCHAIN_SHARE_DIR/lib"
  BASE_RUNTIME_LIB_DIR="$DEVICE_LIB_DIR/$SDCC_MODEL"
else
  echo "Unable to locate SDCC runtime libraries under $SDCC_TOOLCHAIN_DIR" >&2
  exit 1
fi

if [ -n "$SDCC_PORT_INC_DIR" ]; then
  PORT_INC_DIR="$SDCC_PORT_INC_DIR"
elif [ -d "$SDCC_TOOLCHAIN_DIR/device/include/mcs51" ]; then
  PORT_INC_DIR="$SDCC_TOOLCHAIN_DIR/device/include/mcs51"
elif [ -d "$TOOLCHAIN_SHARE_DIR/include/mcs51" ]; then
  PORT_INC_DIR="$TOOLCHAIN_SHARE_DIR/include/mcs51"
elif [ -d "$WORKSPACE_DIR/sdcc/device/include/mcs51" ]; then
  PORT_INC_DIR="$WORKSPACE_DIR/sdcc/device/include/mcs51"
else
  echo "Unable to locate SDCC mcs51 include directory" >&2
  exit 1
fi

if [ ! -f "$CONVERTER_CLI" ] && [ -f "$WORKSPACE_DIR/sdcc/tools/iar2sdcc/cli.py" ]; then
  CONVERTER_CLI="$WORKSPACE_DIR/sdcc/tools/iar2sdcc/cli.py"
fi

for required_bin in "$SDCC_BIN" "$PACKIHX_BIN" "$SDLD_BIN" "$SDAS8051_BIN"; do
  if [ ! -x "$required_bin" ]; then
    echo "Missing required SDCC tool: $required_bin" >&2
    exit 1
  fi
done
if [ ! -f "$CONVERTER_CLI" ]; then
  echo "Missing iar2sdcc converter: $CONVERTER_CLI" >&2
  exit 1
fi

export PATH="$SDCC_TOOLCHAIN_DIR/bin:$PATH"

ABI_ARGS=()
STACK_ARGS=()
EXTRA_ARGS=()
RUNTIME_PORT_SUFFIX=""
RUNTIME_PORT_NAME="$SDCC_MODEL"
RUNTIME_MODELFLAGS="$MODEL_FLAG"
RUNTIME_LIB_DIR="$BASE_RUNTIME_LIB_DIR"

if [ -n "$SDCC_EXTRA_ARGS" ]; then
  # Intentional word splitting: caller passes a plain CLI fragment.
  read -r -a EXTRA_ARGS <<<"$SDCC_EXTRA_ARGS"
fi

case "$SDCC_STACK_MODE" in
  default)
    ;;
  stack-auto)
    STACK_ARGS=(--stack-auto)
    RUNTIME_PORT_SUFFIX="-stack-auto"
    ;;
  stack-auto-xstack|xstack-auto)
    STACK_ARGS=(--stack-auto --xstack)
    if [ -n "$SDCC_XSTACK_LOC" ]; then
      STACK_ARGS+=(--xstack-loc "$SDCC_XSTACK_LOC")
    fi
    RUNTIME_PORT_SUFFIX="-xstack-auto"
    ;;
  *)
    echo "Unsupported SDCC_STACK_MODE: $SDCC_STACK_MODE" >&2
    exit 1
    ;;
esac

RUNTIME_PORT_NAME="${SDCC_MODEL}${RUNTIME_PORT_SUFFIX}"
STACK_ARGS_JOINED=""
if [ "${#STACK_ARGS[@]}" -gt 0 ]; then
  STACK_ARGS_JOINED=" ${STACK_ARGS[*]}"
fi
RUNTIME_MODELFLAGS="${MODEL_FLAG}${STACK_ARGS_JOINED}"
if [ -d "$DEVICE_LIB_DIR/build/$RUNTIME_PORT_NAME" ]; then
  RUNTIME_LIB_DIR="$DEVICE_LIB_DIR/build/$RUNTIME_PORT_NAME"
else
  RUNTIME_LIB_DIR="$DEVICE_LIB_DIR/$RUNTIME_PORT_NAME"
fi

case "$SDCC_ABI" in
  iar)
    ABI_ARGS=(--abi-iar)
    RUNTIME_MODELFLAGS="$RUNTIME_MODELFLAGS --abi-iar"
    if [ -d "$DEVICE_LIB_DIR/build/${RUNTIME_PORT_NAME}-iar" ]; then
      RUNTIME_LIB_DIR="$DEVICE_LIB_DIR/build/${RUNTIME_PORT_NAME}-iar"
    else
      RUNTIME_LIB_DIR="$DEVICE_LIB_DIR/${RUNTIME_PORT_NAME}-iar"
    fi
    ;;
  none|sdcc|default)
    ;;
  *)
    echo "Unsupported SDCC_ABI: $SDCC_ABI" >&2
    exit 1
    ;;
esac

BUNDLED_RUNTIME_LIB_DIR=""
runtime_dir_name="$RUNTIME_PORT_NAME"
if [ "$SDCC_ABI" = "iar" ]; then
  runtime_dir_name="${runtime_dir_name}-iar"
fi
if [ -d "$RUNTIME_ROOT_DIR/$runtime_dir_name" ]; then
  BUNDLED_RUNTIME_LIB_DIR="$RUNTIME_ROOT_DIR/$runtime_dir_name"
  RUNTIME_LIB_DIR="$BUNDLED_RUNTIME_LIB_DIR"
fi

if [ -z "$SDCC_DEFAULT_CODESEG" ] && [ "$SDCC_MODEL" = "huge" ]; then
  SDCC_DEFAULT_CODESEG="BANKED_CODE"
fi

mkdir -p "$OBJ_DIR"
rm -f "$IHX_FILE" "$HEX_FILE" "$LOGICAL_HEX_FILE"

case "$BUILD_SAMPLELIGHT_MODE" in
  full|prepare-native)
    "$PYTHON_BIN" "$SCRIPT_DIR/manifest_paths.py" \
      --manifest "$MANIFEST" \
      --output "$NORMALIZED_MANIFEST" \
      --repo-root "$ZSTACK_DIR"

    "$PYTHON_BIN" "$COMPILE_PLAN_SCRIPT" \
      --manifest "$NORMALIZED_MANIFEST" \
      --output "$COMPILE_PLAN_JSON"
    ;;
  compile-entry|link-only)
    if [ ! -f "$NORMALIZED_MANIFEST" ] || [ ! -f "$COMPILE_PLAN_JSON" ]; then
      echo "Missing native prepare outputs: $NORMALIZED_MANIFEST or $COMPILE_PLAN_JSON" >&2
      exit 1
    fi
    ;;
  *)
    echo "Unsupported BUILD_SAMPLELIGHT_MODE: $BUILD_SAMPLELIGHT_MODE" >&2
    exit 1
    ;;
esac

MANIFEST="$NORMALIZED_MANIFEST"

if [ -z "$SDCC_CODE_SIZE" ]; then
  if [ "$SDCC_MODEL" = "huge" ]; then
    SDCC_CODE_SIZE=$(
      "$PYTHON_BIN" - "$MANIFEST" "$SCRIPT_DIR" "$SDCC_CODE_LOC" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
script_dir = Path(sys.argv[2])
code_loc = int(sys.argv[3], 0)
sys.path.insert(0, str(script_dir))

from gen_aslink_area_bases import _discover_xcl, _parse_xcl

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
xcl_path = _discover_xcl(manifest, manifest_path)
if xcl_path is None:
    print("0x8000")
    raise SystemExit(0)

placements = _parse_xcl(
    xcl_path,
    {
        "_CODE_START": code_loc,
        "_CODE_END": 0x7FFF,
        "_XDATA_START": 0x0001,
        "_XDATA_END": 0x1EFF,
    },
)

max_end = None
for placement in placements.values():
    if str(placement.get("memory")) != "CODE":
        continue
    for start, end in placement.get("ranges", []):
        if max_end is None or int(end) > max_end:
            max_end = int(end)

if max_end is None or max_end < code_loc:
    print("0x8000")
else:
    print(hex(max_end - code_loc + 1))
PY
    )
  else
    SDCC_CODE_SIZE=0x8000
  fi
fi

runtime_libs_present() {
  local lib_dir=$1
  [ -f "$lib_dir/mcs51.lib" ] &&
    [ -f "$lib_dir/libsdcc.lib" ] &&
    [ -f "$lib_dir/libint.lib" ] &&
    [ -f "$lib_dir/liblong.lib" ] &&
    [ -f "$lib_dir/libfloat.lib" ]
}

ensure_runtime_libs() {
  ensure_mcs51_runtime_lib() {
    local port_name=$1
    local port_dir=$2

    if [ -f "$port_dir/mcs51.lib" ]; then
      return
    fi

    mkdir -p "$port_dir"
    make -C "$DEVICE_LIB_DIR/mcs51" PORT="$port_name"
  }

  if runtime_libs_present "$RUNTIME_LIB_DIR"; then
    return
  fi

  if [ -n "$BUNDLED_RUNTIME_LIB_DIR" ] && runtime_libs_present "$BUNDLED_RUNTIME_LIB_DIR"; then
    RUNTIME_LIB_DIR="$BUNDLED_RUNTIME_LIB_DIR"
    return
  fi

  if [ "$RUNTIME_BUILD_CAPABLE" -ne 1 ]; then
    echo "Required runtime libraries are missing: $RUNTIME_LIB_DIR" >&2
    echo "This SDCC toolchain does not provide build metadata to rebuild them." >&2
    exit 1
  fi

  (
    cd "$SDCC_TOOLCHAIN_DIR"
    ./config.status \
      device/lib/Makefile \
      device/lib/mcs51/Makefile \
      device/lib/small/Makefile \
      device/lib/medium/Makefile \
      device/lib/large/Makefile \
      device/lib/huge/Makefile >/dev/null
  )

  make -C "$DEVICE_LIB_DIR" \
    PORT="$RUNTIME_PORT_NAME" \
    PORTDIR="build/$RUNTIME_PORT_NAME" \
    MODELFLAGS="${MODEL_FLAG}${STACK_ARGS_JOINED}" \
    PORTINCDIR="$PORT_INC_DIR" \
    objects
  ensure_mcs51_runtime_lib "$RUNTIME_PORT_NAME" "$DEVICE_LIB_DIR/build/$RUNTIME_PORT_NAME"

  if [ "$SDCC_ABI" != "iar" ]; then
    return
  fi

  make -C "$DEVICE_LIB_DIR" \
    PORT="${RUNTIME_PORT_NAME}-iar" \
    PORTDIR="build/${RUNTIME_PORT_NAME}-iar" \
    MODELFLAGS="$RUNTIME_MODELFLAGS" \
    PORTINCDIR="$PORT_INC_DIR" \
    objects
  ensure_mcs51_runtime_lib "${RUNTIME_PORT_NAME}-iar" "$RUNTIME_LIB_DIR"
}

runtime_lib_flags=()

prepare_compile_source() {
  local mode=$1
  local input_src=$2
  local output_src=$3

  "$PYTHON_BIN" "$PREPARE_SOURCE_SCRIPT" \
    --mode "$mode" \
    --input "$input_src" \
    --output "$output_src"
}

prepare_header_overlays() {
  local entry mode rel_spec rel_path input_src output_src candidate sdk_rel_root
  sdk_rel_root=${ZSTACK_DIR#"$WORKSPACE_DIR"/}
  for entry in "${HEADER_OVERLAYS[@]}"; do
    mode=${entry%%:*}
    rel_spec=${entry#*:}
    input_src=""
    IFS='|' read -r -a candidates <<<"$rel_spec"
    for candidate in "${candidates[@]}"; do
      if [ -f "$ZSTACK_DIR/$candidate" ]; then
        rel_path=$candidate
        input_src="$ZSTACK_DIR/$candidate"
        break
      fi
    done
    if [ -z "$input_src" ]; then
      continue
    fi
    output_src="$GENERATED_SRC_DIR/$sdk_rel_root/$rel_path"
    prepare_compile_source "$mode" "$input_src" "$output_src"
  done
}

prepare_header_aliases() {
  local entry alias_rel source_rel source_path alias_path sdk_rel_root
  sdk_rel_root=${ZSTACK_DIR#"$WORKSPACE_DIR"/}
  for entry in "${HEADER_ALIASES[@]}"; do
    IFS='|' read -r alias_rel source_rel <<<"$entry"
    source_path="$ZSTACK_DIR/$source_rel"
    [ -f "$source_path" ] || continue
    alias_path="$GENERATED_SRC_DIR/$sdk_rel_root/$alias_rel"
    prepare_compile_source "copy" "$source_path" "$alias_path"
  done
}

compute_object_path() {
  local compile_src=$1
  local rel_path=${compile_src#"$WORKSPACE_DIR"/}
  case "$compile_src" in
    *.c)
      printf '%s\n' "$OBJ_DIR/${rel_path%.c}.rel"
      ;;
    *.asm)
      printf '%s\n' "$OBJ_DIR/${rel_path%.asm}.rel"
      ;;
    *)
      echo "Unsupported compile source type: $compile_src" >&2
      exit 1
      ;;
  esac
}

compile_entry_json() {
  local entry_json=$1
  local src
  local compile_src
  local codeseg
  local constseg
  local prepare
  local skip
  local error
  local rel_path
  local prepared_src
  local obj_path
  local obj_dir

  src=$(printf '%s\n' "$entry_json" | jq -r '.source')
  compile_src=$(printf '%s\n' "$entry_json" | jq -r '.compile_source')
  codeseg=$(printf '%s\n' "$entry_json" | jq -r '.codeseg // empty')
  constseg=$(printf '%s\n' "$entry_json" | jq -r '.constseg // empty')
  prepare=$(printf '%s\n' "$entry_json" | jq -r '.prepare // empty')
  skip=$(printf '%s\n' "$entry_json" | jq -r '.skip')
  error=$(printf '%s\n' "$entry_json" | jq -r '.error // empty')

  if [ -n "$error" ]; then
    echo "$error" >&2
    exit 1
  fi
  if [ "$skip" = "true" ]; then
    return 0
  fi

  rel_path=${compile_src#"$WORKSPACE_DIR"/}
  prepared_src=$compile_src
  if [ -n "$prepare" ]; then
    prepared_src="$GENERATED_SRC_DIR/$rel_path"
    prepare_compile_source "$prepare" "$compile_src" "$prepared_src"
  fi

  obj_path=$(compute_object_path "$compile_src")
  obj_dir=$(dirname "$obj_path")
  mkdir -p "$obj_dir"

  if [ "$REUSE_OBJECTS" = "1" ] && [ -f "$obj_path" ]; then
    OBJECTS+=("$obj_path")
    return 0
  fi

  if [[ "$compile_src" == *.asm ]]; then
    assemble_with_sdas8051 "$prepared_src" "$obj_path"
  else
    COMPILE_ARGS=("${SDCC_ARGS[@]}")
    if [ -z "$codeseg" ] && [ -n "$SDCC_DEFAULT_CODESEG" ]; then
      COMPILE_ARGS+=(--codeseg "$SDCC_DEFAULT_CODESEG")
    fi
    if [ -n "$codeseg" ]; then
      COMPILE_ARGS+=(--codeseg "$codeseg")
    fi
    if [ -n "$constseg" ]; then
      COMPILE_ARGS+=(--constseg "$constseg")
    fi

    "$SDCC_BIN" -c "${COMPILE_ARGS[@]}" -o "$obj_path" "$prepared_src"
  fi
  OBJECTS+=("$obj_path")
}

load_objects_from_compile_plan() {
  OBJECTS=()
  while IFS= read -r entry_json; do
    local skip
    local error
    local compile_src
    local obj_path

    skip=$(printf '%s\n' "$entry_json" | jq -r '.skip')
    error=$(printf '%s\n' "$entry_json" | jq -r '.error // empty')
    compile_src=$(printf '%s\n' "$entry_json" | jq -r '.compile_source')

    if [ -n "$error" ]; then
      echo "$error" >&2
      exit 1
    fi
    if [ "$skip" = "true" ]; then
      continue
    fi

    obj_path=$(compute_object_path "$compile_src")
    if [ ! -f "$obj_path" ]; then
      echo "Missing object for link-only mode: $obj_path" >&2
      exit 1
    fi
    OBJECTS+=("$obj_path")
  done < <(jq -c '.[]' "$COMPILE_PLAN_JSON")
}

assemble_with_sdas8051() {
  local input_src=$1
  local output_obj=$2
  local output_dir
  local asm_name

  output_dir=$(dirname "$output_obj")
  asm_name=$(basename "$input_src")

  cp "$input_src" "$output_dir/$asm_name"
  (
    cd "$output_dir"
    "$SDAS8051_BIN" -olsgff "$asm_name"
  )
}

run_iar_converter() {
  mkdir -p "$CONVERTED_DIR"
  IAR2SDCC_SDCC_BIN="$SDCC_BIN" \
  IAR2SDCC_SDAS_BIN="$SDAS8051_BIN" \
  IAR2SDCC_SDCC_MODEL="$SDCC_MODEL" \
  IAR2SDCC_SDCC_ABI="$SDCC_ABI" \
  "$PYTHON_BIN" "$CONVERTER_CLI" \
    convert \
    --manifest "$MANIFEST" \
    --out-dir "$CONVERTED_DIR" >/dev/null
}

append_converted_artifacts() {
  CONVERTED_ARTIFACTS=()
  if [ ! -f "$CONVERTED_MANIFEST" ]; then
    echo "Converted manifest not found: $CONVERTED_MANIFEST" >&2
    exit 1
  fi

  while IFS= read -r artifact; do
    [ -n "$artifact" ] || continue
    CONVERTED_ARTIFACTS+=("$artifact")
  done < <(jq -r '.emitted_artifacts[]?' "$CONVERTED_MANIFEST")
}

link_with_sdcc() {
  local link_cmd=("$SDCC_BIN" -mmcs51 "$MODEL_FLAG")

  if [ "${#STACK_ARGS[@]}" -gt 0 ]; then
    link_cmd+=("${STACK_ARGS[@]}")
  fi
  if [ "${#ABI_ARGS[@]}" -gt 0 ]; then
    link_cmd+=("${ABI_ARGS[@]}")
  fi
  link_cmd+=(
    --out-fmt-ihx
    --code-loc "$SDCC_CODE_LOC"
    --code-size "$SDCC_CODE_SIZE"
    --xram-loc "$SDCC_XRAM_LOC"
    --xram-size "$SDCC_XRAM_SIZE"
    "${runtime_lib_flags[@]}"
    -o "$IHX_FILE"
    "${OBJECTS[@]}"
  )

  if [ "${#CONVERTED_ARTIFACTS[@]}" -gt 0 ]; then
    link_cmd+=("${CONVERTED_ARTIFACTS[@]}")
  fi

  "${link_cmd[@]}" >"$LINK_LOG" 2>&1
}

write_second_pass_lk() {
  local out_lk=$1
  if [ -f "$CONVERTED_MANIFEST" ]; then
    "$PYTHON_BIN" "$ASLINK_AREA_BASES_SCRIPT" \
      --manifest "$MANIFEST" \
      --converted-manifest "$CONVERTED_MANIFEST" \
      --code-loc "$SDCC_CODE_LOC" \
      --code-size "$SDCC_CODE_SIZE" \
      --xram-loc "$SDCC_XRAM_LOC" \
      --xram-size "$SDCC_XRAM_SIZE" >"$ASLINK_AREA_BASES_LK"
  else
    : >"$ASLINK_AREA_BASES_LK"
  fi
  "$PYTHON_BIN" - "$ARTIFACT_BASE.lk" "$CONVERTED_MANIFEST" "$out_lk" <<'PY'
import json
import sys
from pathlib import Path

base_lk = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
manifest = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
out_lk = Path(sys.argv[3])
area_bases_lk = out_lk.parent / "aslink-area-bases.lk"
filtered = [
    line
    for line in base_lk
    if "/iar-converted/" not in line and line not in ("", "-e")
]
extra_lines = []
if area_bases_lk.exists():
    extra_lines = [
        line
        for line in area_bases_lk.read_text(encoding="utf-8").splitlines()
        if line
    ]
out_lk.write_text(
    "\n".join(filtered + extra_lines + manifest.get("emitted_artifacts", []) + ["-e"]) + "\n",
    encoding="utf-8",
)
PY
}

link_with_sdld_second_pass() {
  local pass_lk=$1
  local strict_rc=1

  rm -f "$IHX_FILE"
  rm -f "$SECOND_PASS_STRICT_LOG" "$SECOND_PASS_RELAXED_LOG"
  rm -f "$OUT_DIR/second-pass.stdout" "$OUT_DIR/second-pass-relaxed.stdout"

  if ! "$SDLD_BIN" -n -f "$pass_lk" >"$OUT_DIR/second-pass.stdout" 2>"$SECOND_PASS_STRICT_LOG"; then
    strict_rc=$?
  fi

  if [ -s "$IHX_FILE" ]; then
    return 0
  fi

  case "$RELAX_MEMORY" in
    1|true|TRUE|yes|YES|auto|AUTO)
      if ! SDLD_RELAX_MEMORY=1 "$SDLD_BIN" -n -f "$pass_lk" >"$OUT_DIR/second-pass-relaxed.stdout" 2>"$SECOND_PASS_RELAXED_LOG"; then
        strict_rc=$?
      fi
      ;;
  esac

  if [ -s "$IHX_FILE" ]; then
    return 0
  fi

  return "${strict_rc:-1}"
}

emit_link_failure_report() {
  local log_path=${1:-$LINK_LOG}
  local report_json=${2:-$LINK_REPORT_JSON}
  iar_libraries=()
  while IFS= read -r library; do
    [ -n "$library" ] || continue
    iar_libraries+=("$library")
  done < <(jq -r '.iar_libraries[]' "$MANIFEST")
  if [ "${#iar_libraries[@]}" -eq 0 ]; then
    return
  fi

  IAR2SDCC_SDCC_BIN="$SDCC_BIN" \
  IAR2SDCC_SDAS_BIN="$SDAS8051_BIN" \
  IAR2SDCC_SDCC_MODEL="$SDCC_MODEL" \
  IAR2SDCC_SDCC_ABI="$SDCC_ABI" \
  "$PYTHON_BIN" "$CONVERTER_CLI" \
    convert \
    --manifest "$MANIFEST" \
    --out-dir "$CONVERTED_DIR" \
    --link-log "$log_path" >/dev/null || true

  if ! "$PYTHON_BIN" "$CONVERTER_CLI" \
    resolve-log \
    --json \
    "$log_path" \
    "${iar_libraries[@]}" >"$report_json"; then
    rm -f "$report_json"
    return
  fi

  echo "Link log: $log_path" >&2
  echo "Undefined symbol ownership report: $report_json" >&2
  echo "Updated converter report: $CONVERTED_DIR/report.txt" >&2
  echo "Updated module plan: $CONVERTED_MODULE_PLAN" >&2
}

rerun_link_with_updated_converter() {
  local pass_lk=$1
  append_converted_artifacts
  write_second_pass_lk "$pass_lk"
  if ! link_with_sdld_second_pass "$pass_lk"; then
    return 1
  fi

  if [ -s "$SECOND_PASS_RELAXED_LOG" ]; then
    cp "$SECOND_PASS_RELAXED_LOG" "$LINK_LOG"
  else
    cp "$SECOND_PASS_STRICT_LOG" "$LINK_LOG"
  fi
  return 0
}

current_link_signature() {
  "$PYTHON_BIN" - "$LINK_LOG" <<'PY'
import re
import sys
from pathlib import Path

log = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
undefined = len(set(re.findall(r"Undefined Global (\S+)", log)))
multiple = len(set(re.findall(r"Multiple definition of (\S+)", log)))
print(f"{undefined}:{multiple}")
PY
}

rerun_converter_until_stable() {
  local max_passes=${1:-8}
  local pass_index=3
  local previous_signature=""

  while [ "$pass_index" -le "$max_passes" ]; do
    local signature
    signature=$(current_link_signature)
    if [ "$signature" = "0:0" ]; then
      break
    fi
    if [ -n "$previous_signature" ] && [ "$signature" = "$previous_signature" ]; then
      break
    fi
    previous_signature="$signature"

    local pass_lk="$OUT_DIR/pass-${pass_index}.lk"
    if ! rerun_link_with_updated_converter "$pass_lk"; then
      break
    fi
    emit_link_failure_report "$LINK_LOG" "$FINAL_LINK_REPORT_JSON"
    pass_index=$((pass_index + 1))
  done
}

ensure_runtime_libs
runtime_lib_flags=("-L" "$RUNTIME_LIB_DIR")
if [ "$BUILD_SAMPLELIGHT_MODE" != "compile-entry" ] || [ ! -f "$CONVERTED_MANIFEST" ]; then
  run_iar_converter
fi

SDCC_ARGS=(
  -mmcs51
  "$MODEL_FLAG"
)

if [ "${#STACK_ARGS[@]}" -gt 0 ]; then
  SDCC_ARGS+=("${STACK_ARGS[@]}")
fi
if [ "${#ABI_ARGS[@]}" -gt 0 ]; then
  SDCC_ARGS+=("${ABI_ARGS[@]}")
fi

while IFS= read -r preinclude; do
  [ -n "$preinclude" ] || continue
  SDCC_ARGS+=("-Wp-include,$preinclude")
done < <(jq -r '.preinclude_files[]?' "$MANIFEST")

SDCC_ARGS+=("-Wp-include,$CFG_HEADER")

if [ "${#EXTRA_ARGS[@]}" -gt 0 ]; then
  SDCC_ARGS+=("${EXTRA_ARGS[@]}")
fi

while IFS= read -r def; do
  SDCC_ARGS+=("-D$def")
done < <(jq -r '.sdcc_cli_defines[]' "$MANIFEST")

case "$BUILD_SAMPLELIGHT_MODE" in
  full|prepare-native)
    prepare_header_overlays
    prepare_header_aliases
    ;;
esac

while IFS= read -r inc; do
  rel_inc=${inc#"$WORKSPACE_DIR"/}
  SDCC_ARGS+=("-I$GENERATED_SRC_DIR/$rel_inc")
  SDCC_ARGS+=("-I$inc")
done < <(jq -r '.include_dirs[]' "$MANIFEST")

OBJECTS=()
CONVERTED_ARTIFACTS=()

case "$BUILD_SAMPLELIGHT_MODE" in
  prepare-native)
    exit 0
    ;;
  compile-entry)
    if [ -z "$ENTRY_JSON_FILE" ] || [ ! -f "$ENTRY_JSON_FILE" ]; then
      echo "compile-entry mode requires ENTRY_JSON_FILE=<path>" >&2
      exit 1
    fi
    compile_entry_json "$(cat "$ENTRY_JSON_FILE")"
    exit 0
    ;;
  link-only)
    load_objects_from_compile_plan
    ;;
  full)
    while IFS= read -r entry_json; do
      compile_entry_json "$entry_json"
    done < <(jq -c '.[]' "$COMPILE_PLAN_JSON")
    ;;
  *)
    echo "Unsupported BUILD_SAMPLELIGHT_MODE: $BUILD_SAMPLELIGHT_MODE" >&2
    exit 1
    ;;
esac

append_converted_artifacts

FIRST_LINK_RC=0
if ! link_with_sdcc; then
  FIRST_LINK_RC=$?
fi

if [ "$FIRST_LINK_RC" -ne 0 ] || [ "$(current_link_signature)" != "0:0" ]; then
  cp "$LINK_LOG" "$FIRST_PASS_LINK_LOG"

  if [ "$FIRST_LINK_RC" -ne 0 ]; then
    cat "$LINK_LOG" >&2
    append_converted_artifacts
    SECOND_PASS_LK="$OUT_DIR/second-pass.lk"
    write_second_pass_lk "$SECOND_PASS_LK"
    if ! link_with_sdld_second_pass "$SECOND_PASS_LK"; then
      if [ -s "$SECOND_PASS_RELAXED_LOG" ]; then
        cp "$SECOND_PASS_RELAXED_LOG" "$LINK_LOG"
        cat "$SECOND_PASS_RELAXED_LOG" >&2
      else
        cp "$SECOND_PASS_STRICT_LOG" "$LINK_LOG"
        cat "$SECOND_PASS_STRICT_LOG" >&2
      fi
      exit 1
    fi
    if [ -s "$SECOND_PASS_RELAXED_LOG" ]; then
      cp "$SECOND_PASS_RELAXED_LOG" "$LINK_LOG"
    else
      cp "$SECOND_PASS_STRICT_LOG" "$LINK_LOG"
    fi
  fi

  emit_link_failure_report "$FIRST_PASS_LINK_LOG" "$FIRST_PASS_REPORT_JSON"
  rerun_converter_until_stable 8
fi

if [ "$(current_link_signature)" != "0:0" ]; then
  cat "$LINK_LOG" >&2
  echo "Link completed with unresolved or multiply-defined symbols: $(current_link_signature)" >&2
  exit 1
fi

if [ -s "$LINK_LOG" ]; then
  cat "$LINK_LOG"
fi

if [ ! -s "$IHX_FILE" ]; then
  echo "IHX not produced: $IHX_FILE" >&2
  exit 1
fi

"$PACKIHX_BIN" "$IHX_FILE" > "$LOGICAL_HEX_FILE"

"$PYTHON_BIN" "$REMAP_BANKED_HEX_SCRIPT" \
  --manifest "$MANIFEST" \
  --input-hex "$LOGICAL_HEX_FILE" \
  --output-hex "$HEX_FILE" >/dev/null

echo "IHX: $IHX_FILE"
echo "Logical HEX: $LOGICAL_HEX_FILE"
echo "HEX: $HEX_FILE"
