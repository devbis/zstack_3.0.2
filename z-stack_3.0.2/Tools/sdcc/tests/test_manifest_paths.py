import unittest
from pathlib import Path

from manifest_paths import rebase_manifest_paths


class RebaseManifestPathsTest(unittest.TestCase):
    def test_rebases_manifest_paths_to_current_zstack_root(self) -> None:
        old_root = Path("/tmp/old-worktree/z-stack_3.0.2")
        new_root = Path("/tmp/new-worktree/z-stack_3.0.2")
        manifest = {
            "repo_root": str(old_root),
            "project_file": str(old_root / "Projects/zstack/App/Sample.ewp"),
            "project_dir": str(old_root / "Projects/zstack/App"),
            "include_dirs": [
                str(old_root / "Components/stack"),
                str(old_root / "Projects/zstack/App/Include"),
            ],
            "source_files": [
                str(old_root / "Projects/zstack/App/main.c"),
            ],
            "header_files": [
                str(old_root / "Projects/zstack/App/main.h"),
            ],
            "cfg_files": [
                str(old_root / "Projects/zstack/Tools/board.cfg"),
            ],
            "preinclude_files": [
                str(old_root / "Projects/zstack/App/preinclude.h"),
            ],
            "xcl_file": [
                str(old_root / "Projects/zstack/Tools/linker.xcl"),
            ],
            "iar_libraries": [
                str(old_root / "Projects/zstack/Libraries/libfoo.lib"),
            ],
            "all_project_files": [
                str(old_root / "Projects/zstack/App/main.c"),
                str(old_root / "Projects/zstack/App/main.h"),
            ],
            "sdcc_cli_defines": ["FEATURE_X"],
        }

        rebased = rebase_manifest_paths(manifest, new_root)

        self.assertEqual(rebased["repo_root"], str(new_root))
        self.assertEqual(
            rebased["project_file"],
            str(new_root / "Projects/zstack/App/Sample.ewp"),
        )
        self.assertEqual(
            rebased["include_dirs"][0],
            str(new_root / "Components/stack"),
        )
        self.assertEqual(
            rebased["source_files"][0],
            str(new_root / "Projects/zstack/App/main.c"),
        )
        self.assertEqual(
            rebased["preinclude_files"][0],
            str(new_root / "Projects/zstack/App/preinclude.h"),
        )
        self.assertEqual(
            rebased["iar_libraries"][0],
            str(new_root / "Projects/zstack/Libraries/libfoo.lib"),
        )
        self.assertEqual(rebased["sdcc_cli_defines"], ["FEATURE_X"])


if __name__ == "__main__":
    unittest.main()
