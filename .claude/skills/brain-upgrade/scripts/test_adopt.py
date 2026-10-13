#!/usr/bin/env python3
"""Unit tests for `--adopt` (design D9) on a synthetic template history:

  P0  before 0.1.0: old skill paths, no CHANGELOG/LICENSE/.github
  P1  v0.1.0 (tag): still the old paths
  P2  between releases: skills renamed to brain-*
  P3  v0.2.0 (tag): manifest, index built in release mode

Run: python -m unittest -v"""

import json
import unittest
import urllib.error
from pathlib import Path

import fixtures as fx
import kbtemplate as kt
import planner
from fixtures import P0, P1, P2, VALUES, build_history, enc

def no_network(url):
    raise urllib.error.URLError("offline in tests")


class AdoptCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctmp = fx.TempDir()
        cls.repo = cls.ctmp.path / "template"
        cls.shas = build_history(cls.repo)
        cls.zip3 = fx.zip_of(cls.repo, "v0.2.0", cls.ctmp.path / "kb-template-0.2.0.zip")
        cls.zip1 = fx.zip_of(cls.repo, "v0.1.0", cls.ctmp.path / "kb-template-0.1.0.zip")

    @classmethod
    def tearDownClass(cls):
        cls.ctmp.cleanup()

    def setUp(self):
        self.tmp = fx.TempDir()
        self.planfile = self.tmp.path / "plan.json"

    def tearDown(self):
        self.tmp.cleanup()

    def instance(self, files, rendered=True, git=True, edits=None) -> Path:
        """An unstamped base made from a template state, onboarded the old way."""
        root = self.tmp.path / "kb"
        tree = {k: v for k, v in enc(files).items() if not k.endswith(".template.md")}
        if rendered:
            for out, tpl in fx.CLASSES["rendered"].items():
                data, _, _ = planner.render(fx.RENDER_PY, files[tpl].encode(), VALUES)
                tree[out] = data
            tree[kt.ONBOARD_VALUES] = json.dumps(VALUES).encode()
        tree.update(enc(edits or {}))
        fx.write_tree(root, tree)
        if git:
            fx.git_init(root)
            fx.git(root, "add", "-A")
            fx.git(root, "commit", "-q", "-m", "my base")
        return root

    def plan(self, base, source=None, *extra, opener=no_network):
        code, out, err = fx.run("plan", "--instance", str(base), "--source",
                                str(source or self.repo), "--out", str(self.planfile),
                                *fx.CONSENT, *extra, opener=opener)
        plan = json.loads(self.planfile.read_text(encoding="utf-8")) if code == 0 else None
        return code, out, err, plan

    def apply_commit(self, decisions=None):
        d = self.tmp.path / "decisions.json"
        d.write_text(json.dumps(decisions or {}), encoding="utf-8")
        code, out, err = fx.run("apply", "--plan", str(self.planfile), "--decisions", str(d))
        self.assertEqual(code, 0, err)
        code, out, err = fx.run("commit", "--plan", str(self.planfile))
        self.assertEqual(code, 0, err)

    @staticmethod
    def acts(plan):
        return {a["path"]: (a["kind"], a["selected"]) for a in plan["actions"]}


