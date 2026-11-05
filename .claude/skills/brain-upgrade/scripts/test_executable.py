#!/usr/bin/env python3
"""The executable bit: from the manifest's list through the plan, apply and the commit.

Modes in git are checked on every system. The bit on disk exists only on Linux and macOS,
so those checks are skipped on Windows and run in CI on Linux. Run: python -m unittest -v"""

import json
import os
import unittest
from pathlib import Path
from unittest import mock

import fixtures as fx
import kbtemplate as kt
import planner
import upgrade
from test_adopt import AdoptCase
from test_planner import make_instance

HOOK = ".githooks/pre-commit"
TEXT = "#!/bin/sh\necho lint\n"
TEXT2 = "#!/bin/sh\necho lint two\n"
OLD = fx.template("0.2.0", {HOOK: TEXT})
POSIX = os.name == "posix"


def set_exec(base: Path, path: str) -> None:
    """Make a tracked file executable the way an owner would, on any system."""
    fx.git(base, "update-index", "--chmod=+x", "--", path)
    if POSIX:
        os.chmod(base / path, 0o755)
    fx.git(base, "commit", "-q", "-m", f"chmod +x {path}")


class ExecutableCase(unittest.TestCase):
    git = True
    start = OLD

    def setUp(self):
        self.tmp = fx.TempDir()
        self.base = make_instance(self.tmp.path / "kb", self.start, git=self.git)
        self.planfile = self.tmp.path / "plan.json"
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, version="0.3.0", changes=None, listed=(HOOK,)) -> Path:
        self.n += 1
        return fx.write_tree(self.tmp.path / f"src{self.n}",
                             fx.template(version, {HOOK: TEXT, **(changes or {})}, listed))

    def plan(self, src=None, *extra) -> dict:
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source",
                                str(src or self.source()), "--out", str(self.planfile),
                                *fx.CONSENT, *extra)
        self.assertEqual(code, 0, err)
        self.summary = out
        return json.loads(self.planfile.read_text(encoding="utf-8"))

    def apply(self, decisions=None) -> tuple:
        d = self.tmp.path / "decisions.json"
        d.write_text(json.dumps(decisions or {}), encoding="utf-8")
        return fx.run("apply", "--plan", str(self.planfile), "--decisions", str(d))

    def applied(self, decisions=None) -> None:
        code, out, err = self.apply(decisions)
        self.assertEqual(code, 0, err)
        code, out, err = fx.run("commit", "--plan", str(self.planfile))
        self.assertEqual(code, 0, err)

    def mode(self, path=HOOK) -> str:
        return fx.git(self.base, "ls-tree", "HEAD", "--", path).split()[0]

    def assert_on_disk(self, executable: bool, path=HOOK) -> None:
        if POSIX:
            self.assertEqual(bool(kt.file_bits(self.base / path) & 0o100), executable)

    def rows(self, plan: dict) -> list[str]:
        return [m["path"] for m in plan["modes"]]


