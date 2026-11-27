"""The operation log and the metrics file merge without a conflict (`.gitattributes`).

Run: python -m unittest test_log_merge (from this folder). Uses the `.gitattributes` of
the base this skill lives in; skipped when that file has no union rule for the log."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[4]
ATTRIBUTES = BASE / ".gitattributes"
FILES = ("content/_outputs/log.md", "content/_outputs/metrics.md")
HEADERS = {
    "content/_outputs/log.md": "# Operation log\n\n| When (UTC) | Operation | What | Notes |\n"
                               "|---|---|---|---|\n",
    "content/_outputs/metrics.md": "# Metrics\n\n| Date (UTC) | Basis | Notes |\n|---|---|---|\n",
}


def has_rules() -> bool:
    try:
        text = ATTRIBUTES.read_text(encoding="utf-8")
    except OSError:
        return False
    return all(f"{rel} merge=union" in text for rel in FILES)


def git(cwd, *args):
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}
    return subprocess.run(["git", "-c", "core.autocrlf=false", *args], cwd=cwd, env=env,
                          capture_output=True, text=True)


@unittest.skipUnless(has_rules(), ".gitattributes has no union rule for the log")
class TestUnionMerge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.assertEqual(git(self.repo, "init", "-q").returncode, 0)
        shutil.copyfile(ATTRIBUTES, self.repo / ".gitattributes")
        (self.repo / "content").mkdir()
        (self.repo / "content" / "Note.md").write_text("# Note\n", encoding="utf-8")
        self.commit("base")
        self.main = git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, message):
        git(self.repo, "add", "-A")
        r = git(self.repo, "commit", "-q", "-m", message)
        self.assertEqual(r.returncode, 0, r.stderr)

    def write(self, rel, text, append=False):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("ab" if append else "wb") as f:
            f.write(text.encode("utf-8"))

    def branch(self, name, rows, create):
        git(self.repo, "checkout", "-q", "-b", name, self.main)
        for rel in FILES:
            if create:
                self.write(rel, HEADERS[rel])
            self.write(rel, "".join(rows), append=True)
        self.commit(name)

    def merge_both(self):
        git(self.repo, "checkout", "-q", "one")
        return git(self.repo, "merge", "-q", "--no-edit", "two")

    def assert_merged(self, rows):
        for rel in FILES:
            text = (self.repo / rel).read_text(encoding="utf-8")
            self.assertEqual(text.count(HEADERS[rel].splitlines()[0]), 1, text)
            self.assertNotIn("<<<<<<<", text)
            for r in rows:
                self.assertIn(r, text)

    def test_two_branches_that_create_the_file(self):
        one = ["| 2026-11-26 10:00 | ingest | sources=1 | - |\n"]
        two = ["| 2026-11-25 09:00 | compile | created=1 | - |\n"]
        self.branch("one", one, create=True)
        self.branch("two", two, create=True)
        r = self.merge_both()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assert_merged(one + two)

    def test_two_branches_that_append(self):
        for rel in FILES:
            self.write(rel, HEADERS[rel] + "| 2026-11-20 08:00 | review | days=7 | - |\n")
        self.commit("log")
        one = ["| 2026-11-26 10:00 | ingest | sources=1 | - |\n"]
        two = ["| 2026-11-25 09:00 | compile | created=1 | - |\n",
               "| 2026-11-26 11:00 | enhance | updated=2 | - |\n"]
        self.branch("one", one, create=False)
        self.branch("two", two, create=False)
        r = self.merge_both()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assert_merged(one + two + ["| 2026-11-20 08:00 | review | days=7 | - |\n"])


if __name__ == "__main__":
    unittest.main()
