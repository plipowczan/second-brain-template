#!/usr/bin/env python3
"""Tests for dev/check_manifest.py. Run: python -m unittest -v (from dev/)."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = HERE / "check_manifest.py"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


class CheckManifestTest(unittest.TestCase):
    HOOK = ".githooks/pre-commit"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "copy"
        # A temp copy of the tracked (and staged) tree, as working-tree content.
        files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--cached"],
                               capture_output=True, text=True, check=True).stdout.split("\0")
        for f in filter(None, files):
            src = ROOT / f
            if src.is_file():
                dst = self.repo / f
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        git(self.repo, "init", "-q")
        git(self.repo, "add", "-A")
        # A copy lost the modes, and on Windows `git add` never had them.
        git(self.repo, "update-index", "--chmod=+x", "--", self.HOOK)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.repo)],
                              capture_output=True, text=True)

    def test_copy_passes(self):
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_unclassified_root_file_named(self):
        (self.repo / "NOTES.txt").write_text("stray\n", encoding="utf-8")
        git(self.repo, "add", "NOTES.txt")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("NOTES.txt", r.stdout)

    def test_duplicated_fixed_named(self):
        cl = self.repo / "CHANGELOG.md"
        text = cl.read_text(encoding="utf-8")
        # The newest block: [Unreleased] between releases, [X.Y.Z] on a release commit.
        head = re.search(r"^## \[([^\]]+)\].*\n", text, re.MULTILINE)
        dup = "\n### Fixed\n- one\n\n### Fixed\n- two\n"
        cl.write_text(text[:head.end()] + dup + text[head.end():], encoding="utf-8")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"[{head.group(1)}] has ### Fixed more than once", r.stdout)

    def test_version_mismatch_and_package_version(self):
        man = self.repo / ".kb-manifest.json"
        man.write_text(man.read_text(encoding="utf-8").replace('"version": "', '"version": "9', 1),
                       encoding="utf-8")
        pkg = self.repo / "package.json"
        pkg.write_text(pkg.read_text(encoding="utf-8").replace('"private"', '"version": "1.0.0",\n  "private"'),
                       encoding="utf-8")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("version:", r.stdout)
        self.assertIn('package.json: remove the "version" field', r.stdout)

    def test_listed_but_not_tracked_as_executable(self):
        git(self.repo, "update-index", "--chmod=-x", "--", self.HOOK)
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"executable: {self.HOOK} is listed", r.stdout)
        self.assertIn("--chmod=+x", r.stdout)

    def test_tracked_as_executable_but_not_listed(self):
        git(self.repo, "update-index", "--chmod=+x", "--", "schema.yml")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("executable: schema.yml is tracked as executable but not listed", r.stdout)

    def test_listed_path_that_is_not_tracked(self):
        man = self.repo / ".kb-manifest.json"
        data = json.loads(man.read_text(encoding="utf-8"))
        data["executable"].append(".githooks/gone")
        man.write_text(json.dumps(data), encoding="utf-8")
        r = self.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("executable: .githooks/gone is listed", r.stdout)


if __name__ == "__main__":
    unittest.main()
