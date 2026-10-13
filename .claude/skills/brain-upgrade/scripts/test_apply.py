#!/usr/bin/env python3
"""Unit tests for `upgrade.py apply` and `upgrade.py commit`. Run: python -m unittest -v"""

import json
import unittest
from pathlib import Path

import fixtures as fx
import kbtemplate as kt
from test_planner import V2, make_instance

HOOK2 = "print('hook v2')\n"


class ApplyCase(unittest.TestCase):
    git = True

    def setUp(self):
        self.tmp = fx.TempDir()
        self.base = make_instance(self.tmp.path / "kb", git=self.git)
        self.planfile = self.tmp.path / "plan.json"

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, changes=None, *extra):
        src = fx.write_tree(self.tmp.path / f"src{len(list(self.tmp.path.iterdir()))}",
                            fx.template("0.3.0", changes))
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source", str(src),
                                "--out", str(self.planfile), *fx.CONSENT, *extra)
        self.assertEqual(code, 0, err)
        return json.loads(self.planfile.read_text(encoding="utf-8"))

    def apply(self, decisions=None):
        d = self.tmp.path / "decisions.json"
        d.write_text(json.dumps(decisions or {}), encoding="utf-8")
        return fx.run("apply", "--plan", str(self.planfile), "--decisions", str(d))

    def commit(self):
        return fx.run("commit", "--plan", str(self.planfile))

    def stamp(self):
        return json.loads((self.base / kt.STAMP).read_text(encoding="utf-8"))

    def content(self):
        return {p: h for p, h in fx.tree_hashes(self.base).items() if p.startswith("content/")}


class ApplyTest(ApplyCase):
    def test_writes_selected_actions_and_the_stamp(self):
        self.plan({".claude/hooks/hook.py": HOOK2, ".claude/skills/new/SKILL.md": "new\n"})
        code, out, err = self.apply()
        self.assertEqual(code, 0, err)
        self.assertEqual((self.base / ".claude/hooks/hook.py").read_text(encoding="utf-8"), HOOK2)
        self.assertTrue((self.base / ".claude/skills/new/SKILL.md").is_file())
        s = self.stamp()
        self.assertEqual(s["version"], "0.3.0")
        self.assertEqual(s["files"][".claude/hooks/hook.py"], kt.content_hash(HOOK2.encode()))

    def test_deselected_action_is_not_written(self):
        self.plan({".claude/skills/new/SKILL.md": "new\n"})
        code, out, err = self.apply({"actions": {".claude/skills/new/SKILL.md": False}})
        self.assertEqual(code, 0, err)
        self.assertFalse((self.base / ".claude/skills/new/SKILL.md").exists())

    def test_stale_plan_writes_nothing(self):
        self.plan({".claude/hooks/hook.py": HOOK2, "schema.yml": "types: [x]\n"})
        (self.base / "schema.yml").write_text("types: [edited after the dry run]\n", encoding="utf-8")
        before = fx.tree_hashes(self.base)
        code, out, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("changed since the dry run: schema.yml", err)
        self.assertEqual(fx.tree_hashes(self.base), before)

    def test_dirty_planned_path_is_refused(self):
        (self.base / "schema.yml").write_text("types: [wip]\n", encoding="utf-8")
        self.plan({"schema.yml": "types: [note, upstream]\n"})
        before = fx.tree_hashes(self.base)
        code, out, err = self.apply({"actions": {"schema.yml": "overwrite"}})
        self.assertEqual(code, 1)
        self.assertIn("uncommitted changes in planned paths: schema.yml", err)
        self.assertEqual(fx.tree_hashes(self.base), before)

    def test_conflict_needs_a_choice(self):
        fx.write_tree(self.base, {".claude/skills/demo/SKILL.md": b"mine\n"})
        fx.git(self.base, "commit", "-qam", "edit")
        self.plan({".claude/skills/demo/SKILL.md": "theirs\n"})
        before = fx.tree_hashes(self.base)
        code, out, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("choose keep, overwrite or merge", err)
        self.assertEqual(fx.tree_hashes(self.base), before)

    def test_merge_leaves_the_file_and_lists_it(self):
        fx.write_tree(self.base, {".claude/skills/demo/SKILL.md": b"mine\n"})
        fx.git(self.base, "commit", "-qam", "edit")
        self.plan({".claude/skills/demo/SKILL.md": "theirs\n"})
        code, out, err = self.apply({"actions": {".claude/skills/demo/SKILL.md": "merge"}})
        self.assertEqual(code, 0, err)
        self.assertIn("Waiting for a merge", out)
        self.assertEqual((self.base / ".claude/skills/demo/SKILL.md").read_bytes(), b"mine\n")

    def test_kept_local_file_records_the_source_hash(self):
        fx.write_tree(self.base, {"schema.yml": b"types: [mine]\n"})
        fx.git(self.base, "commit", "-qam", "edit")
        self.plan({"schema.yml": "types: [note, upstream]\n"})
        code, out, err = self.apply({"actions": {"schema.yml": "keep"}})
        self.assertEqual(code, 0, err)
        self.assertEqual((self.base / "schema.yml").read_bytes(), b"types: [mine]\n")
        self.assertEqual(self.stamp()["files"]["schema.yml"],
                         kt.content_hash(b"types: [note, upstream]\n"))

    def test_content_untouched(self):
        before = self.content()
        self.plan({".claude/hooks/hook.py": HOOK2, "content/templates/book.md": "# new\n",
                   "content/REFERENCE/New.md": "# New\n", "README.md": "# new readme\n"})
        code, out, err = self.apply()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.content(), before)

    def test_rejected_plan_writes_nothing(self):
        self.plan({".claude/hooks/hook.py": HOOK2})
        before = fx.tree_hashes(self.base)
        code, out, err = self.apply({"approve": False})
        self.assertEqual(code, 0, err)
        self.assertEqual(fx.tree_hashes(self.base), before)

    def test_tampered_payload_writes_nothing(self):
        plan = self.plan({".claude/hooks/hook.py": HOOK2})
        (Path(plan["payload"]) / "src/.claude/hooks/hook.py").write_text("import os\n", encoding="utf-8")
        before = fx.tree_hashes(self.base)
        code, out, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("does not match the plan", err)
        self.assertEqual(fx.tree_hashes(self.base), before)

    def test_deletion_removes_empty_directories(self):
        self.plan({".claude/skills/demo/SKILL.md": None, ".claude/skills/demo/scripts/tool.py": None})
        code, out, err = self.apply()
        self.assertEqual(code, 0, err)
        self.assertFalse((self.base / ".claude/skills/demo").exists())


