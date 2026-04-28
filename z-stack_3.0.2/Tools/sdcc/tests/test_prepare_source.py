import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prepare_source import (
    ZCL_SAMPLEAPPS_UI_NEW,
    prepare_cc2530_zcl_sampleapps_ui_header,
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


if __name__ == "__main__":
    unittest.main()
