import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from object_path import compute_object_path


class ObjectPathTest(unittest.TestCase):
    def test_canonicalizes_workspace_alias_before_rebasing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            real_workspace = temp_root / "real" / "bundle"
            alias_workspace = temp_root / "bundle"
            compile_source = real_workspace / "src" / "Components" / "foo.c"
            obj_dir = temp_root / "obj"

            compile_source.parent.mkdir(parents=True, exist_ok=True)
            compile_source.write_text("void foo(void) {}\n", encoding="utf-8")
            alias_workspace.symlink_to(real_workspace, target_is_directory=True)

            self.assertEqual(
                compute_object_path(
                    compile_source=compile_source,
                    workspace_root=alias_workspace,
                    obj_dir=obj_dir,
                ),
                obj_dir / "src" / "Components" / "foo.rel",
            )

    def test_supports_alias_compile_source_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            real_workspace = temp_root / "real" / "bundle"
            alias_workspace = temp_root / "bundle"
            alias_compile_source = alias_workspace / "src" / "Components" / "bar.asm"
            obj_dir = temp_root / "obj"

            (real_workspace / "src" / "Components").mkdir(parents=True, exist_ok=True)
            (real_workspace / "src" / "Components" / "bar.asm").write_text("", encoding="utf-8")
            alias_workspace.symlink_to(real_workspace, target_is_directory=True)

            self.assertEqual(
                compute_object_path(
                    compile_source=alias_compile_source,
                    workspace_root=real_workspace,
                    obj_dir=obj_dir,
                ),
                obj_dir / "src" / "Components" / "bar.rel",
            )

    def test_external_source_gets_stable_object_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workspace_root = temp_root / "project"
            external_root = temp_root / "sdk"
            compile_source = external_root / "Components" / "foo.c"
            obj_dir = temp_root / "obj"

            workspace_root.mkdir()
            compile_source.parent.mkdir(parents=True)
            compile_source.write_text("void foo(void) {}\n", encoding="utf-8")

            object_path = compute_object_path(
                compile_source=compile_source,
                workspace_root=workspace_root,
                obj_dir=obj_dir,
            )

            self.assertEqual(object_path.name, "foo.rel")
            self.assertEqual(object_path.parent.parent, obj_dir / "external")
            self.assertEqual(len(object_path.parent.name), 12)


if __name__ == "__main__":
    unittest.main()
