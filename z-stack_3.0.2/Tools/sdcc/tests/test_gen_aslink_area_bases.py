import sys
import unittest
import tempfile
import json
from pathlib import Path

# Add the parent directory to sys.path to import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gen_aslink_area_bases import build_plan

class TestGenAslinkAreaBases(unittest.TestCase):
    def test_build_plan_resolves_required_areas_from_bank_math_xcl(self):
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            manifest_path = temp_root / "manifest.json"
            converted_manifest_path = temp_root / "converted_manifest.json"
            xcl_path = temp_root / "test.xcl"

            xcl_path.write_text(
                "\n".join(
                    [
                        "-D_CODE_START=0x2000",
                        "-D_CODE_END=0x7FFF",
                        "-D_FIRST_BANK_ADDR=0x10000",
                        "-P(CODE)BANKED_CODE=_CODE_START-_CODE_END,0x18000-0x1FFFF,0x28000-0x2FFFF,0x38000-0x3FFFF,\\",
                        "0x48000-0x4FFFF,0x58000-0x5FFFF,0x68000-0x6FFFF,0x78000-0x7FFFF",
                        "-M(CODE)[(_CODEBANK_START+_FIRST_BANK_ADDR)-(_CODEBANK_END+_FIRST_BANK_ADDR)]*\\",
                        "_NR_OF_BANKS+_FIRST_BANK_ADDR=0x8000",
                        "-D_LOCK_BITS_ADDRESS_SPACE_START=(((_NR_OF_BANKS+1)*_FIRST_BANK_ADDR)-0x10)",
                        "-D_LOCK_BITS_ADDRESS_SPACE_END=(_LOCK_BITS_ADDRESS_SPACE_START+0x0F)",
                        "-Z(CODE)LOCK_BITS_ADDRESS_SPACE=_LOCK_BITS_ADDRESS_SPACE_START-_LOCK_BITS_ADDRESS_SPACE_END",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            manifest = {
                "sdcc_required_areas": ["LOCK_BITS_ADDRESS_SPACE"],
                "source_files": [],
                "xcl_path": str(xcl_path),
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            converted_manifest = {
                "emitted_artifacts": [],
            }
            converted_manifest_path.write_text(json.dumps(converted_manifest), encoding="utf-8")

            plan = build_plan(
                manifest_path,
                converted_manifest_path,
                code_loc=0x0000,
                code_size=0x8000,
                xram_loc=0x0000,
                xram_size=0x2000,
            )

            directive = next(
                (d for d in plan["base_directives"] if d["area"] == "LOCK_BITS_ADDRESS_SPACE"),
                None,
            )
            self.assertIsNotNone(directive)
            self.assertEqual(directive["base"], 0x7FFF0)
            self.assertEqual(plan["missing_required_areas"], [])
            self.assertEqual(plan["logical_code_end"], 0x7FFFF)
            self.assertEqual(plan["logical_code_size"], 0x7FFFF - 0x2000 + 1)

    def test_build_plan_uses_native_sdcc_extra_source_areas(self):
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            manifest_path = temp_root / "manifest.json"
            converted_manifest_path = temp_root / "converted_manifest.json"
            xcl_path = temp_root / "test.xcl"
            asm_path = temp_root / "cc2530_flash_reservations.asm"

            xcl_path.write_text(
                "\n".join(
                    [
                        "-Z(CODE)LOCK_BITS_ADDRESS_SPACE=0xFFF0-0xFFFF",
                        "-Z(CODE)IEEE_ADDRESS_SPACE=0xFFE8-0xFFEF",
                        "-Z(CODE)RESERVED_ADDRESS_SPACE=0xF860-0xFFEB",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            asm_path.write_text(
                "\n".join(
                    [
                        "\t.module cc2530_flash_reservations",
                        "",
                        "\t.area LOCK_BITS_ADDRESS_SPACE (CODE)",
                        "\t.blkb 16",
                        "",
                        "\t.area IEEE_ADDRESS_SPACE (CODE)",
                        "\t.blkb 8",
                        "",
                        "\t.area RESERVED_ADDRESS_SPACE (CODE)",
                        "\t.blkb 1932",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            manifest = {
                "sdcc_required_areas": [
                    "LOCK_BITS_ADDRESS_SPACE",
                    "IEEE_ADDRESS_SPACE",
                    "RESERVED_ADDRESS_SPACE",
                ],
                "sdcc_extra_sources": [str(asm_path)],
                "source_files": [],
                "xcl_path": str(xcl_path),
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            converted_manifest = {
                "emitted_artifacts": [],
            }
            converted_manifest_path.write_text(json.dumps(converted_manifest), encoding="utf-8")

            plan = build_plan(
                manifest_path,
                converted_manifest_path,
                code_loc=0x0000,
                code_size=0x8000,
                xram_loc=0x0000,
                xram_size=0x2000,
            )

            area_names = [d["area"] for d in plan["base_directives"]]
            self.assertIn("LOCK_BITS_ADDRESS_SPACE", area_names)
            self.assertIn("IEEE_ADDRESS_SPACE", area_names)
            self.assertIn("RESERVED_ADDRESS_SPACE", area_names)
            self.assertEqual(plan["missing_required_areas"], [])

    def test_build_plan_reports_missing_required_areas(self):
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            manifest_path = temp_root / "manifest.json"
            converted_manifest_path = temp_root / "converted_manifest.json"
            xcl_path = temp_root / "test.xcl"
            
            xcl_path.write_text("-Z(CODE)REQUIRED_AREA=0x2000-0x2FFF\n", encoding="utf-8")
            
            manifest = {
                "sdcc_required_areas": ["REQUIRED_AREA", "MISSING_AREA"],
                "source_files": [],
                "xcl_path": str(xcl_path)
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            
            converted_manifest = {
                "emitted_artifacts": [],
            }
            converted_manifest_path.write_text(json.dumps(converted_manifest), encoding="utf-8")

            plan = build_plan(
                manifest_path, 
                converted_manifest_path, 
                code_loc=0x0000, 
                code_size=0x8000, 
                xram_loc=0x0000, 
                xram_size=0x2000
            )

            # We expect REQUIRED_AREA to be in base_directives and MISSING_AREA to be missing
            area_names = [d["area"] for d in plan["base_directives"]]
            self.assertIn("REQUIRED_AREA", area_names)
            self.assertNotIn("MISSING_AREA", area_names)
            
            # The plan should report missing areas
            self.assertIn("missing_required_areas", plan)
            self.assertEqual(plan["missing_required_areas"], ["MISSING_AREA"])
            
            # Check for the warning in the warnings list
            self.assertTrue(any("Missing required SDCC areas: MISSING_AREA" in w for w in plan["warnings"]))

    def test_main_exits_with_error_on_missing_areas(self):
        from gen_aslink_area_bases import main
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            manifest_path = temp_root / "manifest.json"
            converted_manifest_path = temp_root / "converted_manifest.json"
            xcl_path = temp_root / "test.xcl"
            
            xcl_path.write_text("-Z(CODE)REQUIRED_AREA=0x2000-0x2FFF\n", encoding="utf-8")
            
            manifest = {
                "sdcc_required_areas": ["REQUIRED_AREA", "MISSING_AREA"],
                "source_files": [],
                "xcl_path": str(xcl_path)
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            
            converted_manifest = {
                "emitted_artifacts": [],
            }
            converted_manifest_path.write_text(json.dumps(converted_manifest), encoding="utf-8")

            # Capture stdout to avoid clutter
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                rc = main([
                    "--manifest", str(manifest_path),
                    "--converted-manifest", str(converted_manifest_path),
                    "--code-loc", "0x0000",
                    "--code-size", "0x8000",
                    "--xram-loc", "0x0000",
                    "--xram-size", "0x2000"
                ])
            
            self.assertEqual(rc, 1)
            self.assertIn("; Missing required SDCC areas: MISSING_AREA", f.getvalue())

if __name__ == "__main__":
    unittest.main()
