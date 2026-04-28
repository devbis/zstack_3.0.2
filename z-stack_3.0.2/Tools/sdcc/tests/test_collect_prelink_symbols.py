import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect_prelink_symbols import _parse_sdnm_line, main


class CollectPrelinkSymbolsTest(unittest.TestCase):
    def test_parse_sdnm_line_handles_archive_members(self) -> None:
        parsed = _parse_sdnm_line("/tmp/libfoo.lib:bar.rel:00000000 T _symbol")
        self.assertEqual(parsed, ("/tmp/libfoo.lib:bar.rel", "T", "_symbol"))

        parsed = _parse_sdnm_line("/tmp/file.rel:         U _other")
        self.assertEqual(parsed, ("/tmp/file.rel", "U", "_other"))

    def test_main_collects_only_symbols_not_provided_elsewhere(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_sdnm = root / "fake-sdnm.py"
            fake_sdnm.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import sys",
                        "if '-u' in sys.argv:",
                        "    print(f\"{sys.argv[-2]}:         U _foo\")",
                        "    print(f\"{sys.argv[-2]}:         U _bar\")",
                        "    print(f\"{sys.argv[-1]}:         U _bar\")",
                        "elif '-U' in sys.argv:",
                        "    print(f\"{sys.argv[-1]}:00000000 T _bar\")",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fake_sdnm.chmod(fake_sdnm.stat().st_mode | stat.S_IXUSR)

            consumer_a = root / "a.rel"
            consumer_b = root / "b.rel"
            provider = root / "runtime.lib"
            for path in (consumer_a, consumer_b, provider):
                path.write_text("", encoding="utf-8")

            output = root / "prelink.json"
            rc = main(
                [
                    "--sdnm",
                    str(fake_sdnm),
                    "--consumer",
                    str(consumer_a),
                    "--consumer",
                    str(consumer_b),
                    "--provider",
                    str(provider),
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(rc, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["undefined_symbols"], ["_foo"])
            self.assertEqual(payload["references"]["_foo"], [str(consumer_a.resolve())])


if __name__ == "__main__":
    unittest.main()
