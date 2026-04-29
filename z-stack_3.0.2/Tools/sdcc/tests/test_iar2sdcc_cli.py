import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from iar2sdcc.cli import (
    _choose_owner_module,
    _known_defined_symbols_from_prelink,
    _merge_module_plan_entry,
)


class Iar2SdccCliHelpersTest(unittest.TestCase):
    def test_known_defined_symbols_from_prelink_reads_symbol_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "prelink.json"
            payload_path.write_text(
                json.dumps({"defined_symbols": ["_foo", "_bar", "_foo"]}),
                encoding="utf-8",
            )

            symbols = _known_defined_symbols_from_prelink(payload_path)

            self.assertEqual(symbols, {"_foo", "_bar"})

    def test_merge_module_plan_entry_updates_existing_and_new_modules(self) -> None:
        module_plan = {
            "/tmp/libA.lib": [
                {"module": "Aps", "symbol_count": 1, "symbols": ["_APS_Init"]},
            ]
        }

        changed = _merge_module_plan_entry(module_plan, "/tmp/libA.lib", "Aps", "_APSME_Bind")
        self.assertTrue(changed)
        self.assertEqual(module_plan["/tmp/libA.lib"][0]["symbol_count"], 2)
        self.assertEqual(module_plan["/tmp/libA.lib"][0]["symbols"], ["_APSME_Bind", "_APS_Init"])

        changed = _merge_module_plan_entry(module_plan, "/tmp/libB.lib", "Nwk", "_nwk_init")
        self.assertTrue(changed)
        self.assertEqual(module_plan["/tmp/libB.lib"][0]["module"], "Nwk")

    def test_choose_owner_module_prefers_already_selected_library(self) -> None:
        owner_map = {
            "_APSDE_DataReq": {
                "/tmp/Router-Pro.lib": ["Aps"],
                "/tmp/Special.lib": ["AltAps"],
            }
        }

        owner = _choose_owner_module(
            "_APSDE_DataReq",
            owner_map,
            selected_libraries={"/tmp/Special.lib"},
        )

        self.assertEqual(owner, ("/tmp/Special.lib", "AltAps"))


if __name__ == "__main__":
    unittest.main()
