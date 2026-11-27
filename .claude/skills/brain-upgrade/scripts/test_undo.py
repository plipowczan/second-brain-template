"""The way back without git (bug 9 of the 0.4.x pilot): `apply` always makes the backup
folder and its backup.json, and `undo --backup` puts back what one update changed, only
while each file still holds what apply wrote, newest update first, in one transaction.
Run: python -m unittest -v"""

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import fixtures as fx
import kbtemplate as kt
import upgrade
from test_planner import make_instance

HOOK2 = "print('hook v2')\n"
TOOL = ".claude/skills/demo/scripts/tool.py"
NEW = ".claude/skills/new/SKILL.md"
CHANGES = {".claude/hooks/hook.py": HOOK2, TOOL: None, NEW: "new\n"}


class UndoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()
        self.base = make_instance(self.tmp.path / "kb", git=False)
        self.planfile = self.tmp.path / "plan.json"
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def update(self, version="0.3.0", changes=None, decisions=None, *extra) -> Path:
        """plan + apply + commit of one update without git; returns its backup folder."""
        self.n += 1
        src = fx.write_tree(self.tmp.path / f"src{self.n}",
                            fx.template(version, CHANGES if changes is None else changes))
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source", str(src),
                                "--out", str(self.planfile), *fx.CONSENT, *extra)
        self.assertEqual(code, 0, err)
        d = self.tmp.path / f"decisions{self.n}.json"
        d.write_text(json.dumps(decisions or {}), encoding="utf-8")
        code, out, err = fx.run("apply", "--plan", str(self.planfile), "--decisions", str(d))
        self.assertEqual(code, 0, err)
        backup = Path(out.split("Backup of every replaced or deleted file: ", 1)[1].splitlines()[0])
        self.assertIn(f"undo --backup {backup}", out)
        self.assertEqual(fx.run("commit", "--plan", str(self.planfile))[0], 0)
        return backup

    def undo(self, backup: Path, *extra):
        return fx.run("undo", "--backup", str(backup), *extra)

    def base_files(self) -> dict:
        """Everything in the base but the backups."""
        return {p: h for p, h in fx.tree_hashes(self.base).items()
                if not p.startswith(kt.BACKUP_DIR + "/")}

    def record(self, backup: Path) -> dict:
        return json.loads((backup / "backup.json").read_text(encoding="utf-8"))


class BackupRecordTest(UndoCase):
    def test_backup_json_lists_every_path_apply_wrote_or_deleted(self):
        before = self.base_files()
        backup = self.update()
        rec = self.record(backup)
        self.assertEqual((rec["format"], rec["mode"], rec["from_version"], rec["to_version"]),
                         (1, "upgrade", "0.2.0", "0.3.0"))
        paths = rec["paths"]
        self.assertEqual(paths[".claude/hooks/hook.py"],
                         {"before": before[".claude/hooks/hook.py"],
                          "after": kt.content_hash(HOOK2.encode())})
        self.assertEqual(paths[TOOL], {"before": before[TOOL], "after": None})
        self.assertEqual(paths[NEW], {"before": None, "after": kt.content_hash(b"new\n")})
        self.assertEqual(paths[kt.STAMP]["before"], before[kt.STAMP])
        self.assertEqual(paths[kt.STAMP]["after"], kt.file_hash(self.base / kt.STAMP))
        after = self.base_files()
        for rel, entry in paths.items():
            self.assertEqual(entry["after"], after.get(rel), rel)
        # Every file it replaced or deleted has its copy, with the hash recorded before.
        for rel in (".claude/hooks/hook.py", TOOL, kt.STAMP):
            self.assertEqual(kt.file_hash(backup / rel), paths[rel]["before"], rel)
        self.assertFalse((backup / NEW).exists())


