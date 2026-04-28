This directory contains helper tooling for moving z-stack_3.0.2 CC2530 IAR projects toward SDCC builds.

`extract_iar_project.py` reads an IAR `.ewp` and exports one configuration into JSON:
- preprocessor defines
- include directories
- source files
- referenced `.cfg` files
- linker `.xcl`
- referenced IAR binary libraries
- SDCC-friendly define split:
  - `sdcc_cli_defines` for plain `-D...` usage
  - `sdcc_header_defines` for macros that need a preinclude header

Example:

```sh
python3 Tools/sdcc/extract_iar_project.py \
  Projects/zstack/HomeAutomation/SampleLight/CC2530DB/SampleLight.ewp \
  --config CoordinatorEB \
  --output Tools/sdcc/manifests/samplelight-cc2530db-coordinator.json \
  --sdcc-header-output Tools/sdcc/manifests/samplelight-cc2530db-coordinator-sdcc-cfg.h
```

The generated SDCC header is intended for `-Wp-include,<path>` and normalizes IAR-style cfg macros such as:
- `DEFAULT_KEY="{0}"` -> `#define DEFAULT_KEY {0}`
- `CONST="const __code"` -> `#define CONST const __code`
- `GENERIC=__generic` -> `#define GENERIC`

Optional `sdcc_compile_overrides` entries in the manifest can pin individual
translation units to named SDCC sections. Current `SampleLight` uses this for:
- `hal_startup.c` -> `--codeseg CSTART`
- `OSAL_Math.s51` (compiled as `OSAL_Math.c`) -> `--codeseg NEAR_CODE`

This override layer is intentionally conservative. It does not yet try to
translate IAR's function-local `#pragma location="..."` into SDCC for larger
files such as `hal_sleep.c`, where placement and alignment constraints apply to
one function rather than the whole translation unit.

`build_samplelight.sh` performs an out-of-tree SDCC build for the extracted
`samplelight-cc2530db-coordinator` manifest using only local SDCC tools.
It also applies the current SDCC compatibility substitutions for the two IAR-only
assembler sources:
- `OSAL_Math.s51` -> `Components/osal/mcu/cc2530/OSAL_Math.c`
- `chipcon_cstartup.s51` -> skipped in favor of SDCC startup plus `__sdcc_external_startup()`

Important current limitation:
- the SampleLight IAR project references `Router-Pro.lib`, `Security.lib`, and `TIMAC-CC2530.lib`
- these binaries are IAR 8051 libraries with `__code_model = banked`, `__data_model = large`,
  and `__calling_convention = xdata_reentrant`
- SDCC's `aslink` still cannot consume these `.lib` files directly
- the current workflow therefore uses `sdcc/tools/iar2sdcc` as a preprocessing stage:
  - first-pass SDCC link discovers undefined globals
  - `iar2sdcc` maps them to candidate library modules
  - selected module slices are exported from the IAR archives
  - each slice is currently converted into a prototype SDCC `.rel` plus metadata, with stub fallback
- this is enough to exercise the ABI/converter pipeline without any IAR for Windows tools, but it is
  not yet a semantic IAR object-code translation for all modules

You can inspect library metadata directly with:

```sh
python3 Tools/sdcc/inspect_iar_lib.py \
  Projects/zstack/Libraries/TI2530DB/bin/Router-Pro.lib \
  Projects/zstack/Libraries/TI2530DB/bin/Security.lib \
  Projects/zstack/Libraries/TIMAC/bin/TIMAC-CC2530.lib
```

Useful environment overrides for `build_samplelight.sh`:
- `SDCC_MODEL=large` or `SDCC_MODEL=huge`
- `SDCC_STACK_MODE=default`, `stack-auto`, or `stack-auto-xstack`
- `SDCC_CODE_SIZE=0x8000` to override the linker code window
- `SDCC_XRAM_LOC=0x0001` and `SDCC_XRAM_SIZE=0x1EFF`
- `SDCC_XSTACK_LOC=<addr>` when `SDCC_STACK_MODE=stack-auto-xstack`

## IAR library conversion workflow

Generate SampleLight conversion outputs:

```bash
python3 sdcc/tools/iar2sdcc/cli.py \
  convert \
  --manifest z-stack_3.0.2/Tools/sdcc/manifests/samplelight-cc2530db-coordinator.json \
  --out-dir sdcc-build/iar-converted/samplelight-cc2530db-coordinator
```

