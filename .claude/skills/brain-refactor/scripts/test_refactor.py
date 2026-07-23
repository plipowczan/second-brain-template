import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import refactor  # noqa: E402


def write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class TestRewriteText(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(refactor.rewrite_text("see [[Old]] here", "Old", "New"), "see [[New]] here")

    def test_alias_preserved(self):
        self.assertEqual(refactor.rewrite_text("[[Old|label]]", "Old", "New"), "[[New|label]]")

    def test_heading_preserved(self):
        self.assertEqual(refactor.rewrite_text("[[Old#sec]]", "Old", "New"), "[[New#sec]]")

    def test_path_form(self):
        self.assertEqual(refactor.rewrite_text("[[FOLDER/Old]]", "Old", "New"), "[[FOLDER/New]]")

    def test_unrelated_untouched(self):
        self.assertEqual(refactor.rewrite_text("[[Other]]", "Old", "New"), "[[Other]]")


class TestRename(unittest.TestCase):
    def _vault(self, d):
        root = Path(d) / "content"
        write(root / "A" / "Old.md", '---\ntitle: "Old"\n---\n# Old\nbody\n')
        write(root / "A" / "Ref.md", 'links [[Old]] and [[Old|alias]] and [[A/Old#h]]\n')
        return str(root)

    def test_rename_moves_file_and_rewrites(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._vault(d)
            res = refactor.rename("Old", "New", root=root)
            self.assertFalse((Path(root) / "A" / "Old.md").exists())
            self.assertTrue((Path(root) / "A" / "New.md").exists())
            ref = (Path(root) / "A" / "Ref.md").read_text(encoding="utf-8")
            self.assertIn("[[New]]", ref)
            self.assertIn("[[New|alias]]", ref)
            self.assertIn("[[A/New#h]]", ref)
            self.assertNotIn("[[Old", ref)
            moved = (Path(root) / "A" / "New.md").read_text(encoding="utf-8")
            self.assertIn('title: "New"', moved)

    def test_missing_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._vault(d)
            with self.assertRaises(refactor.RefactorError):
                refactor.rename("Nope", "X", root=root)

    def test_target_exists_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._vault(d)
            write(Path(root) / "A" / "New.md", "x")
            with self.assertRaises(refactor.RefactorError):
                refactor.rename("Old", "New", root=root)


class TestRelink(unittest.TestCase):
    def test_relink_rewrites_without_renaming(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "content"
            write(root / "A" / "Ref.md", "see [[B]] twice [[B]]\n")
            res = refactor.relink("B", "A", root=str(root))
            ref = (root / "A" / "Ref.md").read_text(encoding="utf-8")
            self.assertEqual(ref.count("[[A]]"), 2)
            self.assertNotIn("[[B]]", ref)


if __name__ == "__main__":
    unittest.main()
