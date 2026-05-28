import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prepare_source import (
    BINDING_ADD_ENTRY_CB_OLD,
    BDB_FINDING_BINDING_DSTADDR_NEW,
    BDB_REPORTING_SEARCH_CALL_NEW,
    BDB_REPORTING_SEARCH_CMP_NEW,
    BDB_REPORTING_SEARCH_DEF_NEW,
    BDB_REPORTING_SEARCH_PROTO_OLD,
    HAL_MCU_BLOCK_OLD_VENDOR,
    OSAL_NV_BUF_OLD,
    OSAL_NV_GLOBALS_OLD,
    HAL_TYPES_BLOCK_OLD,
    ONBOARD_H_OLD,
    ONBOARD_H_NEW,
    ONBOARD_INCLUDES_OLD,
    ONBOARD_INCLUDES_NEW,
    ONBOARD_STACK_BLOCK_OLD,
    ONBOARD_STACK_BLOCK_NEW,
    ZCL_SAMPLEAPPS_UI_NEW,
    prepare_cc2530_hal_sleep,
    prepare_cc2530_bdb_finding_binding,
    prepare_cc2530_bdb_reporting,
    prepare_cc2530_osal_nv,
    prepare_cc2530_hal_mcu_header,
    prepare_cc2530_hal_types_header,
    prepare_cc2530_binding_table_header,
    prepare_cc2530_mt_af,
    prepare_cc2530_onboard_header,
    prepare_cc2530_zcl_sampleapps_ui_header,
    prepare_cc2530_onboard,
    ONBOARD_GLOBALS_OLD,
    ONBOARD_LOCKBITS_OLD,
    ONBOARD_NVIEEE_OLD,
    ONBOARD_RESERVED_OLD,
    ONBOARD_STACK_USED_OLD,
)


