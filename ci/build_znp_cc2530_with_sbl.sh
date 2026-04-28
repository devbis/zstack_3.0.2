#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
SDK_SOURCE_DIR="$REPO_ROOT/z-stack_3.0.2"
PATCH_FILE="$REPO_ROOT/firmware_CC2531_CC2530.patch"
PROFILE=${ZNP_SDCC_PROFILE:-balanced}
PYTHON_BIN=${PYTHON_BIN:-$(command -v python3)}
TOOLCHAIN_URL=${SDCC_TOOLCHAIN_URL:-https://github.com/devbis/sdcc_iar/releases/download/20260428/sdcc-linux-amd64.tar.xz}
WORK_ROOT=${WORK_ROOT:-"${RUNNER_TEMP:-$REPO_ROOT/.tmp}/zstack-znp-$PROFILE"}
STAGED_WORKSPACE="$WORK_ROOT/workspace"
STAGED_SDK_DIR="$STAGED_WORKSPACE/z-stack_3.0.2"
TOOLCHAIN_DIR=${SDCC_TOOLCHAIN_DIR:-"$WORK_ROOT/sdcc-build"}
TOOLCHAIN_TARBALL=${SDCC_TOOLCHAIN_TARBALL:-"$WORK_ROOT/sdcc-linux-amd64.tar.xz"}
STAGED_OUT_DIR="$WORK_ROOT/out/$PROFILE"
OUT_DIR=${OUT_DIR:-"$REPO_ROOT/out/znp_cc2530_with_sbl/$PROFILE"}

if [ ! -d "$SDK_SOURCE_DIR" ]; then
  echo "Missing SDK source directory: $SDK_SOURCE_DIR" >&2
  exit 1
fi
if [ ! -f "$PATCH_FILE" ]; then
  echo "Missing vendor patch: $PATCH_FILE" >&2
  exit 1
fi
if [ ! -d "$SDK_SOURCE_DIR/Tools/sdcc" ]; then
  echo "Missing SDCC helper overlay under SDK: $SDK_SOURCE_DIR/Tools/sdcc" >&2
  exit 1
fi

rm -rf "$WORK_ROOT"
mkdir -p "$STAGED_WORKSPACE" "$STAGED_OUT_DIR"
cp -R "$SDK_SOURCE_DIR" "$STAGED_SDK_DIR"

if ! patch -d "$STAGED_SDK_DIR" --forward -p1 < "$PATCH_FILE"; then
  echo "warning: firmware_CC2531_CC2530.patch did not apply cleanly; continuing with staged tree" >&2
fi

if [ ! -x "$TOOLCHAIN_DIR/bin/sdcc" ]; then
  mkdir -p "$TOOLCHAIN_DIR"
  if [ ! -f "$TOOLCHAIN_TARBALL" ]; then
    curl -L "$TOOLCHAIN_URL" -o "$TOOLCHAIN_TARBALL"
  fi
  tar -xf "$TOOLCHAIN_TARBALL" -C "$TOOLCHAIN_DIR"
fi

export PATH="$TOOLCHAIN_DIR/bin:$PATH"

ZNP_SDCC_PROFILE="$PROFILE" \
SDCC_BUILD_DIR="$TOOLCHAIN_DIR" \
PYTHON_BIN="$PYTHON_BIN" \
bash "$STAGED_SDK_DIR/Tools/sdcc/build_znp_cc2530_with_sbl.sh" "$STAGED_OUT_DIR"

mkdir -p "$OUT_DIR"
cp -R "$STAGED_OUT_DIR"/. "$OUT_DIR"/

echo "Profile: $PROFILE"
echo "Output: $OUT_DIR"
echo "HEX: $OUT_DIR/CC2530ZNP-with-SBL.hex"
