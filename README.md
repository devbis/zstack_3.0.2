# zstack_3.0.2

This repository vendors the original `z-stack_3.0.2` SDK tree together with the SDCC helper overlay needed to build `CC2530ZNP-with-SBL` without IAR tools.

Local build:

```bash
ZNP_SDCC_PROFILE=balanced ./ci/build_znp_cc2530_with_sbl.sh
```

By default the script downloads the Linux AMD64 SDCC toolchain release from `devbis/sdcc_iar` and writes build artifacts to `out/znp_cc2530_with_sbl/<profile>/`.

GitHub Actions:

- workflow: `.github/workflows/build-znp-cc2530-with-sbl.yml`
- triggers: `push`, `pull_request`, `workflow_dispatch`
- uploaded artifacts: `out/znp_cc2530_with_sbl/`

The build script stages a clean SDK copy, applies `firmware_CC2531_CC2530.patch`, and then runs `Tools/sdcc/build_znp_cc2530_with_sbl.sh` against the staged tree.