class UndoTest(UndoCase):
    def test_undo_puts_the_base_back(self):
        before = self.base_files()
        backup = self.update()
        self.assertNotEqual(self.base_files(), before)
        code, out, err = self.undo(backup)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.base_files(), before)
        self.assertFalse((self.base / ".claude/skills/new").exists())  # its folder too
        self.assertIn("names 0.2.0 again", out)
        self.assertIn(f"deleted  {NEW} (the update added it)", out)
        self.assertTrue(backup.is_dir())  # the backup stays
        code, out, err = self.undo(backup)
        self.assertEqual(code, 1)
        self.assertIn("already undone", err)
        self.assertEqual(self.base_files(), before)

    def test_an_added_file_edited_after_the_update_is_kept(self):
        before = self.base_files()
        backup = self.update()
        (self.base / NEW).write_text("new\nmy own line\n", encoding="utf-8")
        code, out, err = self.undo(backup)
        self.assertEqual(code, 0, err)
        self.assertIn(f"Kept, because they changed after the update", out)
        self.assertIn(NEW, out.split("Kept,", 1)[1])
        self.assertEqual((self.base / NEW).read_text(encoding="utf-8"), "new\nmy own line\n")
        now = self.base_files()
        self.assertEqual({p: h for p, h in now.items() if p != NEW}, before)

    def test_the_newer_backup_goes_first(self):
        before = self.base_files()
        older = self.update("0.3.0")
        middle = self.base_files()
        newer = self.update("0.4.0", {".claude/hooks/hook.py": "print('hook v3')\n"})
        code, out, err = self.undo(older)
        self.assertEqual(code, 1)
        self.assertIn(f"undo --backup {newer}", err)
        self.assertIn("Nothing was changed", err)
        self.assertEqual(self.undo(newer)[0], 0)
        self.assertEqual(self.base_files(), middle)
        self.assertEqual(self.undo(older)[0], 0)
        self.assertEqual(self.base_files(), before)

    def test_a_rerendered_writing_style_is_put_back(self):
        style = (self.base / kt.WRITING_STYLE).read_bytes()
        notes = {p: h for p, h in self.base_files().items() if p.startswith("content/")}
        backup = self.update(changes={"content/WRITING_STYLE.template.md":
                                      "Language: {{PRIMARY_LANGUAGE}}\n\nNew rule.\n"},
                             decisions={"rerender": [kt.WRITING_STYLE]})
        self.assertIn("New rule.", (self.base / kt.WRITING_STYLE).read_text(encoding="utf-8"))
        self.assertIn(kt.WRITING_STYLE, self.record(backup)["paths"])
        self.assertEqual((backup / kt.WRITING_STYLE).read_bytes(), style)
        code, out, err = self.undo(backup)
        self.assertEqual(code, 0, err)
        self.assertEqual((self.base / kt.WRITING_STYLE).read_bytes(), style)
        self.assertEqual({p: h for p, h in self.base_files().items() if p.startswith("content/")},
                         notes)

    def test_new_values_are_put_back(self):
        values = (self.base / kt.ONBOARD_VALUES).read_bytes()
        backup = self.update(changes={"AGENTS.template.md": "# {{KB_NAME}}\n{{NEW_KEY}}\n"},
                             decisions={"rerender": ["AGENTS.md"], "values": {"NEW_KEY": "x"}})
        self.assertIn(kt.ONBOARD_VALUES, self.record(backup)["paths"])
        self.assertEqual(self.undo(backup)[0], 0)
        self.assertEqual((self.base / kt.ONBOARD_VALUES).read_bytes(), values)

    def test_a_failed_write_puts_everything_back(self):
        backup = self.update()
        after = self.base_files()
        real, calls = upgrade._write, {"n": 0}

        def failing(path, data):
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("disk full")
            real(path, data)
        with mock.patch.object(upgrade, "_write", failing):
            code, out, err = self.undo(backup)
        self.assertEqual(code, 1, out)
        self.assertIn("undo failed at", err)
        self.assertIn("Every change was rolled back", err)
        self.assertEqual(self.base_files(), after)
        self.assertEqual(self.undo(backup)[0], 0)  # and it can run again

    def test_the_base_engine_undoes_the_update_that_replaced_it(self):
        # The documented command runs the base's own engine, which the update replaced:
        # undo rewrites the files it runs from, and must still finish.
        here = Path(__file__).resolve().parent
        names = ("upgrade.py", "planner.py", "sources.py", "kbtemplate.py")
        engine = ".claude/skills/brain-upgrade/scripts/"

        def release(mark):
            return {engine + n: (here / n).read_text(encoding="utf-8") + f"\n# {mark}\n"
                    for n in names}
        self.update("0.3.0", release("engine A"))
        middle = self.base_files()
        newer = self.update("0.4.0", release("engine B"))
        r = subprocess.run([sys.executable, "-B", str(self.base / engine / "upgrade.py"), "undo",
                            "--backup", str(newer)], capture_output=True, text=True,
                           cwd=str(self.tmp.path))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("names 0.3.0 again", r.stdout)
        self.assertEqual(self.base_files(), middle)
        self.assertIn("# engine A", (self.base / engine / "upgrade.py").read_text(encoding="utf-8"))

    def test_the_default_instance_is_the_base_the_backup_is_in(self):
        backup = self.update()
        cwd = os.getcwd()
        os.chdir(self.tmp.path)  # not the base
        try:
            code, out, err = self.undo(backup)
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 0, err)
        code, out, err = self.undo(self.tmp.path / "elsewhere")
        self.assertEqual(code, 1)
        self.assertIn("--instance", err)


