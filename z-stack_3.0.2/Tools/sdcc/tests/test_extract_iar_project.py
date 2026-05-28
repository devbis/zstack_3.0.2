import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract_iar_project import (
    collect_manifest,
    IarPathResolver,
    parse_cfg_preincludes,
    parse_preinclude_extra_opts,
    write_sdcc_header,
)


WORKSPACE = Path(__file__).resolve().parents[4]
ZSTACK = WORKSPACE / "z-stack_3.0.2"
CC2530_EWP = ZSTACK / "Projects" / "zstack" / "ZNP" / "CC253x" / "CC2530.ewp"


class ExtractIarProjectTest(unittest.TestCase):
    def test_parse_preinclude_extra_opts_extracts_headers(self) -> None:
        project_dir = ZSTACK / "Projects" / "zstack" / "ZNP" / "CC253x"
        extra_opts = [
            r"-f $PROJ_DIR$\..\Source\znp.cfg",
            r"--preinclude=$PROJ_DIR$\..\Source\preinclude.h",
        ]

        self.assertEqual(
            parse_preinclude_extra_opts(extra_opts, project_dir),
            [str((project_dir / ".." / "Source" / "preinclude.h").resolve())],
        )

    def test_parse_cfg_preincludes_extracts_headers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "znp.cfg"
            cfg_path.write_text(
                "--preinclude=preinclude.h\n"
                "-DMT_SYS_FUNC\n",
                encoding="utf-8",
            )

            self.assertEqual(
                parse_cfg_preincludes([str(cfg_path)]),
                [str((cfg_path.parent / "preinclude.h").resolve())],
            )

    def test_collect_manifest_uses_zstack_root_for_znp_project(self) -> None:
        manifest = collect_manifest(CC2530_EWP, "ZNP-with-SBL")

        self.assertEqual(manifest["repo_root"], str(ZSTACK.resolve()))

    def test_resolver_prefers_external_project_file_then_sdk_template(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_dir = root / "external" / "CC2530DB"
            sdk_project_dir = root / "sdk" / "Projects" / "zstack" / "HomeAutomation" / "SampleLight" / "CC2530DB"
            external_source = project_dir.parent / "Source" / "app.c"
            sdk_source = sdk_project_dir.parents[4] / "Components" / "hal" / "hal.c"

            external_source.parent.mkdir(parents=True)
            external_source.write_text("", encoding="utf-8")
            sdk_source.parent.mkdir(parents=True)
            sdk_source.write_text("", encoding="utf-8")

            resolver = IarPathResolver(project_dir, sdk_project_dir)

            self.assertEqual(
                resolver.resolve(r"$PROJ_DIR$\..\Source\app.c"),
                str(external_source.resolve()),
            )
            self.assertEqual(
                resolver.resolve(r"$PROJ_DIR$\..\..\..\..\..\Components\hal\hal.c"),
                str(sdk_source.resolve()),
            )

    def test_sdcc_header_includes_cc2530_iar_compatibility_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "cfg.h"

            write_sdcc_header(output, [{"name": "CONST", "value": "const __code"}])

            content = output.read_text(encoding="utf-8")
            self.assertIn("#define CONST const __code", content)
            self.assertIn("#if defined(__SDCC)", content)
            self.assertIn("#define PAN_ID0 PANIDL", content)
            self.assertIn("#define SHORT_ADDR0 SHORTADDRL", content)
            self.assertIn("#define EXT_ADDR0 IEEE_ADDR", content)
            self.assertIn("__at(0x6163) SRCRESINDEX", content)
            self.assertIn("#define X_T3CCTL0 XREG(0x70CC)", content)
            self.assertIn("#define P_INFOPAGE 0x7800", content)


if __name__ == "__main__":
    unittest.main()
