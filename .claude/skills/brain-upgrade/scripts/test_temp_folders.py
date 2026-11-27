"""The temporary folders of an upgrade (bug 8 of the 0.4.x pilot): plan and fetch say
which folders they made, commit deletes the plan's own folder as its last step and keeps
the download, a failed step deletes nothing, and `cleanup` deletes only brain-upgrade's
own folders, never by pattern. Run: python -m unittest -v"""

import json
import os
import re
import tempfile
import unittest
from pathlib import Path

import fixtures as fx
import sources
from test_planner import make_instance

HOOK2 = "print('hook v2')\n"
COMMIT = "c" * 40


class TempFolderCase(unittest.TestCase):
    git = True

    def setUp(self):
        self.tmp = fx.TempDir()
        self.base = make_instance(self.tmp.path / "kb", git=self.git)
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, changes=None) -> Path:
        self.n += 1
        return fx.write_tree(self.tmp.path / f"src{self.n}",
                             fx.template("0.3.0", {".claude/hooks/hook.py": HOOK2, **(changes or {})}))

    def opener(self, url: str) -> bytes:
        return fx.zip_bytes(fx.template("0.3.0", {".claude/hooks/hook.py": HOOK2}), comment=COMMIT)

    def plan(self, *args, base=None, opener=None):
        """A plan in its default place, the temp directory; returns (plan file, the
        folders it reported, by purpose)."""
        base = base or self.base
        if not args:
            args = ("--source", str(self.source()), *fx.CONSENT)
        code, out, err = fx.run("plan", "--instance", str(base), *args, opener=opener)
        self.assertEqual(code, 0, err)
        plan = Path(re.search(r"^Plan: (.+)$", out, re.M).group(1))
        return plan, fx.temp_folders_of(out)

    def apply(self, plan: Path, decisions=None):
        d = self.tmp.path / f"decisions{self.n}.json"
        d.write_text(json.dumps(decisions or {}), encoding="utf-8")
        return fx.run("apply", "--plan", str(plan), "--decisions", str(d))

    def commit(self, plan: Path):
        return fx.run("commit", "--plan", str(plan))