class PlanTest(ExecutableCase):
    def test_equal_content_gets_a_row_and_no_action(self):
        plan = self.plan()
        self.assertEqual(self.rows(plan), [HOOK])
        self.assertNotIn(HOOK, [a["path"] for a in plan["actions"]])
        self.assertIn("Executable bit", self.summary)
        self.assertIn(f"[x] {HOOK}", self.summary)

    def test_a_file_outside_the_list_gets_no_row(self):
        self.assertEqual(self.rows(self.plan(self.source(listed=()))), [])

    def test_a_file_that_has_the_bit_gets_no_row(self):
        set_exec(self.base, HOOK)
        self.assertEqual(self.rows(self.plan()), [])

    def test_a_listed_file_the_source_does_not_ship_is_skipped(self):
        plan = self.plan(self.source(listed=(HOOK, ".claude/hooks/gone.py")))
        self.assertEqual(plan["executable"], [HOOK])

    def test_edited_file_stays_keep_yours_and_gets_a_row(self):
        fx.write_tree(self.base, {HOOK: TEXT2.encode()})
        fx.git(self.base, "commit", "-qam", "my hook")
        plan = self.plan()
        action = next(a for a in plan["actions"] if a["path"] == HOOK)
        self.assertEqual(action["kind"], "keep")
        self.assertIn("keep (yours)", self.summary)
        self.assertEqual(self.rows(plan), [HOOK])
        self.assertIn("your text stays", plan["modes"][0]["note"])
        self.assertTrue(plan["modes"][0]["selected"])

    def test_every_kind_of_source_gives_the_same_answer(self):
        files = fx.template("0.3.0", {HOOK: TEXT}, (HOOK,))
        folder = fx.write_tree(self.tmp.path / "folder", files)
        plain_zip = self.tmp.path / "rebuilt.zip"
        plain_zip.write_bytes(fx.zip_bytes(files))  # no mode information at all
        clone = self.tmp.path / "clone"
        fx.git_init(clone)
        fx.commit_tree(clone, files, "release", tag="v0.3.0")
        for src in (folder, plain_zip, clone):
            with self.subTest(source=src.name):
                self.assertEqual(self.rows(self.plan(src)), [HOOK])

    def test_a_listed_note_stops_the_source(self):
        before = fx.tree_hashes(self.base)
        src = self.source(listed=("content/REFERENCE/Example.md",))
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source", str(src),
                                "--out", str(self.planfile), *fx.CONSENT)
        self.assertEqual(code, 1, out)
        self.assertIn("belongs to the base", err)
        self.assertEqual(fx.tree_hashes(self.base), before)

    def test_a_tampered_plan_cannot_reach_the_notes(self):
        self.plan()
        plan = json.loads(self.planfile.read_text(encoding="utf-8"))
        plan["modes"][0]["path"] = "content/REFERENCE/Example.md"
        self.planfile.write_text(json.dumps(plan), encoding="utf-8")
        code, out, err = self.apply()
        self.assertEqual(code, 1, out)
        self.assertIn("refusing to change the mode", err)


class ApplyAndCommitTest(ExecutableCase):
    def test_equal_content_becomes_executable(self):
        self.plan()
        self.applied()
        self.assertEqual(self.mode(), kt.MODE_EXECUTABLE)
        self.assert_on_disk(True)
        self.assertEqual(fx.git(self.base, "status", "--porcelain"), "")
        self.assertIn("made executable", fx.git(self.base, "log", "-1", "--format=%b"))

    def test_the_text_of_an_edited_file_stays_and_the_bit_moves(self):
        fx.write_tree(self.base, {HOOK: TEXT2.encode()})
        fx.git(self.base, "commit", "-qam", "my hook")
        self.plan()
        self.applied()
        self.assertEqual(self.mode(), kt.MODE_EXECUTABLE)
        self.assertEqual((self.base / HOOK).read_text(encoding="utf-8"), TEXT2)
        self.assertEqual(fx.git(self.base, "status", "--porcelain"), "")

    def test_owner_declines_and_is_asked_again(self):
        for decline in (False, []):
            with self.subTest(decline=decline):
                self.plan()
                self.applied({"executable": decline})
                self.assertEqual(self.mode(), "100644")
                self.assert_on_disk(False)
        self.assertEqual(self.rows(self.plan()), [HOOK])

    def test_unknown_path_in_the_decision_is_refused(self):
        self.plan()
        code, out, err = self.apply({"executable": ["schema.yml"]})
        self.assertEqual(code, 1, out)
        self.assertIn("schema.yml", err)

    def test_declined_row_also_covers_a_write_of_the_file(self):
        self.plan(self.source(changes={HOOK: TEXT2}))
        self.applied({"executable": False})
        self.assertEqual((self.base / HOOK).read_text(encoding="utf-8"), TEXT2)
        self.assertEqual(self.mode(), "100644")

    def test_update_with_the_row_writes_once_and_sets_the_bit(self):
        self.plan(self.source(changes={HOOK: TEXT2}))
        self.applied()
        self.assertEqual(self.mode(), kt.MODE_EXECUTABLE)
        self.assertEqual((self.base / HOOK).read_text(encoding="utf-8"), TEXT2)
        self.assertEqual(fx.git(self.base, "status", "--porcelain"), "")

    def conflict(self):
        fx.write_tree(self.base, {HOOK: b"#!/bin/sh\necho mine\n"})
        fx.git(self.base, "commit", "-qam", "my hook")
        self.plan(self.source(changes={HOOK: TEXT2}))

    def test_conflict_overwritten(self):
        self.conflict()
        self.applied({"actions": {HOOK: "overwrite"}})
        self.assertEqual((self.base / HOOK).read_text(encoding="utf-8"), TEXT2)
        self.assertEqual(self.mode(), kt.MODE_EXECUTABLE)

    def test_conflict_kept(self):
        self.conflict()
        self.applied({"actions": {HOOK: "keep"}})
        self.assertEqual((self.base / HOOK).read_text(encoding="utf-8"), "#!/bin/sh\necho mine\n")
        self.assertEqual(self.mode(), kt.MODE_EXECUTABLE)

    def test_conflict_merged_by_hand_after_apply(self):
        self.conflict()
        code, out, err = self.apply({"actions": {HOOK: "merge"}})
        self.assertEqual(code, 0, err)
        (self.base / HOOK).write_text("#!/bin/sh\necho merged\n", encoding="utf-8", newline="\n")
        code, out, err = fx.run("commit", "--plan", str(self.planfile))
        self.assertEqual(code, 0, err)
        self.assertEqual(self.mode(), kt.MODE_EXECUTABLE)
        self.assertEqual(fx.git(self.base, "show", f"HEAD:{HOOK}"), "#!/bin/sh\necho merged")

    def test_a_bit_only_row_is_checked_like_a_write(self):
        self.plan()
        (self.base / HOOK).write_text("#!/bin/sh\necho changed\n", encoding="utf-8")
        code, out, err = self.apply()
        self.assertEqual(code, 1, out)
        self.assertIn(HOOK, err)
        self.assertIn("Nothing was written", err)

    def test_uncommitted_work_stops_a_bit_only_row(self):
        (self.base / HOOK).write_text(TEXT2, encoding="utf-8")
        self.plan()
        code, out, err = self.apply()
        self.assertEqual(code, 1, out)
        self.assertIn("uncommitted changes in planned paths", err)

    def test_stamp_after_a_bit_only_upgrade_is_new(self):
        self.plan()
        self.applied()
        stamp = json.loads((self.base / kt.STAMP).read_text(encoding="utf-8"))
        self.assertEqual(stamp["version"], "0.3.0")