Inspect a standalone IAR object-like member or extracted slice:

```bash
python3 sdcc/tools/iar2sdcc/cli.py \
  inspect-object \
  --json \
  z-stack_3.0.2/Projects/zstack/Libraries/TI2530DB/bin/ecc.r51
```

Convert a standalone object-like member into a prototype SDCC `.rel`:

```bash
python3 sdcc/tools/iar2sdcc/cli.py \
  convert-object \
  z-stack_3.0.2/Projects/zstack/Libraries/TI2530DB/bin/ecc.r51 \
  --out-dir sdcc-build/iar-converted/ecc
```

When `build_samplelight.sh` needs library-owned symbols, the converter output directory now typically contains:
- `manifest.json`
- `report.txt`
- `module-plan.json`
- `module-slices/<Library>/<module>.bin`
- `<module>.rel`
- `<module>.convert.json`

Run the SampleLight build:

```bash
bash z-stack_3.0.2/Tools/sdcc/build_samplelight.sh \
  sdcc-build/zstack-samplelight-cc2530db-coordinator
```

Build a real `CC2530F256` coordinator hex without IAR tools:

```bash
bash z-stack_3.0.2/Tools/sdcc/build_samplelight_cc2530f256_hex.sh \
  sdcc-build/zstack-samplelight-cc2530db-coordinator-stackauto-f256-hex
```

This wrapper generates a reduced manifest that removes the MT task sources,
touchlink/inter-PAN pieces, and the LCD UI source, then runs the normal SDCC
flow with:
- `SDCC_STACK_MODE=stack-auto`
- `SDCC_CODE_SIZE=0x40000`
- `RELAX_MEMORY=0`

It also validates that the final flash end stays below the reserved NV/lockbits
ceiling at `0x3c800`.

Current validated coordinator profile additionally trims board-facing helpers:
- removes `xZTOOL_P1`, so `HAL_UART` falls back to `FALSE`
- forces `HAL_KEY=FALSE`
- substitutes minimal `zcl_sampleapps_ui`, `hal_lcd`, and `hal_led`
- keeps the `hal_lcd` / `hal_led` shims in `HOME`

This is a headless coordinator-oriented build profile. It preserves the Zigbee
stack and security libraries, but it does not keep the original EB UART/key/LCD
interaction surface.

Verified output example:
- `sdcc-build/zstack-samplelight-cc2530db-coordinator-huge-stackauto-f256-slim-fb0-lcd0-uart0-key0/samplelight-cc2530db-coordinator.hex`
- validated flash end: `0x3bff1`

## Step 1: IAR import bundle

`iar_import.py` implements the normalization/import step that sits before any
plain CMake build. It stages a self-contained bundle with:
- `src/` copied SDK tree with optional vendor patch applied
- `include/` generated SDCC cfg header plus normalized overlay/alias headers
- `libs/original/` copied IAR libraries from the project manifest
- `libs/converted/` `iar2sdcc convert` output for the copied libraries
- `metadata/manifest.json` normalized manifest rooted at the staged tree
- `compile-plan.json`, `layout.json`, `cmake/project.cmake`, `report.json`, `report.txt`

Example for the patched `CC2530.ewp` / `ZNP-with-SBL` target:

```bash
python3 z-stack_3.0.2/Tools/sdcc/iar_import.py \
  --project z-stack_3.0.2/Projects/zstack/ZNP/CC253x/CC2530.ewp \
  --config ZNP-with-SBL \
  --profile balanced \
  --out-dir sdcc-build/znp-cc2530-import \
  --sdcc-toolchain-root /path/to/sdcc-build
```

This step is intentionally independent from the later build:
- it does not require IAR for Windows tools
- it leaves the imported project as ordinary files plus JSON/CMake metadata
- `cmake/project.cmake` is just a handoff descriptor for the next stage

Current scope:
- known-good import defaults are wired for `CC2530 ZNP-with-SBL`
- non-ZNP imports currently support `--profile full`
- library conversion at this step is still metadata-driven; full module
  selection depends on later link feedback

## ZNP `CC2530 ZNP-with-SBL`

The patched coordinator firmware from
`Z-Stack-firmware/coordinator/Z-Stack_3.0.x/COMPILE.md` can be built with SDCC
without IAR tools.

Prerequisite:
- apply `firmware_CC2531_CC2530.patch` to a vanilla `z-stack_3.0.2` tree first;
  the build expects the patched `Projects/zstack/ZNP/Source/preinclude.h` and
  patched `znp.cfg`