class PlanFolderTest(TempFolderCase):
    def test_plan_and_payload_share_one_reported_folder(self):
        plan, folders = self.plan()
        self.assertEqual(list(folders), ["plan"])
        folder = Path(folders["plan"][0])
        self.assertEqual(plan.parent, folder.resolve())
        data = json.loads(plan.read_text(encoding="utf-8"))
        self.assertEqual(Path(data["temp_folder"]), folder)
        self.assertEqual(Path(data["payload"]).parent, plan.parent)
        self.assertTrue(folder.name.startswith(sources.TEMP_PREFIX))
        self.assertEqual(folder.parent.resolve(), Path(tempfile.gettempdir()).resolve())

    def test_commit_deletes_the_plan_folder_and_keeps_the_download(self):
        plan, folders = self.plan("--to", "0.3.0", opener=self.opener)
        self.assertEqual(sorted(folders), ["download", "plan"])
        download = Path(folders["download"][0])
        archive = Path(json.loads(plan.read_text(encoding="utf-8"))["source"]["archive"])
        self.assertEqual(archive.parent, download)
        self.assertEqual(self.apply(plan)[0], 0)
        self.assertTrue(plan.is_file())  # apply deletes nothing
        code, out, err = self.commit(plan)
        self.assertEqual(code, 0, err)
        self.assertIn("Committed", out)
        self.assertIn("Deleted the plan's temporary folder", out)
        self.assertFalse(plan.parent.exists())
        self.assertTrue(archive.is_file())  # reusable offline, e.g. after an adoption
        # Offline, the archive the plan downloaded is still a source.
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source", str(archive),
                                *fx.CONSENT, opener=fx_offline)
        self.assertEqual(code, 0, err)
        self.assertIn("Up to date", out)

    def test_a_merge_finds_the_payload_after_apply(self):
        hook = self.base / ".claude/hooks/hook.py"
        hook.write_text("print('mine')\n", encoding="utf-8")
        fx.git(self.base, "commit", "-qam", "my hook")
        plan, folders = self.plan()
        payload = Path(json.loads(plan.read_text(encoding="utf-8"))["payload"])
        code, out, err = self.apply(plan, {"actions": {".claude/hooks/hook.py": "merge"}})
        self.assertEqual(code, 0, err)
        theirs = payload / "src/.claude/hooks/hook.py"
        self.assertEqual(theirs.read_text(encoding="utf-8"), HOOK2)  # what Phase 6 reads
        hook.write_text("print('mine')\n" + HOOK2, encoding="utf-8")  # the merge
        code, out, err = self.commit(plan)
        self.assertEqual(code, 0, err)
        self.assertFalse(payload.exists())
        self.assertFalse(plan.parent.exists())

    def test_a_parallel_plan_keeps_its_folders(self):
        other = make_instance(self.tmp.path / "other")
        waiting, _ = self.plan(base=other)  # waiting for the owner's review
        waiting_payload = Path(json.loads(waiting.read_text(encoding="utf-8"))["payload"])
        plan, _ = self.plan()
        self.assertEqual(self.apply(plan)[0], 0)
        code, out, err = self.commit(plan)
        self.assertEqual(code, 0, err)
        self.assertFalse(plan.parent.exists())
        self.assertTrue(waiting.is_file())
        self.assertTrue((waiting_payload / "src/.claude/hooks/hook.py").is_file())
        # ... and that plan still goes through.
        self.assertEqual(self.apply(waiting)[0], 0)
        self.assertEqual(self.commit(waiting)[0], 0)
        self.assertFalse(waiting.parent.exists())

    def test_a_plan_written_with_out_is_kept(self):
        planfile = self.tmp.path / "my-plan.json"
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source",
                                str(self.source()), "--out", str(planfile), *fx.CONSENT)
        self.assertEqual(code, 0, err)
        self.assertNotIn("Temporary folder", out)
        self.assertEqual(self.apply(planfile)[0], 0)
        code, out, err = self.commit(planfile)
        self.assertEqual(code, 0, err)
        self.assertTrue(planfile.is_file())
        self.assertTrue(planfile.with_suffix(".files").is_dir())

    def test_commit_deletes_only_the_folder_the_plan_file_is_in(self):
        # The plan file is not trusted: one that names another folder as its own (here a
        # download folder) gets the commit, and that folder stays.
        plan, folders = self.plan()
        decoy = sources.private_dir("decoy")
        (decoy / "keep.txt").write_text("x\n", encoding="utf-8")
        data = json.loads(plan.read_text(encoding="utf-8"))
        data["temp_folder"] = str(decoy)
        plan.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(self.apply(plan)[0], 0)
        code, out, err = self.commit(plan)
        self.assertEqual(code, 0, err)
        self.assertIn("Kept", out)
        self.assertTrue((decoy / "keep.txt").is_file())
        self.assertTrue(plan.is_file())
        fx.REPORTED.append(str(decoy))

    def test_a_failed_step_keeps_its_folders(self):
        plan, _ = self.plan()
        (self.base / ".claude/hooks/hook.py").write_text("print('edited')\n", encoding="utf-8")
        code, out, err = self.apply(plan)
        self.assertEqual(code, 1)
        self.assertIn("changed since the dry run", err)
        self.assertTrue(plan.is_file())
        code, out, err = self.commit(plan)  # not applied: refused
        self.assertEqual(code, 1)
        self.assertTrue(plan.is_file())
        fx.git(self.base, "checkout", "-q", "--", ".claude/hooks/hook.py")
        self.assertEqual(self.apply(plan)[0], 0)
        (self.base / ".claude/hooks/hook.py").write_text("print('after apply')\n", encoding="utf-8")
        code, out, err = self.commit(plan)
        self.assertEqual(code, 1)
        self.assertIn("changed after apply", err)
        self.assertTrue(plan.is_file())
        self.assertTrue(Path(json.loads(plan.read_text(encoding="utf-8"))["payload"]).is_dir())

    def test_a_refused_plan_names_the_download_it_keeps(self):
        # The release downloads, then the plan stops (it is older than the base): the
        # download stays for diagnosis, and the error output names it for cleanup.
        def older(url):
            return fx.zip_bytes(fx.template("0.1.0"), comment=COMMIT)
        code, out, err = fx.run("plan", "--instance", str(self.base), "--to", "0.1.0",
                                opener=older)
        self.assertEqual(code, 1)
        self.assertIn("downgrades are not supported", err)
        folders = fx.temp_folders_of(err)
        self.assertEqual(list(folders), ["download"])
        self.assertTrue((Path(folders["download"][0]) / "kb-template-v0.1.0.zip").is_file())
        # Refused before anything was made: nothing to name.
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source",
                                str(self.source()))
        self.assertEqual(code, 1)
        self.assertEqual(fx.temp_folders_of(err), {})

    def test_fetch_reports_its_folders(self):
        code, out, err = fx.run("fetch", "--instance", str(self.base), "--to", "0.3.0",
                                opener=self.opener)
        self.assertEqual(code, 0, err)
        fetched = json.loads(out)
        folders = [Path(p) for p in fetched["temp_folders"]]
        self.assertEqual(len(folders), 2)  # the download, the unpacked tree
        self.assertEqual(Path(fetched["source"]["archive"]).parent, folders[0])
        self.assertEqual(Path(fetched["root"]).parent, folders[1])
        code, out, err = fx.run("cleanup", "--path", *map(str, folders))
        self.assertEqual(code, 0, err)
        self.assertFalse(any(p.exists() for p in folders))

    def test_a_folder_source_makes_no_fetch_folder(self):
        code, out, err = fx.run("fetch", "--instance", str(self.base), "--source",
                                str(self.source()), *fx.CONSENT)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["temp_folders"], [])


