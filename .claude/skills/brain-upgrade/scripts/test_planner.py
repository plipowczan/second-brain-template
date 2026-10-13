#!/usr/bin/env python3
"""Unit tests for planner.py: the dry run of a stamped upgrade. One test per scenario of
the template-upgrade spec. Run: python -m unittest -v"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import fixtures as fx
import kbtemplate as kt
import planner
import sources

V2 = fx.template("0.2.0")


def make_instance(root: Path, files=None, git=True, values=None) -> Path:
    fx.write_tree(root, files or V2)
    if git:
        fx.git_init(root)
        fx.git(root, "add", "-A")
        fx.git(root, "commit", "-q", "-m", "clone")
    fx.onboard(root, values, git_repo=git)
    return root


class PlannerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()
        self.base = make_instance(self.tmp.path / "kb")
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, version="0.3.0", changes=None) -> sources.Source:
        self.n += 1
        root = fx.write_tree(self.tmp.path / f"src{self.n}", fx.template(version, changes))
        return sources.resolve(str(root))

    def plan(self, version="0.3.0", changes=None, **kw):
        return planner.plan_upgrade(self.base, self.source(version, changes), **kw)

    def edit(self, path, text):
        target = self.base / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        fx.git(self.base, "add", "-A")
        fx.git(self.base, "commit", "-q", "-m", f"edit {path}")

    @staticmethod
    def by_path(plan):
        return {a["path"]: a for a in plan["actions"]}


class ThreeWayTest(PlannerCase):
    def test_pristine_file_changed_upstream_is_updated(self):
        a = self.by_path(self.plan(changes={".claude/hooks/hook.py": "print('hook v2')\n"}))
        self.assertEqual((a[".claude/hooks/hook.py"]["kind"], a[".claude/hooks/hook.py"]["selected"]),
                         ("update", True))

    def test_local_edit_upstream_unchanged_is_kept_without_question(self):
        self.edit("schema.yml", "types: [note, mine]\n")
        p = self.plan()
        a = self.by_path(p)["schema.yml"]
        self.assertEqual((a["kind"], a["selected"], a["choice"]), ("keep", None, None))
        self.assertEqual(p["stamp"]["files"]["schema.yml"], kt.content_hash(b"types: [note]\n"))

    def test_both_changed_is_a_conflict(self):
        self.edit(".claude/skills/demo/SKILL.md", "mine\n")
        a = self.by_path(self.plan(changes={".claude/skills/demo/SKILL.md": "theirs\n"}))
        self.assertEqual(a[".claude/skills/demo/SKILL.md"]["kind"], "conflict")
        self.assertIsNone(a[".claude/skills/demo/SKILL.md"]["choice"])

    def test_new_template_file_is_added(self):
        a = self.by_path(self.plan(changes={".claude/skills/new/SKILL.md": "new\n"}))
        self.assertEqual((a[".claude/skills/new/SKILL.md"]["kind"],
                          a[".claude/skills/new/SKILL.md"]["selected"]), ("add", True))

    def test_new_template_file_colliding_with_an_instance_file_is_a_conflict(self):
        self.edit(".claude/skills/new/SKILL.md", "my own\n")
        a = self.by_path(self.plan(changes={".claude/skills/new/SKILL.md": "new\n"}))
        self.assertEqual(a[".claude/skills/new/SKILL.md"]["kind"], "conflict")

    def test_owner_deleted_file_stays_deleted_unless_restored(self):
        (self.base / ".claude/hooks/hook.py").unlink()
        a = self.by_path(self.plan(changes={".claude/hooks/hook.py": "print('hook v2')\n"}))
        self.assertEqual((a[".claude/hooks/hook.py"]["kind"], a[".claude/hooks/hook.py"]["selected"]),
                         ("restore", False))

    def test_unchanged_files_need_nothing(self):
        p = self.plan()  # only the version number and the changelog move
        self.assertEqual([(a["path"], a["kind"]) for a in p["actions"]],
                         [(".kb-manifest.json", "update"), ("CHANGELOG.md", "update")])
        self.assertGreater(p["info"]["uptodate"], 5)

    def test_crlf_checkout_counts_as_unmodified(self):
        hook = self.base / ".claude/hooks/hook.py"
        hook.write_bytes(hook.read_bytes().replace(b"\n", b"\r\n"))
        self.assertNotIn(".claude/hooks/hook.py", self.by_path(self.plan()))

    def test_instance_only_skill_is_never_claimed(self):
        self.edit(".claude/skills/my-skill/SKILL.md", "mine\n")
        (self.base / ".claude/settings.local.json").write_text("{}\n", encoding="utf-8")
        p = self.plan(changes={".claude/skills/demo/SKILL.md": "v3\n"})
        paths = {a["path"] for a in p["actions"]}
        self.assertNotIn(".claude/skills/my-skill/SKILL.md", paths)
        self.assertNotIn(".claude/settings.local.json", paths)
        self.assertNotIn(".claude/skills/my-skill/SKILL.md", p["stamp"]["files"])


class RemovedTest(PlannerCase):
    def test_renamed_skill_directory(self):
        changes = {".claude/skills/demo/SKILL.md": None, ".claude/skills/demo/scripts/tool.py": None,
                   ".claude/skills/brain-demo/SKILL.md": "---\nname: brain-demo\n---\n",
                   ".claude/skills/brain-demo/scripts/tool.py": "print('tool v1')\n"}
        a = self.by_path(self.plan(changes=changes))
        for p in (".claude/skills/brain-demo/SKILL.md", ".claude/skills/brain-demo/scripts/tool.py"):
            self.assertEqual((a[p]["kind"], a[p]["selected"]), ("add", True))
        for p in (".claude/skills/demo/SKILL.md", ".claude/skills/demo/scripts/tool.py"):
            self.assertEqual((a[p]["kind"], a[p]["selected"]), ("delete", True))

    def test_edited_file_the_template_removed(self):
        self.edit(".claude/hooks/hook.py", "print('my hook')\n")
        a = self.by_path(self.plan(changes={".claude/hooks/hook.py": None}))[".claude/hooks/hook.py"]
        self.assertEqual((a["kind"], a["selected"]), ("delete", False))
        self.assertIn("edited", a["warning"])

    def test_already_gone(self):
        (self.base / ".claude/hooks/hook.py").unlink()
        p = self.plan(changes={".claude/hooks/hook.py": None})
        self.assertNotIn(".claude/hooks/hook.py", self.by_path(p))
        self.assertNotIn(".claude/hooks/hook.py", p["stamp"]["files"])


class RenderedTest(PlannerCase):
    NEW_AGENTS = "# {{KB_NAME}}\n\nOwner: {{KB_OWNER}}\n\nNew section.\n"

    def rendered(self, plan):
        return {e["path"]: e for e in plan["rendered"]}

    def test_untouched_and_requested(self):
        e = self.rendered(self.plan(changes={"AGENTS.template.md": self.NEW_AGENTS},
                                    rerender=True))["AGENTS.md"]
        self.assertEqual((e["status"], e["writable"], e["requested"], e["template_changed"]),
                         ("writable", True, True, True))

    def test_not_requested_only_reports(self):
        p = self.plan(changes={"AGENTS.template.md": self.NEW_AGENTS})
        e = self.rendered(p)["AGENTS.md"]
        self.assertEqual((e["requested"], e["template_changed"]), (False, True))
        self.assertIn("re-render on request", planner.summary(p))

    def test_hand_edited_is_a_proposal(self):
        self.edit("AGENTS.md", "# Test KB\n\nmy notes\n")
        e = self.rendered(self.plan(changes={"AGENTS.template.md": self.NEW_AGENTS},
                                    rerender=True))["AGENTS.md"]
        self.assertEqual((e["status"], e["writable"]), ("edited", False))

    def test_new_placeholder_is_a_question(self):
        p = self.plan(changes={"AGENTS.template.md": "# {{KB_NAME}}\n{{NEW_KEY}}\n"})
        e = self.rendered(p)["AGENTS.md"]
        self.assertEqual((e["status"], e["missing"]), ("missing-values", ["NEW_KEY"]))
        self.assertEqual(p["questions"], [{"path": "AGENTS.md", "missing": ["NEW_KEY"]}])

    def test_missing_render_inputs(self):
        (self.base / kt.ONBOARD_VALUES).unlink()
        p = self.plan(changes={"AGENTS.template.md": self.NEW_AGENTS}, rerender=True)
        self.assertEqual({e["status"] for e in p["rendered"]}, {"no-values"})

    def test_unchanged_template_is_current(self):
        self.assertEqual({e["status"] for e in self.plan()["rendered"]}, {"current"})


class SeededAndAuthorTest(PlannerCase):
    def test_seeded_changes_are_information_only(self):
        p = self.plan(changes={"README.md": "# New product page\n",
                               "content/templates/book.md": "# {{title}} v2\n",
                               "content/REFERENCE/New.md": "# New\n"})
        paths = {a["path"] for a in p["actions"]} | {q["path"] for q in p["questions"]}
        self.assertFalse(any(x == "README.md" or x.startswith("content/") for x in paths), paths)
        self.assertEqual({(s["path"], s["change"]) for s in p["info"]["seeded"]}, {
            ("README.md", "changed upstream"),
            ("content/templates/book.md", "changed upstream"),
            ("content/REFERENCE/New.md", "added upstream")})

    def test_pristine_author_leftover_is_proposed_for_deletion(self):
        self.edit("CONTRIBUTING.md", "# Contributing to the template\n")
        a = self.by_path(self.plan())["CONTRIBUTING.md"]
        self.assertEqual((a["kind"], a["selected"]), ("author-delete", True))

    def test_own_author_path_is_left_alone(self):
        self.edit("CONTRIBUTING.md", "# How to contribute to my base\n")
        p = self.plan()
        self.assertNotIn("CONTRIBUTING.md", self.by_path(p))
        self.assertEqual(p["info"]["author_kept"], ["CONTRIBUTING.md"])

    def test_author_files_never_copied(self):
        p = self.plan()
        self.assertFalse(any(x.startswith("openspec/") or x == "CONTRIBUTING.md"
                             for x in p["stamp"]["files"]))


class PlanCommandTest(PlannerCase):
    def run_plan(self, *extra, source=None):
        src = source or fx.write_tree(self.tmp.path / "srcdir", fx.template("0.3.0", {
            ".claude/hooks/hook.py": "print('hook v2')\n"}))
        return fx.run("plan", "--instance", str(self.base), "--source", str(src),
                      "--out", str(self.tmp.path / "plan.json"), *extra)

    def test_plan_changes_nothing(self):
        before = fx.tree_hashes(self.base)
        code, out, err = self.run_plan("--diff", "all")
        self.assertEqual(code, 0, err)
        self.assertEqual(fx.tree_hashes(self.base), before)

    def test_plan_file_and_summary(self):
        code, out, err = self.run_plan("--diff", ".claude/hooks/hook.py")
        plan = json.loads((self.tmp.path / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual((plan["mode"], plan["from_version"], plan["to_version"]),
                         ("upgrade", "0.2.0", "0.3.0"))
        self.assertTrue((Path(plan["payload"]) / "src/.claude/hooks/hook.py").is_file())
        self.assertIn("Upgrade: 0.2.0 -> 0.3.0", out)
        self.assertIn("!! BREAKING", out)
        self.assertIn("+print('hook v2')", out)
        self.assertIn("Plan: ", out)

    def test_default_plan_location_is_the_temp_dir(self):
        src = fx.write_tree(self.tmp.path / "s", fx.template("0.3.0"))
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source", str(src))
        path = Path(out.strip().splitlines()[-2].split("Plan: ", 1)[1])
        try:
            self.assertEqual(path.parent.parent, Path(tempfile.gettempdir()).resolve())
            self.assertTrue(path.parent.name.startswith("kb-upgrade-"))
        finally:
            shutil.rmtree(path.parent, ignore_errors=True)

    def test_up_to_date(self):
        src = fx.write_tree(self.tmp.path / "same", V2)
        code, out, err = self.run_plan(source=src)
        self.assertEqual(code, 0, err)
        self.assertIn("Up to date", out)

    def test_older_source_refused(self):
        before = fx.tree_hashes(self.base)
        src = fx.write_tree(self.tmp.path / "old", fx.template("0.1.0"))
        code, out, err = self.run_plan(source=src)
        self.assertEqual(code, 1)
        self.assertIn("downgrades are not supported", err)
        self.assertEqual(fx.tree_hashes(self.base), before)

    def test_without_stamp_suggests_adopt(self):
        (self.base / kt.STAMP).unlink()
        code, out, err = self.run_plan()
        self.assertEqual(code, 1)
        self.assertIn("--adopt", err)

    def test_warnings(self):
        fx.git(self.base, "rm", "-q", "--cached", kt.ONBOARD_VALUES)
        fx.git(self.base, "commit", "-q", "-m", "untrack values")
        (self.base / ".claude/hooks/hook.py").write_text("print('hook v1')\n# wip\n", encoding="utf-8")
        tpl = self.tmp.path / "tplrepo"
        fx.git_init(tpl)
        fx.commit_tree(tpl, fx.template("0.3.0", {".claude/hooks/hook.py": "print('hook v2')\n"}), "x")
        code, out, err = self.run_plan(source=tpl)
        self.assertEqual(code, 0, err)
        self.assertIn("not a release", out)
        self.assertIn(f"{kt.ONBOARD_VALUES} is not tracked", out)
        self.assertIn("uncommitted changes in planned paths", out)


if __name__ == "__main__":
    unittest.main()
