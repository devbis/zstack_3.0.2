import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prepare_znp_cc2530_with_sbl import FULL_PROFILE, BALANCED_PROFILE, LEAN_PROFILE, apply_profile
from sdcc_contract import sdcc_flash_reservation_sources


class PrepareZnpCc2530WithSblTest(unittest.TestCase):
    def test_full_profile_marks_flash_windows_required(self):
        manifest = {"source_files": []}
        updated, _ = apply_profile(manifest, FULL_PROFILE)
        self.assertEqual(updated["sdcc_required_areas"], [
            "SLEEP_CODE",
            "CRC_SHDW",
            "LOCK_BITS_ADDRESS_SPACE",
            "IEEE_ADDRESS_SPACE",
            "RESERVED_ADDRESS_SPACE",
            "ZIGNV_ADDRESS_SPACE",
        ])

    def test_full_profile_adds_flash_reservation_sources(self) -> None:
        manifest = {"source_files": []}
        updated, _ = apply_profile(manifest, FULL_PROFILE)

        self.assertEqual(updated["sdcc_extra_sources"], sdcc_flash_reservation_sources(FULL_PROFILE))

    def test_full_profile_defines_firmware_sbl(self) -> None:
        manifest = {
            "source_files": [],
            "defines": ["FIRMWARE_CC2530"],
            "all_defines": ["FIRMWARE_CC2530"],
            "sdcc_cli_defines": ["FIRMWARE_CC2530"],
        }

        updated, _ = apply_profile(manifest, FULL_PROFILE)

        self.assertIn("FIRMWARE_SBL", updated["defines"])
        self.assertIn("FIRMWARE_SBL", updated["all_defines"])
        self.assertIn("FIRMWARE_SBL", updated["sdcc_cli_defines"])

    def test_full_profile_adds_norestartseqatomics_override_for_zmain(self) -> None:
        zmain = "/tmp/Projects/zstack/ZMain/TI2530ZNP/ZMain.c"
        manifest = {
            "source_files": [zmain],
        }

        updated, _ = apply_profile(manifest, FULL_PROFILE)

        self.assertEqual(
            updated["sdcc_compile_overrides"],
            [
                {
                    "source": zmain,
                    "sdcc_extra_args": ["--norestartseqatomics"],
                }
            ],
        )

    def test_full_profile_only_adds_nv_reservation_source(self) -> None:
        manifest = {"source_files": []}
        updated, _ = apply_profile(manifest, FULL_PROFILE)

        self.assertEqual(
            updated["sdcc_extra_sources"],
            [
                str(
                    (Path(__file__).resolve().parents[1] / "asm" / "cc2530_full_nv_reservation.asm").resolve()
                )
            ],
        )

    def test_non_full_profiles_do_not_add_flash_reservation_sources(self) -> None:
        for profile in (BALANCED_PROFILE, LEAN_PROFILE):
            manifest = {"source_files": []}
            updated, _ = apply_profile(manifest, profile)

            self.assertEqual(updated.get("sdcc_extra_sources", []), [])

    def test_balanced_profile_prunes_mt_features_but_keeps_reduced_af(self) -> None:
        manifest = {
            "source_files": [
                "/tmp/Components/stack/zcl/zcl_key_establish.c",
                "/tmp/Components/stack/bdb/bdb.c",
                "/tmp/Components/stack/bdb/bdb_touchlink.c",
                "/tmp/Components/stack/sapi/sapi.c",
                "/tmp/Components/mt/MT_SAPI.c",
                "/tmp/Components/mt/MT_GP.c",
                "/tmp/Components/mt/MT_APP_CONFIG.c",
                "/tmp/Components/mt/MT_AF.c",
                "/tmp/Components/osal/mcu/cc2530/OSAL_Nv.c",
                "/tmp/Projects/zstack/ZMain/TI2530ZNP/ZMain.c",
            ],
        }

        updated, extra_lines = apply_profile(manifest, BALANCED_PROFILE)

        self.assertEqual(updated["profile"], BALANCED_PROFILE)
        self.assertEqual(
            updated["source_files"],
            [
                "/tmp/Components/stack/bdb/bdb.c",
                str(Path(__file__).resolve().parents[1] / "shims" / "MT_AF_balanced.c"),
                str(Path(__file__).resolve().parents[1] / "shims" / "OSAL_Nv_volatile.c"),
                "/tmp/Projects/zstack/ZMain/TI2530ZNP/ZMain.c",
            ],
        )
        self.assertIn("#define SDCC_SKIP_FLASH_RESERVATION_SENTINELS 1", extra_lines)
        self.assertIn("#undef ZCL_KEY_ESTABLISH", extra_lines)
        self.assertIn("#undef FEATURE_SYSTEM_STATS", extra_lines)
        self.assertIn("#undef MT_APP_FUNC", extra_lines)
        self.assertIn("#undef MT_UTIL_FUNC", extra_lines)
        self.assertIn("#undef MT_SAPI_FUNC", extra_lines)
        self.assertIn("#undef MT_ZDO_MGMT", extra_lines)
        self.assertIn("#undef MT_ZDO_EXTENSIONS", extra_lines)
        self.assertIn("#undef MT_SYS_KEY_MANAGEMENT", extra_lines)
        self.assertIn("#define MT_SYS_KEY_MANAGEMENT 0", extra_lines)
        self.assertIn("#define SDCC_VOLATILE_NV_SHIM 1", extra_lines)
        self.assertEqual(
            updated["profile_notes"],
            [
                "balanced profile disables inter-PAN, touchlink, CBKE/key-establishment and SAPI paths",
                "balanced profile keeps a reduced MT AF command path, but disables MT app/util, MT ZDO management/extensions, MT key-management commands and system stats",
                "balanced profile replaces flash-backed OSAL NV with a volatile shim",
                "balanced profile constrains ZNP to coordinator-only stack build",
            ],
        )

    def test_lean_profile_prunes_optional_sources_and_marks_profile(self) -> None:
        manifest = {
            "source_files": [
                "/tmp/Components/stack/zcl/zcl_key_establish.c",
                "/tmp/Components/stack/bdb/bdb.c",
                "/tmp/Components/stack/bdb/bdb_touchlink.c",
                "/tmp/Components/mt/MT_SAPI.c",
                "/tmp/Components/mt/MT_AF.c",
                "/tmp/Components/osal/mcu/cc2530/OSAL_Nv.c",
                "/tmp/Projects/zstack/ZMain/TI2530ZNP/ZMain.c",
            ],
        }

        updated, extra_lines = apply_profile(manifest, LEAN_PROFILE)

        self.assertEqual(updated["profile"], LEAN_PROFILE)
        self.assertEqual(
            updated["source_files"],
            [
                "/tmp/Components/stack/bdb/bdb.c",
                str(Path(__file__).resolve().parents[1] / "shims" / "MT_AF_lean.c"),
                str(Path(__file__).resolve().parents[1] / "shims" / "OSAL_Nv_volatile.c"),
                "/tmp/Projects/zstack/ZMain/TI2530ZNP/ZMain.c",
            ],
        )
        self.assertIn("#define SDCC_SKIP_FLASH_RESERVATION_SENTINELS 1", extra_lines)
        self.assertIn("#undef FEATURE_SYSTEM_STATS", extra_lines)
        self.assertIn("#undef REFLECTOR", extra_lines)
        self.assertIn("#undef NV_RESTORE", extra_lines)
        self.assertIn("#undef NV_INIT", extra_lines)
        self.assertIn("#undef MT_UTIL_FUNC", extra_lines)
        self.assertIn("#undef MT_AF_FUNC", extra_lines)
        self.assertIn("#undef MT_ZDO_MGMT", extra_lines)
        self.assertIn("#undef MT_ZDO_EXTENSIONS", extra_lines)
        self.assertIn("#undef MT_SYS_KEY_MANAGEMENT", extra_lines)
        self.assertIn("#define MT_SYS_KEY_MANAGEMENT 0", extra_lines)
        self.assertIn("#undef ZSTACK_DEVICE_BUILD", extra_lines)
        self.assertIn("#define ZSTACK_DEVICE_BUILD DEVICE_BUILD_COORDINATOR", extra_lines)
        self.assertIn("#define SDCC_VOLATILE_NV_SHIM 1", extra_lines)
        self.assertEqual(
            updated["profile_notes"],
            [
                "lean profile disables optional MT/SAPI/inter-PAN/key-establishment sources",
                "lean profile constrains ZNP to coordinator-only stack build",
                "lean profile replaces MT AF callback machinery with no-op stubs",
                "lean profile replaces flash-backed OSAL NV with a volatile in-RAM shim",
            ],
        )


if __name__ == "__main__":
    unittest.main()