class AdoptTest(AdoptCase):
    def test_pre_release_generation_gets_0_1_0(self):
        base = self.instance(P0)
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.assertEqual(code, 0, err)
        self.assertEqual(plan["to_version"], "0.1.0")
        self.assertEqual(plan["base"]["ref"], "v0.1.0")  # read from the clone's tag
        self.assertEqual([b["version"] for b in plan["changelog"]], ["0.1.0"])
        a = self.acts(plan)
        self.assertEqual(a[".claude/skills/ingest/SKILL.md"], ("update", True))
        self.assertEqual(a[".claude/hooks/hook.py"], ("update", True))
        for added in ("LICENSE", "CHANGELOG.md", ".github/workflows/kb.yml"):
            self.assertEqual(a[added], ("add", True))
        self.assertFalse(any(k == "conflict" for k, _ in a.values()))
        self.assertIn("matches release 0.1.0 best", out)

    def test_unmodified_newer_file_is_not_rewound(self):
        base = self.instance(P1, edits={".claude/hooks/hook.py": "hook v2\n"})
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.assertEqual(plan["to_version"], "0.1.0")
        self.assertEqual(self.acts(plan)[".claude/hooks/hook.py"], ("keep", None))
        self.assertEqual(plan["stamp"]["files"][".claude/hooks/hook.py"],
                         kt.content_hash(b"hook v2\n"))

    def test_local_edit_is_kept_with_the_release_baseline(self):
        base = self.instance(P1, edits={"schema.yml": "types: [mine]\n"})
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.assertEqual(self.acts(plan)["schema.yml"], ("keep", None))
        self.assertEqual(plan["stamp"]["files"]["schema.yml"], kt.content_hash(b"types: [note]\n"))

    def test_between_releases_adopts_the_newer_release(self):
        base = self.instance(P2)
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.assertEqual(code, 0, err)
        self.assertEqual(plan["to_version"], "0.2.0")
        self.assertEqual(plan["base"]["kind"], "git")
        self.assertEqual(self.acts(plan)["CONTRIBUTING.md"], ("author-delete", True))
        self.apply_commit()
        code, out, err, plan = self.plan(base)
        self.assertEqual(code, 0, err)
        self.assertTrue(plan["up_to_date"], out)

    def test_history_index_follows_the_release(self):
        old = kt.dump_index(kt.HistoryIndex().data)
        base = self.instance(fx.P3, edits={kt.INDEX: old})
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.assertEqual(code, 0, err)
        self.assertEqual(plan["to_version"], "0.2.0")
        self.assertEqual(self.acts(plan)[kt.INDEX], ("update", True))

    def test_rendered_files(self):
        base = self.instance(P1, edits={"CLAUDE.md": "@AGENTS.md\n\nmy own line\n"})
        code, out, err, plan = self.plan(base, None, "--adopt")
        r = plan["stamp"]["rendered"]
        self.assertEqual(r["AGENTS.md"]["output_hash"],
                         kt.content_hash((base / "AGENTS.md").read_bytes()))
        self.assertIsNone(r["CLAUDE.md"]["output_hash"])
        self.apply_commit({"rerender": True})
        self.assertEqual((base / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n\nmy own line\n")

    def test_without_render_inputs_output_hashes_are_null(self):
        base = self.instance(P1)
        (base / kt.ONBOARD_VALUES).unlink()
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.assertTrue(all(e["output_hash"] is None for e in plan["stamp"]["rendered"].values()))

    def test_adopt_with_a_stamp_is_refused(self):
        base = self.instance(P1)
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.apply_commit()
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.assertEqual(code, 1)
        self.assertIn("plain upgrade", err)

    def test_rejected_adoption_writes_nothing(self):
        base = self.instance(P0)
        before = fx.tree_hashes(base)
        self.plan(base, None, "--adopt")
        d = self.tmp.path / "no.json"
        d.write_text('{"approve": false}', encoding="utf-8")
        code, out, err = fx.run("apply", "--plan", str(self.planfile), "--decisions", str(d))
        self.assertEqual(code, 0, err)
        self.assertEqual(fx.tree_hashes(base), before)
        self.assertFalse((base / kt.STAMP).exists())

    def test_adoption_then_upgrade_two_commits(self):
        base = self.instance(P0)
        start = len(fx.git(base, "log", "--format=%H").splitlines())
        self.plan(base, None, "--adopt")
        self.apply_commit()
        self.assertEqual(json.loads((base / kt.STAMP).read_text())["version"], "0.1.0")
        code, out, err, plan = self.plan(base)
        a = self.acts(plan)
        self.assertEqual(a[".claude/skills/ingest/SKILL.md"], ("delete", True))
        self.assertEqual(a[".claude/skills/onboard/scripts/render.py"], ("delete", True))
        self.assertEqual(a[".claude/skills/brain-ingest/SKILL.md"], ("add", True))
        self.apply_commit()
        log = fx.git(base, "log", "--format=%s").splitlines()
        self.assertEqual(len(log), start + 2)
        self.assertEqual(log[:2], [f"chore(template): upgrade to {fx.REPO} 0.2.0",
                                   f"chore(template): adopt {fx.REPO} 0.1.0"])
        self.assertEqual(json.loads((base / kt.STAMP).read_text())["version"], "0.2.0")
        self.assertFalse((base / ".claude/skills/ingest").exists())


class BaseContentTest(AdoptCase):
    def test_zip_source_downloads_the_older_release(self):
        base = self.instance(P0)
        calls = []

        def opener(url):
            calls.append(url)
            return self.zip1.read_bytes()
        code, out, err, plan = self.plan(base, self.zip3, "--adopt", opener=opener)
        self.assertEqual(code, 0, err)
        self.assertEqual(calls, [f"https://github.com/{fx.REPO}/archive/refs/tags/v0.1.0.zip"])
        self.assertEqual(plan["base"]["kind"], "download")
        self.assertEqual(plan["stamp"]["commit"], self.shas["P1"])

    def test_offline_without_base_stops(self):
        base = self.instance(P0)
        before = fx.tree_hashes(base)
        code, out, err, plan = self.plan(base, self.zip3, "--adopt")
        self.assertEqual(code, 1)
        self.assertIn("v0.1.0", err)
        self.assertIn("--base", err)
        self.assertEqual(fx.tree_hashes(base), before)

    def test_offline_with_base(self):
        base = self.instance(P0)
        code, out, err, plan = self.plan(base, self.zip3, "--adopt", "--base", str(self.zip1))
        self.assertEqual(code, 0, err)
        self.assertEqual(plan["base"]["kind"], "zip")
        self.assertEqual(plan["stamp"]["commit"], self.shas["P1"])

    def test_wrong_base_refused(self):
        base = self.instance(P0)
        code, out, err, plan = self.plan(base, self.zip3, "--adopt", "--base", str(self.zip3))
        self.assertEqual(code, 1)
        self.assertIn("not the release v0.1.0", err)

    def test_release_zip_is_its_own_base(self):
        base = self.instance(P2)
        code, out, err, plan = self.plan(base, self.zip3, "--adopt")
        self.assertEqual(code, 0, err)
        self.assertEqual((plan["to_version"], plan["base"]["kind"]), ("0.2.0", "zip"))

    def test_main_between_releases_is_not_the_release(self):
        fx.commit_tree(self.repo, {**{p: (self.repo / p).read_bytes() for p in
                                      fx.git(self.repo, "ls-files").splitlines()},
                                   ".claude/hooks/hook.py": b"hook v3\n"}, "after 0.2.0")
        try:
            base = self.instance(P2)
            code, out, err, plan = self.plan(base, None, "--adopt", "--ref", "HEAD")
            self.assertEqual(code, 0, err)
            self.assertEqual(plan["to_version"], "0.2.0")
            self.assertEqual(plan["base"]["ref"], "v0.2.0")
        finally:
            fx.git(self.repo, "reset", "-q", "--hard", "v0.2.0")


if __name__ == "__main__":
    unittest.main()