class UndoRefusalTest(UndoCase):
    def assert_refused(self, backup: Path, words: str):
        before = self.base_files()
        code, out, err = self.undo(backup)
        self.assertEqual(code, 1, out)
        self.assertIn(words, err)
        self.assertEqual(self.base_files(), before)

    def edit_record(self, backup: Path, fn) -> None:
        rec = self.record(backup)
        fn(rec)
        (backup / "backup.json").write_text(json.dumps(rec), encoding="utf-8")

    def test_no_or_broken_backup_json(self):
        backup = self.update()
        (backup / "backup.json").write_text("{not json", encoding="utf-8")
        self.assert_refused(backup, "no valid backup.json (not JSON")
        (backup / "backup.json").unlink()
        self.assert_refused(backup, "no valid backup.json (missing")
        self.assert_refused(backup.parent / "nothing-here", "no such folder")

    def test_an_invalid_record(self):
        backup = self.update()
        good = self.record(backup)
        for fn, words in (
                (lambda r: r.update(format=2), "unknown format"),
                (lambda r: r.update(paths={}), "no paths"),
                (lambda r: r["paths"].pop(kt.STAMP), f"does not record {kt.STAMP}"),
                (lambda r: r["paths"][NEW].update(after="md5:x"), "a bad entry"),
                (lambda r: r["paths"].update({"../outside.txt": {"before": None, "after": None}}),
                 "unsafe path")):
            with self.subTest(words=words):
                (backup / "backup.json").write_text(json.dumps(good), encoding="utf-8")
                self.edit_record(backup, fn)
                self.assert_refused(backup, words)

    def test_a_path_under_content_is_refused(self):
        backup = self.update()
        note = "content/REFERENCE/Example.md"
        h = kt.file_hash(self.base / note)
        self.edit_record(backup, lambda r: r["paths"].update({note: {"before": None, "after": h}}))
        self.assert_refused(backup, f"refusing to touch {note}")
        self.assertTrue((self.base / note).is_file())

    def test_a_changed_copy_is_refused(self):
        backup = self.update()
        (backup / TOOL).write_text("print('planted')\n", encoding="utf-8")
        self.assert_refused(backup, f"copy of {TOOL} is missing or does not match")

    def test_a_stamp_changed_by_hand_is_refused(self):
        backup = self.update()
        stamp = self.base / kt.STAMP
        stamp.write_text(stamp.read_text(encoding="utf-8").replace("0.3.0", "0.3.9"),
                         encoding="utf-8")
        self.assert_refused(backup, "no longer the one this update left")

    def link(self, link: Path, target: Path):
        try:
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(target), str(link))
            else:
                os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"this system does not let the test create a link ({e})")

    def test_a_link_in_a_path_is_refused(self):
        # The folder of the added skill becomes a link to a folder outside the base that
        # holds the same file: its hash matches, and undo still writes nothing through it.
        backup = self.update()
        outside = self.tmp.path / "outside"
        shutil.copytree(self.base / ".claude/skills/new", outside)
        shutil.rmtree(self.base / ".claude/skills/new")
        self.link(self.base / ".claude/skills/new", outside)
        self.assert_refused(backup, "link or junction")
        self.assertEqual((outside / "SKILL.md").read_text(encoding="utf-8"), "new\n")