class RerenderTest(ApplyCase):
    NEW = "# {{KB_NAME}}\n\nOwner: {{KB_OWNER}}\n\nNew section.\n"

    def test_untouched_file_is_rerendered_on_request(self):
        self.plan({"AGENTS.template.md": self.NEW}, "--rerender")
        code, out, err = self.apply()
        self.assertEqual(code, 0, err)
        text = (self.base / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("New section.", text)
        entry = self.stamp()["rendered"]["AGENTS.md"]
        self.assertEqual(entry["output_hash"], kt.content_hash(text.encode()))
        self.assertEqual(entry["template_hash"], kt.content_hash(self.NEW.encode()))

    def test_not_requested_is_not_written(self):
        before = (self.base / "AGENTS.md").read_bytes()
        self.plan({"AGENTS.template.md": self.NEW})
        code, out, err = self.apply()
        self.assertEqual(code, 0, err)
        self.assertEqual((self.base / "AGENTS.md").read_bytes(), before)
        self.assertNotEqual(self.stamp()["rendered"]["AGENTS.md"]["template_hash"],
                            kt.content_hash(self.NEW.encode()))

    def test_hand_edited_file_is_never_written(self):
        fx.write_tree(self.base, {"AGENTS.md": b"# mine\n"})
        fx.git(self.base, "commit", "-qam", "edit")
        self.plan({"AGENTS.template.md": self.NEW})
        code, out, err = self.apply({"rerender": True})
        self.assertEqual(code, 0, err)
        self.assertEqual((self.base / "AGENTS.md").read_bytes(), b"# mine\n")
        self.assertIn("proposal only", out)

    def test_new_placeholder_value_is_saved_and_used(self):
        self.plan({"AGENTS.template.md": "# {{KB_NAME}}\n{{NEW_KEY}}\n"}, "--rerender")
        code, out, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("NEW_KEY", err)
        code, out, err = self.apply({"values": {"NEW_KEY": "answer"}})
        self.assertEqual(code, 0, err)
        self.assertIn("answer", (self.base / "AGENTS.md").read_text(encoding="utf-8"))
        values = json.loads((self.base / kt.ONBOARD_VALUES).read_text(encoding="utf-8"))
        self.assertEqual(values["NEW_KEY"], "answer")


class NoGitTest(ApplyCase):
    git = False

    def test_backup_holds_every_replaced_and_deleted_file(self):
        old_hook = (self.base / ".claude/hooks/hook.py").read_bytes()
        old_tool = (self.base / ".claude/skills/demo/scripts/tool.py").read_bytes()
        self.plan({".claude/hooks/hook.py": HOOK2, ".claude/skills/demo/scripts/tool.py": None})
        code, out, err = self.apply()
        self.assertEqual(code, 0, err)
        backups = list((self.base / kt.BACKUP_DIR).iterdir())
        self.assertEqual(len(backups), 1)
        self.assertTrue(backups[0].name.startswith("0.3.0-"))
        self.assertEqual((backups[0] / ".claude/hooks/hook.py").read_bytes(), old_hook)
        self.assertEqual((backups[0] / ".claude/skills/demo/scripts/tool.py").read_bytes(), old_tool)
        self.assertTrue((backups[0] / kt.STAMP).is_file())
        # The engine prints the resolved path; a temp dir can be an 8.3 alias (RUNNER~1).
        self.assertIn(str(backups[0].resolve()), out)
        code, out, err = self.commit()
        self.assertEqual(code, 0, err)
        self.assertIn("nothing to commit", out.lower())


class CommitTest(ApplyCase):
    def log(self):
        return fx.git(self.base, "log", "--format=%s").splitlines()

    def test_one_commit_and_unrelated_work_stays(self):
        note = self.base / "content/REFERENCE/Example.md"
        note.write_text("# Example\n\nwork in progress\n", encoding="utf-8")
        (self.base / "content/REFERENCE/Draft.md").write_text("draft\n", encoding="utf-8")
        fx.git(self.base, "add", "content/REFERENCE/Draft.md")  # staged, unrelated
        before = self.log()
        self.plan({".claude/hooks/hook.py": HOOK2, ".claude/skills/demo/SKILL.md": None})
        self.assertEqual(self.apply()[0], 0)
        code, out, err = self.commit()
        self.assertEqual(code, 0, err)
        after = self.log()
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(after[0], f"chore(template): upgrade to {fx.REPO} 0.3.0")
        files = set(fx.git(self.base, "show", "--name-only", "--format=", "HEAD").splitlines())
        self.assertEqual(files, {".claude/hooks/hook.py", ".claude/skills/demo/SKILL.md",
                                 ".kb-manifest.json", "CHANGELOG.md", kt.STAMP})
        status = fx.git(self.base, "status", "--porcelain")
        self.assertIn(" M content/REFERENCE/Example.md", status)
        self.assertIn("A  content/REFERENCE/Draft.md", status)

    def test_untracked_render_inputs_are_added(self):
        fx.git(self.base, "rm", "-q", "--cached", kt.ONBOARD_VALUES)
        fx.write_tree(self.base, {".gitignore": b"__pycache__/\n.kb-onboard.json\n"})
        fx.git(self.base, "commit", "-qam", "old ignore rule")
        self.plan({".claude/hooks/hook.py": HOOK2})
        self.assertEqual(self.apply({"actions": {".gitignore": "keep"}})[0], 0)
        code, out, err = self.commit()
        self.assertEqual(code, 0, err)
        files = fx.git(self.base, "show", "--name-only", "--format=", "HEAD").splitlines()
        self.assertIn(kt.ONBOARD_VALUES, files)

    def test_commit_needs_apply(self):
        self.plan({".claude/hooks/hook.py": HOOK2})
        code, out, err = self.commit()
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