class PrepareSourceTest(unittest.TestCase):
    def test_zcl_sampleapps_ui_prepare_is_idempotent_for_already_prepared_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "zcl_sampleapps_ui.h"
            dst = temp_root / "out.h"
            src.write_text(
                "\n".join(
                    [
                        "#ifndef ZCL_SAMPLEAPPS_UI_H",
                        ZCL_SAMPLEAPPS_UI_NEW,
                        "#endif",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            prepare_cc2530_zcl_sampleapps_ui_header(src, dst)

            self.assertEqual(dst.read_text(encoding="utf-8"), src.read_text(encoding="utf-8"))

    def test_hal_mcu_header_uses_sdcc_mcs51_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "hal_mcu.h"
            dst = temp_root / "out.h"
            src.write_text(HAL_MCU_BLOCK_OLD_VENDOR, encoding="utf-8")

            prepare_cc2530_hal_mcu_header(src, dst)

            content = dst.read_text(encoding="utf-8")
            self.assertIn("#elif defined __SDCC", content)
            self.assertIn("#define HAL_COMPILER_SDCC", content)

    def test_hal_types_header_uses_sdcc_mcs51_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "hal_types.h"
            dst = temp_root / "out.h"
            src.write_text(HAL_TYPES_BLOCK_OLD, encoding="utf-8")

            prepare_cc2530_hal_types_header(src, dst)

            content = dst.read_text(encoding="utf-8")
            self.assertIn("#elif defined __SDCC", content)
            self.assertIn("#define ASM_NOP __asm NOP __endasm", content)

    def test_hal_sleep_prepare_keeps_plain_function_body(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "hal_sleep.c"
            dst = temp_root / "out.c"
            src.write_text(
                "void halSetSleepMode(void)\n"
                "{\n"
                "  PCON = halSleepPconValue;\n"
                "  HAL_DISABLE_INTERRUPTS();\n"
                "}\n"
                "#pragma optimize=none\n",
                encoding="utf-8",
            )

            prepare_cc2530_hal_sleep(src, dst)

            content = dst.read_text(encoding="utf-8")
            self.assertIn("void halSetSleepMode(void)", content)
            self.assertNotIn("#if defined(__SDCC)", content)
            self.assertIn("#if !defined(__SDCC)\n#pragma optimize=none\n#endif", content)

    def test_hal_sleep_prepare_preserves_sleep_code_guard_for_non_sdcc(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "hal_sleep.c"
            dst = temp_root / "out.c"
            src.write_text(
                "#if !defined(__SDCC)\n"
                "#pragma location = \"SLEEP_CODE\"\n"
                "#endif\n"
                "void halSetSleepMode(void)\n"
                "{\n"
                "  PCON = halSleepPconValue;\n"
                "  HAL_DISABLE_INTERRUPTS();\n"
                "}\n"
                "#pragma optimize=none\n",
                encoding="utf-8",
            )

            prepare_cc2530_hal_sleep(src, dst)

            content = dst.read_text(encoding="utf-8")
            self.assertIn('#if !defined(__SDCC)\n#pragma location = "SLEEP_CODE"\n#endif', content)
            self.assertIn("void halSetSleepMode(void)", content)

    def test_onboard_header_uses_sdcc_mcs51_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "OnBoard.h"
            dst = temp_root / "out.h"
            src.write_text(
                "\n".join(
                    [
                        ONBOARD_INCLUDES_OLD,
                        ONBOARD_STACK_BLOCK_OLD,
                        ONBOARD_H_OLD,
                    ]
                ),
                encoding="utf-8",
            )

            prepare_cc2530_onboard_header(src, dst)

            content = dst.read_text(encoding="utf-8")
            self.assertIn("#elif defined __SDCC", content)
            self.assertIn("extern void Onboard_soft_reset( void ) __nonbanked;", content)
            self.assertIn("SDCC uses an XDATA stack layout that is not meaningfully introspectable here.", content)

    def test_onboard_header_prepare_is_idempotent_for_defined_sdcc_variant(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "OnBoard.h"
            dst = temp_root / "out.h"
            src.write_text(
                "\n".join(
                    [
                        ONBOARD_INCLUDES_NEW,
                        ONBOARD_STACK_BLOCK_NEW.replace("#elif defined __SDCC", "#elif defined(__SDCC)"),
                        ONBOARD_H_NEW,
                    ]
                ),
                encoding="utf-8",
            )

            prepare_cc2530_onboard_header(src, dst)

            self.assertEqual(dst.read_text(encoding="utf-8"), src.read_text(encoding="utf-8"))

    def test_osal_nv_prepare_keeps_sdcc_reservation_policy_comment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "OSAL_Nv.c"
            dst = temp_root / "out.c"
            src.write_text(
                "\n".join(
                    [
                        OSAL_NV_GLOBALS_OLD,
                        OSAL_NV_BUF_OLD,
                    ]
                ),
                encoding="utf-8",
            )

            prepare_cc2530_osal_nv(src, dst)

            content = dst.read_text(encoding="utf-8")
            self.assertIn("SDCC profiles rely on the linker script to reserve NV pages.", content)
            self.assertNotIn("const __code __at", content)

    def test_mt_af_prepare_is_idempotent_for_already_prepared_dstaddr_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "MT_AF.c"
            dst = temp_root / "out.c"
            src.write_text(
                "\n".join(
                    [
                        "void demo(void)",
                        "{",
                        "  pMtAfDataReq->dstAddr = dstAddr;",
                        "}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            prepare_cc2530_mt_af(src, dst)

            self.assertEqual(dst.read_text(encoding="utf-8"), src.read_text(encoding="utf-8"))

    def test_sdcc_prepared_source_does_not_emit_flash_bytes_for_reservations(self):
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            src = temp_root / "OnBoard.c"
            dst = temp_root / "out.c"
            src.write_text(
                ONBOARD_GLOBALS_OLD
                + ONBOARD_LOCKBITS_OLD
                + ONBOARD_NVIEEE_OLD
                + ONBOARD_RESERVED_OLD
                + ONBOARD_STACK_USED_OLD,
                encoding="utf-8",
            )

            prepare_cc2530_onboard(src, dst)

            content = dst.read_text(encoding="utf-8")
            # Ensure SDCC absolute placement is NOT there
            self.assertNotIn("const __code __at", content)
            # Ensure IAR block IS there
            self.assertIn("#pragma location=\"LOCK_BITS_ADDRESS_SPACE\"", content)
            self.assertIn("#pragma location=\"IEEE_ADDRESS_SPACE\"", content)
            self.assertIn("#pragma location=\"RESERVED_ADDRESS_SPACE\"", content)

    def test_bdb_finding_binding_keeps_binding_indirection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "bdb_FindingAndBinding.c"
            dst = temp_root / "out.c"
            src.write_text(
                "\n".join(
                    [
                        "  zAddrType_t dstAddr = { 0 };",
                        "  if ( pbindAddEntry )",
                        "  {",
                        "    if (!pbindAddEntry( SrcEndpInt, DstAddr, DstEndpInt,",
                        "                           1, &BindClusterId ) )",
                        "    {",
                        "      return ( ZApsTableFull );",
                        "    }",
                        "  }",
                    ]
                ),
                encoding="utf-8",
            )

            prepare_cc2530_bdb_finding_binding(src, dst)

            content = dst.read_text(encoding="utf-8")
            self.assertIn("if (!pbindAddEntry(", content)
            self.assertNotIn("if (!bindAddEntry(", content)
            self.assertIn("osal_memset(&dstAddr, 0, sizeof(dstAddr));", content)

    def test_bdb_finding_binding_prepare_is_idempotent_for_already_prepared_dstaddr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "bdb_FindingAndBinding.c"
            dst = temp_root / "out.c"
            src.write_text(
                "\n".join(
                    [
                        "void bdb_ProcessRespondentList( void )",
                        "{",
                        BDB_FINDING_BINDING_DSTADDR_NEW,
                        "  if ( pbindAddEntry )",
                        "  {",
                        "  }",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )

            prepare_cc2530_bdb_finding_binding(src, dst)

            self.assertEqual(dst.read_text(encoding="utf-8"), src.read_text(encoding="utf-8"))

    def test_binding_table_header_prepare_rewrites_bind_add_entry_callback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "BindingTable.h"
            dst = temp_root / "out.h"
            src.write_text(BINDING_ADD_ENTRY_CB_OLD, encoding="utf-8")

            prepare_cc2530_binding_table_header(src, dst)

            content = dst.read_text(encoding="utf-8")
            self.assertIn("extern BindingEntry_t *(*pbindAddEntry)( byte srcEpInt,", content)
            self.assertNotIn("extern BindingEntry_t *bindAddEntry( byte srcEpInt,", content)

    def test_bdb_reporting_prepare_is_idempotent_for_already_prepared_searchdata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            src = temp_root / "bdb_Reporting.c"
            dst = temp_root / "out.c"
            src.write_text(
                "\n".join(
                    [
                        BDB_REPORTING_SEARCH_PROTO_OLD.replace(
                            "bdbReportAttrDefaultCfgData_t searchdata );",
                            "bdbReportAttrDefaultCfgData_t *searchdata );",
                        ),
                        BDB_REPORTING_SEARCH_DEF_NEW,
                        BDB_REPORTING_SEARCH_CMP_NEW,
                        BDB_REPORTING_SEARCH_CALL_NEW,
                    ]
                ),
                encoding="utf-8",
            )

            prepare_cc2530_bdb_reporting(src, dst)

            self.assertEqual(dst.read_text(encoding="utf-8"), src.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
