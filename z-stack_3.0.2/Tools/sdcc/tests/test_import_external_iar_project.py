import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from import_external_iar_project import (
    PORTING_DOC,
    _copy_porting_doc,
    _project_service_root,
    _write_import_project_cmake,
    import_external_project,
)
from sdcc_contract import sdcc_flash_reservation_sources, sdcc_required_areas
from gen_aslink_area_bases import build_plan
from unittest.mock import MagicMock, patch


class ImportExternalIarProjectTest(unittest.TestCase):
    @patch("import_external_iar_project.collect_manifest")
    @patch("import_external_iar_project.build_compile_plan")
    @patch("import_external_iar_project.write_sdcc_header")
    @patch("import_external_iar_project._write_json")
    @patch("import_external_iar_project._write_import_project_cmake")
    @patch("import_external_iar_project._copy_porting_doc")
    def test_import_uses_profile_required_areas_even_when_manifest_omits_them(
        self,
        mock_copy_doc,
        mock_write_cmake,
        mock_write_json,
        mock_write_header,
        mock_build_plan,
        mock_collect_manifest
    ) -> None:
        mock_collect_manifest.return_value = {
            "sdcc_required_areas": [],
            "sdcc_header_defines": [],
            "source_files": [],
            "include_dirs": [],
            "iar_libraries": [],
            "sdcc_extra_sources": [],
        }
        mock_build_plan.return_value = {}

        args = MagicMock()
        args.project = Path("test.ewp")
        args.zstack_root = Path("/zstack")
        args.out_dir = Path("/out")
        args.target_name = "test"
        args.config = "debug"
        args.profile = "full"
        args.write_cmakelists = None

        import_external_project(args)

        # Check that the manifest written to JSON contains the required areas
        manifest_written = mock_write_json.call_args_list[0][0][1]
        self.assertIn("sdcc_required_areas", manifest_written)
        self.assertEqual(manifest_written["sdcc_required_areas"], sdcc_required_areas(args.profile))
        self.assertEqual(manifest_written["sdcc_extra_sources"], sdcc_flash_reservation_sources(args.profile))

    def test_area_base_generator_honors_required_areas(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            manifest_path = temp_root / "manifest.json"
            converted_manifest_path = temp_root / "converted-manifest.json"
            xcl_path = temp_root / "test.xcl"

            xcl_path.write_text("-Z(CODE)SLEEP_CODE=0x2000-0x2004\n", encoding="utf-8")
            manifest_path.write_text(
                "\n".join(
                    [
                        "{",
                        '  "sdcc_required_areas": ["SLEEP_CODE", "LOCK_BITS_ADDRESS_SPACE"],',
                        f'  "xcl_path": "{xcl_path.as_posix()}"',
                        "}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            converted_manifest_path.write_text(
                "{\n  \"emitted_artifacts\": []\n}\n",
                encoding="utf-8",
            )

            plan = build_plan(
                manifest_path,
                converted_manifest_path,
                code_loc=0x0000,
                code_size=0x8000,
                xram_loc=0x0000,
                xram_size=0x2000,
            )

            self.assertIn("SLEEP_CODE", [directive["area"] for directive in plan["base_directives"]])
            self.assertEqual(plan["missing_required_areas"], ["LOCK_BITS_ADDRESS_SPACE"])

    @patch("import_external_iar_project.collect_manifest")
    @patch("import_external_iar_project.build_compile_plan")
    @patch("import_external_iar_project.write_sdcc_header")
    @patch("import_external_iar_project._write_json")
    @patch("import_external_iar_project._write_import_project_cmake")
    @patch("import_external_iar_project._copy_porting_doc")
    def test_import_injects_sdcc_sleep_entry_source(
        self,
        mock_copy_doc,
        mock_write_cmake,
        mock_write_json,
        mock_write_header,
        mock_build_plan,
        mock_collect_manifest,
    ) -> None:
        mock_collect_manifest.return_value = {
            "sdcc_required_areas": [],
            "sdcc_header_defines": [],
            "source_files": [],
            "include_dirs": [],
            "iar_libraries": [],
            "sdcc_extra_sources": [],
        }
        mock_build_plan.return_value = []

        args = MagicMock()
        args.project = Path("test.ewp")
        args.zstack_root = Path("/zstack")
        args.out_dir = Path("/out")
        args.target_name = "test"
        args.config = "debug"
        args.profile = "full"
        args.write_cmakelists = None

        import_external_project(args)

        manifest_written = mock_write_json.call_args_list[0][0][1]
        self.assertEqual(manifest_written["sdcc_extra_sources"], sdcc_flash_reservation_sources(args.profile))

    def test_write_import_project_cmake_tracks_bundle_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bundle_root = Path(td) / ".sdcc-import" / "full"
            project_cmake = bundle_root / "cmake" / "project.cmake"
            manifest_path = bundle_root / "metadata" / "manifest.json"
            compile_plan_path = bundle_root / "compile-plan.json"
            cfg_header_path = bundle_root / "include" / "test-sdcc-cfg.h"
            source_files = [
                str(bundle_root / "src" / "foo.c"),
                str(bundle_root / "src" / "bar.c"),
            ]

            _write_import_project_cmake(
                project_cmake,
                project_name="CC2530ZNP-with-SBL",
                profile="full",
                import_root=bundle_root,
                manifest_path=manifest_path,
                compile_plan_path=compile_plan_path,
                cfg_header_path=cfg_header_path,
                source_files=source_files,
            )

            text = project_cmake.read_text(encoding="utf-8")
            self.assertIn('set(ZSTACK_IMPORTED_COMPILE_PLAN "', text)
            self.assertIn(compile_plan_path.as_posix(), text)
            self.assertIn('set(ZSTACK_IMPORTED_CONFIGURE_DEPENDS', text)
            self.assertIn(manifest_path.as_posix(), text)
            self.assertIn(cfg_header_path.as_posix(), text)
            self.assertIn(project_cmake.as_posix(), text)
            self.assertIn('set(ZSTACK_IMPORTED_SOURCE_FILES', text)
            self.assertIn(source_files[0], text)
            self.assertIn(source_files[1], text)

    def test_external_project_cmake_consumes_configure_depends_before_native_plan(self) -> None:
        cmake_text = (Path(__file__).resolve().parents[4] / "cmake" / "ZStackSDCC.cmake").read_text(encoding="utf-8")
        imported_project_idx = cmake_text.index('include("${imported_project_cmake}")')
        configure_depends_idx = cmake_text.index('if(DEFINED ZSTACK_IMPORTED_CONFIGURE_DEPENDS)')
        native_plan_idx = cmake_text.index('execute_process(', configure_depends_idx)

        self.assertLess(imported_project_idx, configure_depends_idx)
        self.assertLess(configure_depends_idx, native_plan_idx)
        self.assertIn('set_property(', cmake_text[configure_depends_idx:native_plan_idx])
        self.assertIn('PROPERTY CMAKE_CONFIGURE_DEPENDS', cmake_text[configure_depends_idx:native_plan_idx])

    def test_project_service_root_prefers_generated_cmakelists_parent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            self.assertEqual(
                _project_service_root(
                    out_dir=root / "project" / ".sdcc-import" / "full",
                    profile="full",
                    write_cmakelists=root / "project" / "CMakeLists.txt",
                ),
                (root / "project").resolve(),
            )

    def test_project_service_root_infers_standard_sidecar_layout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            self.assertEqual(
                _project_service_root(
                    out_dir=root / "project" / ".sdcc-import" / "full",
                    profile="full",
                    write_cmakelists=None,
                ),
                (root / "project").resolve(),
            )

    def test_copy_porting_doc_to_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)

            _copy_porting_doc(project_root)

            copied = project_root / "SDCC_PORTING.md"
            self.assertTrue(copied.exists())
            self.assertEqual(copied.read_text(encoding="utf-8"), PORTING_DOC.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
