#!/usr/bin/env python3
"""Unit tests for kbtemplate.py: hashes, manifest classes, changelog, history index.
Run: python -m unittest -v   (from this directory)."""

import json
import unittest
from pathlib import Path

import fixtures as fx
import kbtemplate as kt


class HashTest(unittest.TestCase):
    def test_crlf_and_lf_hash_alike(self):
        self.assertEqual(kt.content_hash(b"a\r\nb\r\n"), kt.content_hash(b"a\nb\n"))

    def test_hash_format(self):
        h = kt.content_hash(b"x")
        self.assertTrue(h.startswith("sha256:"))
        self.assertEqual(len(h), len("sha256:") + 64)

    def test_binary_hashed_raw(self):
        self.assertNotEqual(kt.content_hash(b"\0a\r\n"), kt.content_hash(b"\0a\n"))

    def test_lone_cr_is_content(self):
        self.assertNotEqual(kt.content_hash(b"a\rb"), kt.content_hash(b"ab"))


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.m = kt.Manifest(json.loads(fx.manifest("0.2.0")))

    def test_reads_all_fields(self):
        self.assertEqual(self.m.version, "0.2.0")
        self.assertEqual(self.m.repository, fx.REPO)
        self.assertIn("CLAUDE.md", self.m.rendered)
        self.assertTrue(self.m.exclude)

    def test_class_order_author_before_owned(self):
        # dev/** is author even though nothing else claims it; CONTRIBUTING.md too.
        self.assertEqual(self.m.classify("CONTRIBUTING.md"), "author")
        m = kt.Manifest({**json.loads(fx.manifest("0.2.0")),
                         "classes": {**fx.CLASSES, "owned": fx.CLASSES["owned"] + ["openspec/**"]}})
        self.assertEqual(m.classify("openspec/config.yaml"), "author")

    def test_rendered_before_seeded(self):
        self.assertEqual(self.m.classify("content/WRITING_STYLE.template.md"), "rendered")
        self.assertEqual(self.m.classify("content/WRITING_STYLE.md"), "rendered")
        self.assertEqual(self.m.classify("content/REFERENCE/Example.md"), "seeded")
        self.assertEqual(self.m.classify("README.md"), "seeded")

    def test_owned_globs(self):
        self.assertEqual(self.m.classify(".claude/skills/a/scripts/x.py"), "owned")
        self.assertEqual(self.m.classify("schema.yml"), "owned")

    def test_exclude_wins(self):
        for p in (".claude/skills/a/scripts/__pycache__/x.cpython-313.pyc",
                  ".claude/settings.local.json", "graft/cache.bin", ".kb-template.json"):
            self.assertIsNone(self.m.classify(p), p)
            self.assertTrue(self.m.excluded(p), p)

    def test_unclassified(self):
        self.assertIsNone(self.m.classify("NOTES.txt"))

    def test_glob_semantics(self):
        self.assertTrue(kt.glob_match("**/*.pyc", "a.pyc"))
        self.assertTrue(kt.glob_match("**/*.pyc", "x/y/a.pyc"))
        self.assertFalse(kt.glob_match("*.md", "x/a.md"))
        self.assertTrue(kt.glob_match("dev/**", "dev/a/b.py"))
        self.assertFalse(kt.glob_match("dev/**", "devx/a.py"))


class VersionTest(unittest.TestCase):
    def test_order(self):
        self.assertLess(kt.parse_version("0.2.0"), kt.parse_version("0.10.0"))
        self.assertLess(kt.parse_version("1.0.0-rc.1"), kt.parse_version("1.0.0"))
        self.assertEqual(kt.parse_version("v0.2.0"), kt.parse_version("0.2.0"))

    def test_rejects_garbage(self):
        with self.assertRaises(kt.TemplateError):
            kt.parse_version("latest")


