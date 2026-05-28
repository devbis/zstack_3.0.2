import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gen_compile_plan import build_compile_plan


class TestGenCompilePlan(unittest.TestCase):
    def test_banked_code_model_defaults_c_sources_to_banked_code(self) -> None:
        repo_root = Path("/tmp/work/src")
        manifest = {
            "repo_root": str(repo_root),
            "code_model_state": ["2"],
            "source_files": [
                str(repo_root / "Components" / "stack" / "zcl" / "zcl.c"),
                str(repo_root / "Projects" / "zstack" / "ZMain" / "TI2530DB" / "OnBoard.c"),
                str(repo_root / "Projects" / "zstack" / "ZMain" / "TI2530DB" / "chipcon_cstartup.s51"),
            ],
            "sdcc_compile_overrides": [
                {
                    "source": str(repo_root / "Projects" / "zstack" / "ZMain" / "TI2530DB" / "OnBoard.c"),
                    "codeseg": "HOME",
                }
            ],
        }

        plan = build_compile_plan(manifest)

        self.assertEqual(plan[0]["codeseg"], "BANKED_CODE")
        self.assertEqual(plan[1]["codeseg"], "HOME")
        self.assertTrue(plan[2]["skip"])

    def test_non_banked_code_model_leaves_default_codeseg_unset(self) -> None:
        repo_root = Path("/tmp/work/src")
        manifest = {
            "repo_root": str(repo_root),
            "code_model_state": ["0"],
            "source_files": [
                str(repo_root / "Components" / "stack" / "zcl" / "zcl.c"),
            ],
            "sdcc_compile_overrides": [],
        }

        plan = build_compile_plan(manifest)

        self.assertIsNone(plan[0]["codeseg"])

    def test_compile_overrides_can_add_sdcc_extra_args(self) -> None:
        repo_root = Path("/tmp/work/src")
        zmain = repo_root / "Projects" / "zstack" / "ZMain" / "TI2530DB" / "ZMain.c"
        manifest = {
            "repo_root": str(repo_root),
            "code_model_state": ["2"],
            "source_files": [str(zmain)],
            "sdcc_compile_overrides": [
                {
                    "source": str(zmain),
                    "codeseg": "BANKED_CODE",
                    "sdcc_extra_args": ["--norestartseqatomics"],
                }
            ],
        }

        plan = build_compile_plan(manifest)

        self.assertEqual(plan[0]["sdcc_extra_args"], ["--norestartseqatomics"])


if __name__ == "__main__":
    unittest.main()
