#!/usr/bin/env python3
"""Unit tests for the stamp (`upgrade.py stamp`) and the onboarding helpers.
Run: python -m unittest -v"""

import json
import unittest

import fixtures as fx
import kbtemplate as kt

FIELDS = {"format", "repository", "version", "commit", "updated", "files", "rendered"}


class StampTest(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()
        self.base = self.tmp.path / "kb"
        fx.git_init(self.base)
        self.sha = fx.commit_tree(self.base, fx.template("0.2.0"), "release")

    def tearDown(self):
        self.tmp.cleanup()

    def stamp(self):
        code, out, err = fx.run("stamp", "--instance", str(self.base))
        self.assertEqual(code, 0, err)
        return json.loads((self.base / kt.STAMP).read_text(encoding="utf-8"))

    def render_outputs(self):
        for out, body in (("AGENTS.md", "# Test KB\n"), ("CLAUDE.md", "@AGENTS.md\n"),
                          ("content/WRITING_STYLE.md", "Language: English\n")):
            (self.base / out).write_text(body, encoding="utf-8")

    def test_fields(self):
        self.render_outputs()
        s = self.stamp()
        self.assertTrue(FIELDS <= set(s), set(s))
        self.assertEqual((s["format"], s["repository"], s["version"]), (1, fx.REPO, "0.2.0"))
        self.assertRegex(s["updated"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(s["files"][".claude/hooks/hook.py"],
                         kt.content_hash(b"print('hook v1')\n"))
        self.assertIn(".kb-manifest.json", s["files"])
        self.assertNotIn("README.md", s["files"])
        self.assertNotIn("CONTRIBUTING.md", s["files"])
        self.assertIn("README.md", s["seeded"])
        self.assertEqual(s["rendered"]["AGENTS.md"], {
            "template": "AGENTS.template.md",
            "template_hash": kt.content_hash((self.base / "AGENTS.template.md").read_bytes()),
            "output_hash": kt.content_hash(b"# Test KB\n")})

    def test_commit_null_without_tag(self):
        self.assertIsNone(self.stamp()["commit"])

    def test_commit_of_the_tagged_head(self):
        fx.git(self.base, "tag", "-a", "v0.2.0", "-m", "v0.2.0")
        self.assertEqual(self.stamp()["commit"], self.sha)

    def test_tag_of_another_version_is_no_proof(self):
        fx.git(self.base, "tag", "-a", "v0.1.0", "-m", "v0.1.0")
        self.assertIsNone(self.stamp()["commit"])

    def test_without_git(self):
        plain = fx.write_tree(self.tmp.path / "plain", fx.template("0.2.0"))
        code, out, err = fx.run("stamp", "--instance", str(plain))
        self.assertEqual(code, 0, err)
        s = json.loads((plain / kt.STAMP).read_text(encoding="utf-8"))
        self.assertIsNone(s["commit"])
        self.assertIn("schema.yml", s["files"])

    def test_refuses_an_existing_stamp(self):
        self.stamp()
        code, out, err = fx.run("stamp", "--instance", str(self.base))
        self.assertEqual(code, 1)

    def test_refuses_the_template_source(self):
        (self.base / "CLAUDE.local.md").write_text("@CONTRIBUTING.md\n", encoding="utf-8")
        for cmd in ("stamp", "prune-author"):
            code, out, err = fx.run(cmd, "--instance", str(self.base))
            self.assertEqual(code, 1, cmd)
            self.assertIn("template source", err)
        self.assertFalse((self.base / kt.STAMP).exists())
        self.assertTrue((self.base / "CONTRIBUTING.md").exists())

    def test_prune_author(self):
        code, out, err = fx.run("prune-author", "--instance", str(self.base))
        self.assertEqual(code, 0, err)
        self.assertFalse((self.base / "CONTRIBUTING.md").exists())
        self.assertFalse((self.base / "openspec").exists())
        self.assertTrue((self.base / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