class NewFileTest(ExecutableCase):
    start = fx.template("0.2.0")

    def test_added_file_has_the_mode_of_the_release(self):
        plan = self.plan()
        self.assertEqual(next(a for a in plan["actions"] if a["path"] == HOOK)["kind"], "add")
        self.assertEqual(self.rows(plan), [])
        self.applied()
        self.assertEqual(self.mode(), kt.MODE_EXECUTABLE)
        self.assert_on_disk(True)
        self.assertEqual(fx.git(self.base, "status", "--porcelain"), "")

    def test_added_file_outside_the_list_stays_plain(self):
        self.plan(self.source(listed=()))
        self.applied()
        self.assertEqual(self.mode(), "100644")
        self.assert_on_disk(False)


class KeptBitTest(ExecutableCase):
    def test_update_of_an_executable_file_keeps_the_bit(self):
        set_exec(self.base, HOOK)
        self.plan(self.source(changes={HOOK: TEXT2}))
        self.applied()
        self.assertEqual(self.mode(), kt.MODE_EXECUTABLE)
        self.assert_on_disk(True)
        self.assertEqual(fx.git(self.base, "status", "--porcelain"), "")

    def test_a_bit_outside_the_list_is_never_removed(self):
        tool = ".claude/hooks/hook.py"
        set_exec(self.base, tool)
        self.plan(self.source(changes={tool: "print('hook v2')\n"}))
        self.applied()
        self.assertEqual(self.mode(tool), kt.MODE_EXECUTABLE)
        self.assert_on_disk(True, tool)
        self.assertEqual(fx.git(self.base, "status", "--porcelain"), "")


class AlreadyPastTest(ExecutableCase):
    """A base that went through an update with an engine that did not carry the bit: its
    content equals the release, so only the bit can show that it is not finished."""
    start = fx.template("0.2.0", {HOOK: TEXT}, (HOOK,))

    def source_same(self) -> Path:
        self.n += 1
        return fx.write_tree(self.tmp.path / f"src{self.n}", self.start)

    def test_not_up_to_date_until_the_bit_is_set(self):
        plan = self.plan(self.source_same())
        self.assertFalse(plan["up_to_date"])
        self.assertEqual(plan["actions"], [])
        self.assertNotIn("Up to date", self.summary)
        self.applied()
        self.assertEqual(self.mode(), kt.MODE_EXECUTABLE)
        again = self.plan(self.source_same())
        self.assertTrue(again["up_to_date"])
        self.assertIn("Up to date", self.summary)