Prepare the derived manifest and generated SDCC header:

```bash
python3 z-stack_3.0.2/Tools/sdcc/prepare_znp_cc2530_with_sbl.py \
  --output-manifest sdcc-build/znp-cc2530-with-sbl/znp-cc2530-with-sbl.manifest.json \
  --output-header sdcc-build/znp-cc2530-with-sbl/znp-cc2530-with-sbl-sdcc-cfg.h
```

Optional SDCC-oriented balanced profile:

```bash
python3 z-stack_3.0.2/Tools/sdcc/prepare_znp_cc2530_with_sbl.py \
  --profile balanced \
  --output-manifest sdcc-build/znp-cc2530-with-sbl-balanced/znp-cc2530-with-sbl.manifest.json \
  --output-header sdcc-build/znp-cc2530-with-sbl-balanced/znp-cc2530-with-sbl-sdcc-cfg.h
```

Optional SDCC-oriented lean profile:

```bash
python3 z-stack_3.0.2/Tools/sdcc/prepare_znp_cc2530_with_sbl.py \
  --profile lean \
  --output-manifest sdcc-build/znp-cc2530-with-sbl-lean/znp-cc2530-with-sbl.manifest.json \
  --output-header sdcc-build/znp-cc2530-with-sbl-lean/znp-cc2530-with-sbl-sdcc-cfg.h
```

This derived manifest intentionally follows the manual IAR recipe:
- target configuration: `CC2530.ewp` / `ZNP-with-SBL`
- clear project `Defined symbols`
- add only `FIRMWARE_CC2530`
- keep `znp.cfg`, `f8wConfig.cfg`, `f8wZCL.cfg`, and patched `preinclude.h`

The optional `balanced` profile intentionally deviates from the IAR target:
- trims touchlink / CBKE / inter-PAN paths
- replaces `MT_AF.c` with a reduced shim
- disables `MT_APP`, `MT_UTIL`, `MT_SAPI`, `MT_GP`, `MT_APP_CONFIG`
- disables `MT_ZDO_MGMT`, `MT_ZDO_EXTENSIONS`, `MT_SYS_KEY_MANAGEMENT`
- keeps the build coordinator-only and replaces flash-backed NV with a volatile shim

The optional `lean` profile intentionally deviates further from the IAR target:
- trims optional MT/SAPI/inter-PAN/key-establishment sources that SDCC currently pulls in too aggressively
- constrains the stack build to coordinator-only mode

Build the final bootloader-compatible coordinator image:

```bash
bash z-stack_3.0.2/Tools/sdcc/build_znp_cc2530_with_sbl.sh \
  sdcc-build/zstack-znp-cc2530-with-sbl
```

Build the current working balanced profile:

```bash
ZNP_SDCC_PROFILE=balanced \
  bash z-stack_3.0.2/Tools/sdcc/build_znp_cc2530_with_sbl.sh
```

Build the smaller experimental lean profile:

```bash
ZNP_SDCC_PROFILE=lean \
  bash z-stack_3.0.2/Tools/sdcc/build_znp_cc2530_with_sbl.sh
```

The wrapper uses:
- `--abi-iar`
- `SDCC_CODE_LOC=0x2000`
- `SDCC_CODE_SIZE=0x3c800`
- `SDCC_STACK_MODE=stack-auto-xstack`
- `SDCC_XRAM_SIZE=0x1AFF`
- `SDCC_XSTACK_LOC=0x1B00`

It also validates:
- flash end below `0x3c800`
- no IHX data records inside the bootloader window below `0x2000`

Current verified status:
- the wrapper prepares the derived manifest and generated SDCC header correctly
- a clean smoke build completes C compilation and reaches the final link step
- the default `full` profile still overflows `FLASH` and `XDATA` at the final link, so the coordinator `hex` is not emitted yet
- the `balanced` profile emits a validated bootloader-compatible `ihx` and `hex`
- the experimental `lean` profile emits a validated bootloader-compatible `ihx` and `hex`

Verified balanced output:
- `sdcc-build/zstack-znp-cc2530-with-sbl-balanced-utilcut/CC2530ZNP-with-SBL.hex`
- validated flash end: `0x3c11c`

Verified lean output:
- `sdcc-build/zstack-znp-cc2530-with-sbl-lean/CC2530ZNP-with-SBL.hex`
