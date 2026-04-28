# zstack_3.0.2

This repository vendors the original `z-stack_3.0.2` SDK tree together with the SDCC helper overlay needed to build `CC2530ZNP-with-SBL` without IAR tools.

Local build:

```bash
cmake -S . -B build -DZSTACK_PROFILE=balanced
cmake --build build
```

Optional local toolchain override:

```bash
cmake -S . -B build \
  -DZSTACK_PROFILE=balanced \
  -DSDCC_TOOLCHAIN_ROOT=/path/to/sdcc
cmake --build build --target znp_cc2530_with_sbl
```

By default the CMake build downloads the Linux AMD64 SDCC toolchain release from `devbis/sdcc_iar`.

Artifacts are written to:

```text
build/out/znp_cc2530_with_sbl/<profile>/
```

The CMake flow stages a clean SDK copy, applies `firmware_CC2531_CC2530.patch`, prepares a derived ZNP manifest/header, creates an SDCC toolchain overlay with a compatible `sdcpp`, and then runs the existing SDCC backend on the staged tree.

GitHub Actions:

- workflow: `.github/workflows/build-znp-cc2530-with-sbl.yml`
- triggers: `push`, `pull_request`, `workflow_dispatch`
- uploaded artifacts: `build/out/znp_cc2530_with_sbl/`