class RollbackTest(ExecutableCase):
    def test_a_failed_apply_puts_the_bit_back(self):
        self.plan()
        before = kt.file_bits(self.base / HOOK)
        real = upgrade._write

        def failing(path, data):
            if Path(path).name == kt.STAMP:
                self.assert_on_disk(True)  # the bit step ran before the stamp
                raise OSError("injected failure")
            real(path, data)
        with mock.patch.object(upgrade, "_write", failing):
            code, out, err = self.apply()
        self.assertEqual(code, 1, out)
        self.assertIn("rolled back", err)
        self.assertEqual(kt.file_bits(self.base / HOOK), before)
        self.assertEqual(fx.git(self.base, "status", "--porcelain"), "")

    @unittest.skipUnless(POSIX, "only Linux and macOS have the bit on disk")
    def test_a_restored_file_gets_its_bits_back(self):
        set_exec(self.base, HOOK)
        self.plan(self.source(changes={HOOK: None}, listed=()))
        real = upgrade._write

        def failing(path, data):
            if Path(path).name == kt.STAMP:
                raise OSError("injected failure")
            real(path, data)
        with mock.patch.object(upgrade, "_write", failing):
            self.assertEqual(self.apply()[0], 1)
        self.assert_on_disk(True)


class WithoutGitTest(ExecutableCase):
    git = False

    def test_the_file_itself_is_the_only_truth(self):
        plan = self.plan()
        if not POSIX:
            self.assertEqual(self.rows(plan), [])  # no bit to read on Windows without git
            return
        self.assertEqual(self.rows(plan), [HOOK])
        code, out, err = self.apply()
        self.assertEqual(code, 0, err)
        self.assert_on_disk(True)
        self.assertEqual(self.rows(self.plan()), [])


class AdoptionTest(AdoptCase):
    """The first update of a base from before 0.2.0 is an adoption: it writes and commits
    like an upgrade, and the list comes from the source, because the base has no manifest."""
    executable = (HOOK,)

    def mode(self, base) -> str:
        return fx.git(base, "ls-tree", "HEAD", "--", HOOK).split()[0]

    def test_adoption_makes_the_hook_executable(self):
        base = self.instance({**fx.P1, HOOK: "#!/bin/sh\n"})
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.assertEqual(code, 0, err)
        self.assertEqual(plan["to_version"], "0.1.0")
        self.assertEqual([m["path"] for m in plan["modes"]], [HOOK])
        self.apply_commit()
        self.assertEqual(self.mode(base), kt.MODE_EXECUTABLE)
        self.assertEqual(fx.git(base, "status", "--porcelain"), "")

    def test_edited_hook_keeps_its_text(self):
        base = self.instance({**fx.P1, HOOK: "#!/bin/sh\n"}, edits={HOOK: TEXT2})
        code, out, err, plan = self.plan(base, None, "--adopt")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.acts(plan)[HOOK][0], "keep")
        self.apply_commit()
        self.assertEqual(self.mode(base), kt.MODE_EXECUTABLE)
        self.assertEqual((base / HOOK).read_text(encoding="utf-8"), TEXT2)


class HelperTest(unittest.TestCase):
    def test_execute_follows_read(self):
        self.assertEqual(kt.with_executable(0o644), 0o755)
        self.assertEqual(kt.with_executable(0o640), 0o750)
        self.assertEqual(kt.with_executable(0o600), 0o700)
        self.assertIsNone(kt.with_executable(None))

    def test_chosen_modes(self):
        plan = {"modes": [{"path": "a", "selected": True}, {"path": "b", "selected": False}]}
        self.assertEqual(planner.chosen_modes(plan, None), {"a"})
        self.assertEqual(planner.chosen_modes(plan, True), {"a", "b"})
        self.assertEqual(planner.chosen_modes(plan, False), set())
        self.assertEqual(planner.chosen_modes(plan, ["b"]), {"b"})


if __name__ == "__main__":
    unittest.main()
