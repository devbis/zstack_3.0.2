import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[4] / "z-stack_3.0.2"


def _read_text(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252")


class SdccMergeRegressionTest(unittest.TestCase):
    def test_hal_sleep_has_sdcc_sleep_entry_implementation(self) -> None:
        content = _read_text(ROOT / "Components" / "hal" / "target" / "CC2530EB" / "hal_sleep.c")

        self.assertIn("void halSetSleepMode(void)\n{\n  PCON = halSleepPconValue;\n  HAL_DISABLE_INTERRUPTS();\n}\n", content)

    def test_sdcc_flash_reservation_asm_sources_exist_and_define_named_areas(self) -> None:
        asm_root = ROOT / "Tools" / "sdcc" / "asm"
        common = (asm_root / "cc2530_flash_reservations.asm").read_text(encoding="utf-8")
        full_nv = (asm_root / "cc2530_full_nv_reservation.asm").read_text(encoding="utf-8")

        self.assertIn(".area LOCK_BITS_ADDRESS_SPACE (CODE)", common)
        self.assertIn(".area IEEE_ADDRESS_SPACE (CODE)", common)
        self.assertIn(".area RESERVED_ADDRESS_SPACE (CODE)", common)
        self.assertIn(".blkb 1932", common)
        self.assertIn(".area ZIGNV_ADDRESS_SPACE (CODE)", full_nv)
        self.assertIn(".blkb 12288", full_nv)

    def test_onboard_stack_usage_is_disabled_for_sdcc(self) -> None:
        content = _read_text(ROOT / "Projects" / "zstack" / "ZMain" / "TI2530DB" / "OnBoard.c")

        self.assertIn("#if defined(__SDCC)\n  return 0;\n#else", content)
        self.assertIn("// SDCC uses an XDATA stack layout that is not meaningfully introspectable here.",
                      _read_text(ROOT / "Projects" / "zstack" / "ZMain" / "TI2530DB" / "OnBoard.h"))

    def test_osal_nv_documents_sdcc_reservation_policy(self) -> None:
        content = _read_text(ROOT / "Components" / "osal" / "mcu" / "cc2530" / "OSAL_Nv.c")

        self.assertIn("SDCC profiles rely on the linker script to reserve NV pages.", content)
        self.assertNotIn("#define SDCC_SKIP_FLASH_RESERVATION_SENTINELS", content)
        self.assertNotIn("const __code __at", content)

    def test_zcl_key_establish_uses_sdcc_safe_partner_initialization(self) -> None:
        content = _read_text(ROOT / "Components" / "stack" / "zcl" / "zcl_key_establish.c")

        self.assertIn("afAddrType_t partner;", content)
        self.assertIn("osal_memset(&partner, 0, sizeof(partner));", content)
        self.assertNotIn("afAddrType_t partner = {0};", content)


if __name__ == "__main__":
    unittest.main()