class NoGitCommitTest(TempFolderCase):
    git = False

    def test_commit_reports_the_backup_then_deletes_the_plan_folder(self):
        plan, _ = self.plan()
        self.assertEqual(self.apply(plan)[0], 0)
        code, out, err = self.commit(plan)
        self.assertEqual(code, 0, err)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("Not a git repository: nothing to commit. Backup: "))
        self.assertIn("Deleted the plan's temporary folder", lines[-1])
        self.assertFalse(plan.parent.exists())
        self.assertTrue(Path(lines[0].split("Backup: ", 1)[1]).is_dir())


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()

    def tearDown(self):
        self.tmp.cleanup()

    def cleanup(self, *folders):
        return fx.run("cleanup", "--path", *map(str, folders))

    def own(self) -> Path:
        folder = sources.private_dir("test")
        (folder / "a" / "b").mkdir(parents=True)
        (folder / "a" / "b" / "file.txt").write_text("x\n", encoding="utf-8")
        return folder

    def test_deletes_its_own_folders_and_names_gone_ones(self):
        one, two = self.own(), self.own()
        code, out, err = self.cleanup(one, two)
        self.assertEqual(code, 0, err)
        self.assertFalse(one.exists() or two.exists())
        code, out, err = self.cleanup(one)
        self.assertEqual(code, 0, err)
        self.assertIn(f"Already gone: {one}", out)

    def assert_refused(self, folder: Path, why: str):
        good = self.own()
        code, out, err = self.cleanup(good, folder)
        self.assertEqual(code, 1, out)
        self.assertIn(str(folder), err)
        self.assertIn(why, err)
        self.assertIn("Nothing was deleted", err)
        self.assertTrue((good / "a" / "b" / "file.txt").is_file())  # nothing, not even good
        self.cleanup(good)

    def test_refuses_a_folder_outside_the_temp_directory(self):
        inside_base = self.tmp.path / "kb" / "kb-upgrade-notes"
        inside_base.mkdir(parents=True)
        (inside_base / "note.md").write_text("mine\n", encoding="utf-8")
        self.assert_refused(inside_base, "not directly in the temp directory")
        self.assertTrue((inside_base / "note.md").is_file())

    def test_refuses_a_deeper_folder_of_the_temp_directory(self):
        nested = self.own() / "kb-upgrade-nested"
        nested.mkdir()
        self.assert_refused(nested, "not directly in the temp directory")
        self.cleanup(nested.parent)

    def test_refuses_a_wrong_prefix(self):
        other = Path(tempfile.mkdtemp(prefix="someone-else-"))
        try:
            self.assert_refused(other, "does not start with kb-upgrade-")
            self.assertTrue(other.is_dir())
        finally:
            other.rmdir()

    def test_refuses_a_file(self):
        fd, name = tempfile.mkstemp(prefix=sources.TEMP_PREFIX)
        os.close(fd)
        try:
            self.assert_refused(Path(name), "not a folder")
            self.assertTrue(Path(name).is_file())
        finally:
            os.unlink(name)

    def link(self, link: Path, target: Path, junction: bool):
        try:
            if junction:
                import _winapi
                _winapi.CreateJunction(str(target), str(link))
            else:
                os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError, ImportError) as e:
            self.skipTest(f"this system does not let the test create a link ({e})")

    def assert_link_refused(self, junction: bool):
        notes = self.tmp.path / "notes"
        notes.mkdir()
        (notes / "note.md").write_text("mine\n", encoding="utf-8")
        link = Path(tempfile.gettempdir()) / f"{sources.TEMP_PREFIX}link{int(junction)}"
        self.link(link, notes, junction)
        try:
            self.assert_refused(link, "link or junction")
            self.assertTrue((notes / "note.md").is_file())
        finally:
            os.rmdir(link) if junction else os.unlink(link)

    def test_refuses_a_symbolic_link(self):
        self.assert_link_refused(junction=False)

    @unittest.skipUnless(os.name == "nt", "junctions exist only on Windows")
    def test_refuses_a_junction(self):
        self.assert_link_refused(junction=True)

    def test_a_short_or_relative_spelling_of_the_temp_directory_counts(self):
        # The temp directory as a relative path (and, on Windows, possibly in its 8.3
        # form): the parent is resolved before it is compared.
        folder = self.own()
        cwd = os.getcwd()
        os.chdir(folder.parent)
        try:
            code, out, err = self.cleanup(Path(folder.name))
        finally:
            os.chdir(cwd)
        self.assertEqual(code, 0, err)
        self.assertFalse(folder.exists())


def fx_offline(url):
    import urllib.error
    raise urllib.error.URLError("offline in tests")


# No test may leave a kb-upgrade-* folder in the temp directory (fixtures.py).
tearDownModule = fx.tear_down_module


if __name__ == "__main__":
    unittest.main()
