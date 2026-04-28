import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gen_native_cmake_plan import generate_native_plan


class GenNativeCmakePlanTest(unittest.TestCase):
    def test_generates_entry_files_and_object_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "bundle"
            obj_dir = temp_root / "obj"
            entries_dir = temp_root / "entries"
            source_root = workspace_root / "src"
            compile_source = source_root / "Components" / "foo.c"
            compile_source.parent.mkdir(parents=True, exist_ok=True)
            compile_source.write_text("void foo(void) {}\n", encoding="utf-8")

            compile_plan = [
                {
                    "source": str(compile_source),
                    "compile_source": str(compile_source),
                    "skip": False,
                },
                {
                    "source": str(source_root / "Components" / "bar.c"),
                    "compile_source": str(source_root / "Components" / "bar.c"),
                    "skip": True,
                },
            ]

            entries, skipped = generate_native_plan(
                compile_plan,
                workspace_root=workspace_root,
                obj_dir=obj_dir,
                entries_dir=entries_dir,
            )

            self.assertEqual(len(entries), 1)
            self.assertEqual(skipped, [str(source_root / "Components" / "bar.c")])
            self.assertEqual(
                entries[0]["object_file"],
                str(obj_dir / "src" / "Components" / "foo.rel"),
            )
            self.assertTrue(Path(entries[0]["entry_file"]).is_file())


if __name__ == "__main__":
    unittest.main()