class AdoptionBackupTest(unittest.TestCase):
    """An adoption without git that only adds files and the stamp still gets its backup
    folder, and the report names that folder (it used to name one that did not exist)."""

    @classmethod
    def setUpClass(cls):
        cls.ctmp = fx.TempDir()
        cls.repo = cls.ctmp.path / "template"
        fx.build_history(cls.repo)
        cls.zip = fx.zip_of(cls.repo, "v0.2.0", cls.ctmp.path / "kb-template-0.2.0.zip")

    @classmethod
    def tearDownClass(cls):
        cls.ctmp.cleanup()

    def setUp(self):
        self.tmp = fx.TempDir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_adoption_that_only_adds(self):
        import planner
        base = self.tmp.path / "kb"
        tree = {p: v for p, v in fx.enc(fx.P3).items()
                if not p.endswith(".template.md") and p not in ("LICENSE", "CONTRIBUTING.md")}
        for out, tpl in fx.CLASSES["rendered"].items():
            tree[out], _, _ = planner.render(fx.RENDER_PY, fx.P3[tpl].encode(), fx.VALUES)
        tree[kt.ONBOARD_VALUES] = json.dumps(fx.VALUES).encode()
        fx.write_tree(base, tree)
        before = fx.tree_hashes(base)
        planfile = self.tmp.path / "plan.json"
        code, out, err = fx.run("plan", "--instance", str(base), "--source", str(self.zip),
                                "--out", str(planfile), "--adopt", *fx.CONSENT)
        self.assertEqual(code, 0, err)
        plan = json.loads(planfile.read_text(encoding="utf-8"))
        self.assertEqual({a["kind"] for a in plan["actions"]}, {"add"})
        d = self.tmp.path / "decisions.json"
        d.write_text("{}", encoding="utf-8")
        code, out, err = fx.run("apply", "--plan", str(planfile), "--decisions", str(d))
        self.assertEqual(code, 0, err)
        named = Path(out.split("Backup of every replaced or deleted file: ", 1)[1].splitlines()[0])
        self.assertTrue(named.is_dir())
        self.assertEqual(named.parent, (base / kt.BACKUP_DIR).resolve())
        rec = json.loads((named / "backup.json").read_text(encoding="utf-8"))
        added = {a["path"] for a in plan["actions"]}
        self.assertEqual(set(rec["paths"]), added | {kt.STAMP})
        self.assertTrue(all(e["before"] is None for e in rec["paths"].values()))
        self.assertEqual((rec["mode"], rec["from_version"], rec["to_version"]),
                         ("adopt", None, "0.2.0"))
        self.assertEqual(os.listdir(named), ["backup.json"])  # nothing was replaced
        code, out, err = fx.run("commit", "--plan", str(planfile))
        self.assertEqual(code, 0, err)
        self.assertIn(f"Backup: {named}", out)
        # Undo takes the adoption back, the stamp included.
        code, out, err = fx.run("undo", "--backup", str(named))
        self.assertEqual(code, 0, err)
        self.assertIn("the adoption is undone", out)
        self.assertEqual({p: h for p, h in fx.tree_hashes(base).items()
                          if not p.startswith(kt.BACKUP_DIR + "/")}, before)


# No test may leave a kb-upgrade-* folder in the temp directory (fixtures.py).
tearDownModule = fx.tear_down_module


if __name__ == "__main__":
    unittest.main()
