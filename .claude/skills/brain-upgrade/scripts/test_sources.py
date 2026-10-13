#!/usr/bin/env python3
"""Unit tests for sources.py: directory, git, zip and download sources. No test touches
the network: downloads go through a stub opener. Run: python -m unittest -v"""

import json
import unittest
import urllib.error
from pathlib import Path

import fixtures as fx
import kbtemplate as kt
import sources


class DirSourceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_plain_directory(self):
        root = fx.write_tree(self.tmp.path / "rel", fx.template("0.2.0", {
            "graft/cache.bin": b"\0x", ".claude/settings.local.json": "{}",
            ".claude/skills/demo/scripts/__pycache__/tool.cpython-313.pyc": b"\0pyc",
            "STRAY.txt": "x"}))
        src = sources.resolve(str(root))
        self.assertEqual((src.kind, src.version, src.commit), ("dir", "0.2.0", None))
        owned = src.owned()
        for stray in ("graft/cache.bin", ".claude/settings.local.json",
                      ".claude/skills/demo/scripts/__pycache__/tool.cpython-313.pyc"):
            self.assertNotIn(stray, owned)
        ignored = src.by_class()[None]
        self.assertIn("STRAY.txt", ignored)
        self.assertIn("graft/cache.bin", ignored)

    def test_missing_manifest(self):
        root = fx.write_tree(self.tmp.path / "old", {"README.md": b"x"})
        with self.assertRaises(kt.TemplateError):
            sources.resolve(str(root))

    def test_no_such_source(self):
        with self.assertRaises(kt.TemplateError):
            sources.resolve(str(self.tmp.path / "nope"))


class GitSourceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()
        self.repo = self.tmp.path / "tpl"
        fx.git_init(self.repo)
        self.tagged = fx.commit_tree(self.repo, fx.template("0.2.0"), "release", tag="v0.2.0")

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_to_the_version_tag(self):
        fx.commit_tree(self.repo, fx.template("0.2.0", {".claude/hooks/hook.py": "print('next')\n"}),
                       "after the release")
        src = sources.resolve(str(self.repo))
        self.assertEqual((src.kind, src.ref, src.commit), ("git", "v0.2.0", self.tagged))
        self.assertTrue(src.release)
        self.assertEqual(src.files[".claude/hooks/hook.py"], b"print('hook v1')\n")
        self.assertEqual(src.warnings, [])

    def test_head_without_tag_warns(self):
        fx.commit_tree(self.repo, fx.template("0.3.0"), "bump without tag")
        src = sources.resolve(str(self.repo))
        self.assertEqual(src.ref, "HEAD")
        self.assertFalse(src.release)
        self.assertTrue(any("not a release" in w for w in src.warnings))

    def test_untracked_and_ignored_files_never_used(self):
        (self.repo / "untracked.txt").write_text("x", encoding="utf-8")
        (self.repo / ".claude/skills/demo/scripts/__pycache__").mkdir(parents=True)
        (self.repo / ".claude/skills/demo/scripts/__pycache__/t.pyc").write_bytes(b"\0")
        (self.repo / ".claude/hooks/hook.py").write_text("dirty\n", encoding="utf-8")
        src = sources.resolve(str(self.repo))
        self.assertNotIn("untracked.txt", src.files)
        self.assertNotIn(".claude/skills/demo/scripts/__pycache__/t.pyc", src.files)
        self.assertEqual(src.files[".claude/hooks/hook.py"], b"print('hook v1')\n")

    def test_export_ignore_applies(self):
        fx.commit_tree(self.repo, fx.template("0.2.0", {
            ".gitattributes": "/openspec export-ignore\n/CONTRIBUTING.md export-ignore\n"}),
            "export-ignore")
        src = sources.resolve(str(self.repo), ref="HEAD")
        self.assertNotIn("CONTRIBUTING.md", src.files)
        self.assertNotIn("openspec/config.yaml", src.files)

    def test_explicit_ref_and_to(self):
        fx.commit_tree(self.repo, fx.template("0.3.0"), "next", tag="v0.3.0")
        self.assertEqual(sources.resolve(str(self.repo), to="0.2.0").commit, self.tagged)
        self.assertEqual(sources.resolve(str(self.repo), ref="v0.2.0").version, "0.2.0")


class ZipSourceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()
        self.repo = self.tmp.path / "tpl"
        fx.git_init(self.repo)
        self.sha = fx.commit_tree(self.repo, fx.template("0.2.0"), "release", tag="v0.2.0")

    def tearDown(self):
        self.tmp.cleanup()

    def test_git_archive_zip(self):
        z = fx.zip_of(self.repo, "v0.2.0", self.tmp.path / "rel.zip")
        src = sources.resolve(str(z))
        self.assertEqual((src.kind, src.version, src.commit), ("zip", "0.2.0", self.sha))
        self.assertIn(".kb-manifest.json", src.files)  # top-level folder stripped

    def test_zip_without_comment(self):
        z = self.tmp.path / "plain.zip"
        z.write_bytes(fx.zip_bytes(fx.template("0.2.0")))
        self.assertIsNone(sources.resolve(str(z)).commit)

    def test_zip_slip_rejected(self):
        z = self.tmp.path / "bad.zip"
        z.write_bytes(fx.zip_bytes({"../evil.txt": b"x"}, prefix=""))
        with self.assertRaises(kt.TemplateError):
            sources.resolve(str(z))

    def test_materialize(self):
        z = fx.zip_of(self.repo, "v0.2.0", self.tmp.path / "rel.zip")
        out = sources.resolve(str(z)).materialize(self.tmp.path / "unpacked")
        self.assertTrue((out / ".claude/skills/demo/SKILL.md").is_file())


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()
        self.calls = []
        self.archive = fx.zip_bytes(fx.template("0.2.0"), comment="a" * 40)

    def tearDown(self):
        self.tmp.cleanup()

    def opener(self, url):
        self.calls.append(url)
        if url.endswith("/releases/latest"):
            return json.dumps({"tag_name": "v0.2.0"}).encode()
        if url.endswith("/v0.2.0.zip"):
            return self.archive
        raise urllib.error.HTTPError(url, 404, "not found", None, None)

    def test_latest_release(self):
        src = sources.resolve(None, repository=fx.REPO, opener=self.opener, dest=self.tmp.path)
        self.assertEqual(self.calls, [
            f"https://api.github.com/repos/{fx.REPO}/releases/latest",
            f"https://github.com/{fx.REPO}/archive/refs/tags/v0.2.0.zip"])
        self.assertEqual((src.kind, src.version, src.commit), ("download", "0.2.0", "a" * 40))
        self.assertEqual(Path(src.archive).read_bytes(), self.archive)
        self.assertEqual(Path(src.archive).parent, self.tmp.path)

    def test_explicit_version_skips_the_api(self):
        sources.resolve(None, to="0.2.0", repository=fx.REPO, opener=self.opener, dest=self.tmp.path)
        self.assertEqual(len(self.calls), 1)

    def test_offline(self):
        def offline(url):
            raise urllib.error.URLError("no network")
        with self.assertRaises(sources.OfflineError) as cm:
            sources.resolve(None, repository=fx.REPO, opener=offline, dest=self.tmp.path)
        self.assertIn("--source", str(cm.exception))
        self.assertEqual(list(self.tmp.path.iterdir()), [])

    def test_missing_release_is_not_offline(self):
        with self.assertRaises(kt.TemplateError) as cm:
            sources.resolve(None, to="9.9.9", repository=fx.REPO, opener=self.opener,
                            dest=self.tmp.path)
        self.assertNotIsInstance(cm.exception, sources.OfflineError)
        self.assertIn("HTTP 404", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
