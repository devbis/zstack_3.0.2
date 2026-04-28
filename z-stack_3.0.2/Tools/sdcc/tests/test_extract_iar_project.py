import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extract_iar_project import (
    collect_manifest,
    parse_cfg_preincludes,
    parse_preinclude_extra_opts,
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


if __name__ == "__main__":
    unittest.main()