class ChangelogTest(unittest.TestCase):
    TEXT = fx.changelog("0.3.0", "0.2.1", "0.2.0", "0.1.0", unreleased="next thing")

    def test_range_starts_after_the_stamp_version(self):
        blocks = kt.changelog_range(self.TEXT, "0.2.0", "0.3.0")
        self.assertEqual([b["version"] for b in blocks], ["Unreleased", "0.3.0", "0.2.1"])

    def test_range_stops_at_the_source_version(self):
        blocks = kt.changelog_range(fx.changelog("0.3.0", "0.2.0"), "0.1.0", "0.2.0")
        self.assertEqual([b["version"] for b in blocks], ["0.2.0"])

    def test_single_version(self):
        blocks = kt.changelog_version(self.TEXT, "0.2.0")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["version"], "0.2.0")
        self.assertEqual(blocks[0]["date"], "2026-01-01")

    def test_breaking_marked(self):
        block = kt.changelog_version(self.TEXT, "0.3.0")[0]
        flags = {s["heading"]: [e["breaking"] for e in s["entries"]] for s in block["sections"]}
        self.assertEqual(flags, {"Added": [False], "Changed": [True]})

    def test_empty_unreleased_skipped(self):
        text = "## [Unreleased]\n\n## [0.2.0] - 2026-01-01\n\n### Added\n- x\n"
        self.assertEqual([b["version"] for b in kt.changelog_range(text, "0.1.0", "0.2.0")],
                         ["0.2.0"])

    def test_entries_keep_continuation_lines(self):
        text = "## [0.2.0]\n\n### Fixed\n- **Title.** first\n  second\n\n  Existing bases: x\n- next\n"
        entries = kt.parse_changelog(text)[0]["sections"][0]["entries"]
        self.assertEqual(len(entries), 2)
        self.assertIn("Existing bases: x", entries[0]["text"])

    def test_newest_release(self):
        self.assertEqual(kt.newest_release(self.TEXT), "0.3.0")

    def test_real_changelog_parses(self):
        root = Path(__file__).resolve().parents[4]
        text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertTrue(kt.parse_changelog(text))


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()
        self.repo = self.tmp.path / "tpl"
        fx.git_init(self.repo)
        self.c1 = fx.commit_tree(self.repo, fx.template("0.1.0", {
            ".claude/skills/ingest/SKILL.md": "old ingest\n"}), "first")
        self.c2 = fx.commit_tree(self.repo, fx.template("0.1.0", {
            ".claude/skills/ingest/SKILL.md": "old ingest v2\n"}), "release", tag="v0.1.0")
        self.c3 = fx.commit_tree(self.repo, fx.template("0.1.0"), "rename")
        self.c4 = fx.commit_tree(self.repo, fx.template("0.1.0", {"README.md": "changed\n"}),
                                 "readme only")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, **kw):
        return kt.build_index(self.repo, kt.Manifest.load(self.repo), **kw)

    def test_history_and_release(self):
        idx = kt.HistoryIndex(self.build())
        old = idx.files[".claude/skills/ingest/SKILL.md"]
        self.assertIn(kt.content_hash(b"old ingest\n"), old)
        self.assertIn(kt.content_hash(b"old ingest v2\n"), old)
        self.assertEqual(idx.releases(), {"0.1.0": 1})
        self.assertEqual(idx.states[1]["commit"], self.c2)

    def test_only_owned_and_author(self):
        idx = kt.HistoryIndex(self.build())
        self.assertIn("CONTRIBUTING.md", idx.files)
        self.assertNotIn("README.md", idx.files)
        self.assertNotIn("AGENTS.template.md", idx.files)

    def test_states_without_indexed_change_collapse(self):
        idx = kt.HistoryIndex(self.build())
        self.assertEqual([s["commit"] for s in idx.states], [self.c1, self.c2, self.c3])

    def test_deterministic(self):
        self.assertEqual(kt.dump_index(self.build()), kt.dump_index(self.build()))

    def test_release_tree_labels_staged_state(self):
        fx.write_tree(self.repo, {".kb-manifest.json": fx.manifest("0.2.0").encode(),
                                  "CHANGELOG.md": fx.changelog("0.2.0", "0.1.0").encode()})
        fx.git(self.repo, "add", "-A")
        idx = kt.HistoryIndex(self.build(release_tree=True))
        self.assertEqual(idx.states[-1], {"commit": None, "date": "2026-01-01",
                                          "release": "0.2.0", "in": ["0.2.0"]})
        self.assertIn("0.2.0", idx.releases())
        self.assertEqual(idx.states[0]["in"], ["0.1.0", "0.2.0"])

    def test_release_history(self):
        idx = kt.HistoryIndex(self.build())
        self.assertTrue(idx.in_release(0, "0.1.0"))
        self.assertTrue(idx.in_release(1, "0.1.0"))
        self.assertFalse(idx.in_release(2, "0.1.0"))


if __name__ == "__main__":
    unittest.main()
