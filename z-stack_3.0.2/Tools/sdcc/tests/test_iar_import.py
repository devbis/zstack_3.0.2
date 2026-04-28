import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iar_import import (
    KNOWN_ZNP_LAYOUT,
    ZNP_CONFIG_NAME,
    ZNP_RELATIVE_PROJECT,
    build_layout_metadata,
    write_project_cmake,
)


class IarImportTest(unittest.TestCase):
    def test_build_layout_metadata_applies_known_znp_defaults(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        project_file = repo_root / ZNP_RELATIVE_PROJECT
        manifest = {"xcl_file": []}
        manifest_path = repo_root / "Tools/sdcc/tests/tmp-manifest.json"

        layout = build_layout_metadata(
            manifest,
            manifest_path,
            project_file=project_file,
            config_name=ZNP_CONFIG_NAME,
            profile="balanced",
        )

        self.assertEqual(layout["project_name"], KNOWN_ZNP_LAYOUT["project_name"])
        self.assertEqual(layout["sdcc_abi"], KNOWN_ZNP_LAYOUT["sdcc_abi"])
        self.assertEqual(layout["sdcc_model"], KNOWN_ZNP_LAYOUT["sdcc_model"])
        self.assertEqual(layout["sdcc_stack_mode"], KNOWN_ZNP_LAYOUT["sdcc_stack_mode"])
        self.assertEqual(layout["validation"]["flash_limit_hex"], KNOWN_ZNP_LAYOUT["flash_limit_hex"])
        self.assertEqual(layout["profile"], "balanced")
        self.assertIsNone(layout["xcl_path"])
        self.assertEqual(layout["placements"], {})

    def test_write_project_cmake_exports_bundle_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir)
            output = bundle_root / "cmake" / "project.cmake"

            write_project_cmake(
                output,
                profile="balanced",
                project_name="CC2530ZNP-with-SBL",
                manifest_path=bundle_root / "metadata" / "manifest.json",
                layout_path=bundle_root / "layout.json",
                include_root=bundle_root / "include",
                source_root=bundle_root / "src",
                converted_lib_dir=bundle_root / "libs" / "converted",
                generated_cfg_header=bundle_root / "include" / "cfg.h",
                compile_plan_path=bundle_root / "compile-plan.json",
            )

            text = output.read_text(encoding="utf-8")
            self.assertIn('set(ZSTACK_IMPORTED_PROFILE "balanced")', text)
            self.assertIn('set(ZSTACK_IMPORTED_PROJECT_NAME "CC2530ZNP-with-SBL")', text)
            self.assertIn('set(ZSTACK_IMPORTED_SOURCE_ROOT "${ZSTACK_IMPORTED_BUNDLE_ROOT}/src")', text)
            self.assertIn('set(ZSTACK_IMPORTED_MANIFEST "${ZSTACK_IMPORTED_METADATA_DIR}/manifest.json")', text)
            self.assertIn('set(ZSTACK_IMPORTED_CONVERTED_LIB_DIR "${ZSTACK_IMPORTED_LIB_ROOT}/converted")', text)


if __name__ == "__main__":
    unittest.main()
