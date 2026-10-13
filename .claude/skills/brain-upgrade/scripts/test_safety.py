#!/usr/bin/env python3
"""Safety tests for brain-upgrade: untrusted paths (stamp, manifest, index, plan),
case-insensitive collisions, and the all-or-nothing apply. Run: python -m unittest -v"""

import json
import os
import unittest
from pathlib import Path
from unittest import mock

import fixtures as fx
import kbtemplate as kt
import sources
import upgrade
from test_planner import V2, make_instance

UNSAFE = ["../../outside.txt", "/etc/outside.txt", "C:/outside.txt", "C:outside.txt",
          "//server/share/outside.txt", ".claude\\hooks\\hook.py", ".claude/./hooks/hook.py",
          "a/../../outside.txt", ".claude/hooks./hook.py", ".claude/hooks /hook.py",
          ".git/config", "a:stream", "GIT~1/config", "CONTEN~1/notes.md", "content/NUL",
          ".claude/aux.md", ".claude/COM1.txt", ".claude/a|b.md", ".claude/a?b.md"]


def snapshot(root: Path) -> tuple[dict, set]:
    files, dirs = {}, set()
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if rel.parts[0] == ".git":
            continue
        if p.is_dir():
            dirs.add(rel.as_posix())
        else:
            files[rel.as_posix()] = p.read_bytes()
    return files, dirs


class SafetyCase(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()
        self.base = make_instance(self.tmp.path / "kb")
        self.planfile = self.tmp.path / "plan.json"
        self.n = 0

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, version="0.3.0", changes=None, manifest=None) -> Path:
        self.n += 1
        files = fx.template(version, changes)
        if manifest is not None:
            files[".kb-manifest.json"] = json.dumps(manifest).encode()
        return fx.write_tree(self.tmp.path / f"src{self.n}", files)

    def plan(self, src, *extra):
        return fx.run("plan", "--instance", str(self.base), "--source", str(src),
                      "--out", str(self.planfile), *extra)

    def apply(self, decisions=None):
        d = self.tmp.path / "decisions.json"
        d.write_text(json.dumps(decisions or {}), encoding="utf-8")
        return fx.run("apply", "--plan", str(self.planfile), "--decisions", str(d))

    def edit_stamp(self, fn):
        path = self.base / kt.STAMP
        stamp = json.loads(path.read_text(encoding="utf-8"))
        fn(stamp)
        path.write_text(json.dumps(stamp), encoding="utf-8")


class PathRuleTest(unittest.TestCase):
    def test_unsafe_paths_rejected(self):
        for p in UNSAFE + ["", "x/", "a\0b"]:
            self.assertIsNotNone(kt.path_problem(p), p)

    def test_ordinary_paths_accepted(self):
        for p in (".claude/skills/a/SKILL.md", ".gitignore", "content/WRITING_STYLE.md",
                  ".github/workflows/kb.yml"):
            self.assertIsNone(kt.path_problem(p), p)

    def test_protected(self):
        for p in ("README.md", "readme.md", "content/x.md", "Content/X.md", kt.STAMP,
                  kt.ONBOARD_VALUES, ".kb-upgrade-backup/0.2.0-x/schema.yml"):
            self.assertTrue(kt.protected(p), p)
        self.assertFalse(kt.protected("schema.yml"))

    def test_unicode_normal_forms_collide(self):
        composed, decomposed = "café.md", "café.md"
        self.assertTrue(kt.case_collisions([composed, decomposed]))
        self.assertTrue(kt.protected("CONTENT/x.md"))

    def test_collisions(self):
        self.assertTrue(kt.case_collisions(["a/SKILL.md", "A/skill.md"]))
        self.assertTrue(kt.case_collisions(["a", "A/b"]))
        self.assertFalse(kt.case_collisions(["a/b", "a/c"]))


class StampPathTest(SafetyCase):
    def test_unsafe_stamp_keys_refused_before_planning(self):
        outside = self.tmp.path / "outside.txt"
        outside.write_text("keep me\n", encoding="utf-8")
        h = kt.content_hash(outside.read_bytes())
        src = self.source()
        for key in UNSAFE:
            with self.subTest(key=key):
                original = (self.base / kt.STAMP).read_bytes()
                self.edit_stamp(lambda s: s["files"].__setitem__(key, h))
                before = snapshot(self.base)
                code, out, err = self.plan(src)
                self.assertEqual(code, 1, out)
                self.assertIn("unsafe path", err)
                self.assertEqual(snapshot(self.base), before)
                self.assertTrue(outside.is_file())
                (self.base / kt.STAMP).write_bytes(original)

    def test_protected_stamp_key_refused(self):
        self.edit_stamp(lambda s: s["files"].__setitem__(
            "content/REFERENCE/Example.md", kt.content_hash(b"# Example\n")))
        code, out, err = self.plan(self.source())
        self.assertEqual(code, 1)
        self.assertIn("belong to the base", err)

    def test_case_twins_in_stamp_refused(self):
        def twin(s):
            s["files"][".CLAUDE/hooks/hook.py"] = s["files"][".claude/hooks/hook.py"]
        self.edit_stamp(twin)
        code, out, err = self.plan(self.source())
        self.assertEqual(code, 1)
        self.assertIn("same file on Windows", err)


class ManifestPathTest(SafetyCase):
    def manifest(self, **classes):
        m = json.loads(fx.manifest("0.3.0"))
        m["classes"].update(classes)
        return m

    def test_rendered_output_outside_the_base(self):
        rendered = {**fx.CLASSES["rendered"], "../evil.md": "AGENTS.template.md"}
        code, out, err = self.plan(self.source(manifest=self.manifest(rendered=rendered)))
        self.assertEqual(code, 1)
        self.assertIn("unsafe path", err)

    def test_rendered_output_into_notes(self):
        rendered = {"README.md": "AGENTS.template.md"}
        code, out, err = self.plan(self.source(manifest=self.manifest(rendered=rendered)))
        self.assertEqual(code, 1)
        self.assertIn("belongs to the base", err)

    def test_traversal_pattern(self):
        code, out, err = self.plan(self.source(manifest=self.manifest(
            owned=fx.CLASSES["owned"] + ["../**"])))
        self.assertEqual(code, 1)
        self.assertIn("unsafe pattern", err)

    def test_notes_reclassified_as_owned(self):
        before = snapshot(self.base)
        src = self.source(changes={"content/REFERENCE/Example.md": "# overwritten\n",
                                   "README.md": "# overwritten\n"},
                          manifest=self.manifest(owned=["content/**", "README.md"] + fx.CLASSES["owned"]))
        code, out, err = self.plan(src)
        self.assertEqual(code, 1)
        self.assertIn("always belong to the base", err)
        self.assertEqual(snapshot(self.base), before)

    def test_notes_reclassified_as_author_leftovers(self):
        src = self.source(manifest=self.manifest(author=fx.CLASSES["author"] + ["content/**"]))
        code, out, err = self.plan(src)
        self.assertEqual(code, 1)
        self.assertIn("(author-delete)", err)

    def test_index_with_unsafe_path(self):
        index = {"format": 1, "states": [{"commit": None, "date": "x", "release": None, "in": []}],
                 "files": {"../outside.txt": {"sha256:00": [0]}}}
        code, out, err = self.plan(self.source(changes={kt.INDEX: json.dumps(index)}))
        self.assertEqual(code, 1)
        self.assertIn("unsafe path", err)


class ArchiveCollisionTest(SafetyCase):
    def zip(self, extra: dict) -> Path:
        z = self.tmp.path / f"bad{self.n}.zip"
        self.n += 1
        z.write_bytes(fx.zip_bytes({**fx.template("0.3.0"), **{k: v.encode() for k, v in extra.items()}}))
        return z

    def test_case_twins_in_archive(self):
        z = self.zip({".CLAUDE/skills/demo/SKILL.md": "twin\n"})
        with self.assertRaises(kt.TemplateError) as cm:
            sources.resolve(str(z))
        self.assertIn("same file on Windows", str(cm.exception))

    def test_trailing_dot_and_space(self):
        for name in (".claude/skills/demo./SKILL.md", ".claude/skills/demo /SKILL.md"):
            with self.subTest(name=name), self.assertRaises(kt.TemplateError):
                sources.resolve(str(self.zip({name: "alias\n"})))

    def test_file_and_folder_twins(self):
        with self.assertRaises(kt.TemplateError):
            sources.resolve(str(self.zip({"LICENSE/extra.txt": "x\n"})))

    def test_plan_refuses_and_writes_nothing(self):
        before = snapshot(self.base)
        code, out, err = self.plan(self.zip({".CLAUDE/hooks/hook.py": "twin\n"}))
        self.assertEqual(code, 1)
        self.assertEqual(snapshot(self.base), before)


class ApplyGuardTest(SafetyCase):
    def tamper(self, path):
        plan = json.loads(self.planfile.read_text(encoding="utf-8"))
        a = next(a for a in plan["actions"] if a["kind"] == "update")
        a["path"] = path
        self.planfile.write_text(json.dumps(plan), encoding="utf-8")

    def test_tampered_plan_paths_refused(self):
        for path in ("../outside.txt", "content/REFERENCE/Example.md", "README.md",
                     kt.STAMP, kt.ONBOARD_VALUES, "CONTEN~1/x.md"):
            with self.subTest(path=path):
                code, out, err = self.plan(self.source(changes={".claude/hooks/hook.py": "v2\n"}))
                self.assertEqual(code, 0, err)
                self.tamper(path)
                before = snapshot(self.base)
                code, out, err = self.apply()
                self.assertEqual(code, 1)
                self.assertEqual(snapshot(self.base), before)
                self.assertFalse((self.tmp.path / "outside.txt").exists())

    def link_folder(self, link: Path, target: Path):
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"this system does not let the test create a symlink ({e})")

    def test_link_out_of_the_base_refused(self):
        outside = self.tmp.path / "elsewhere"
        outside.mkdir()
        src = self.source(changes={".claude/linked/x.md": "x\n"})
        # A link that is there at the dry run stops the dry run ...
        self.link_folder(self.base / ".claude" / "linked", outside)
        code, out, err = self.plan(src)
        self.assertEqual(code, 1)
        self.assertIn("link or junction", err)
        # ... and one planted after it stops apply.
        try:
            (self.base / ".claude" / "linked").unlink()
        except OSError:  # a folder link on Windows
            os.rmdir(self.base / ".claude" / "linked")
        code, out, err = self.plan(src)
        self.assertEqual(code, 0, err)
        self.link_folder(self.base / ".claude" / "linked", outside)
        code, out, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("link or junction", err)
        self.assertEqual(list(outside.iterdir()), [])

    def test_link_inside_the_base_into_notes_refused(self):
        src = self.source(changes={".claude/notes/x.md": "x\n"})
        code, out, err = self.plan(src)
        self.assertEqual(code, 0, err)
        self.link_folder(self.base / ".claude" / "notes", self.base / "content")
        before = snapshot(self.base)
        code, out, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("link or junction", err)
        self.assertFalse((self.base / "content" / "x.md").exists())
        self.assertEqual(snapshot(self.base)[0], before[0])
        code, out, err = self.plan(src)
        self.assertEqual(code, 1)
        self.assertIn("link or junction", err)

    def test_no_git_backup_waits_for_the_checks(self):
        plain = make_instance(self.tmp.path / "plain", git=False)
        self.base = plain
        code, out, err = self.plan(self.source(changes={".claude/hooks/hook.py": "v2\n"}))
        self.assertEqual(code, 0, err)
        self.tamper("../outside.txt")
        code, out, err = self.apply()
        self.assertEqual(code, 1)
        self.assertFalse((plain / kt.BACKUP_DIR).exists())


class LinkTest(SafetyCase):
    """A template path that is, or sits under, a link must stop the dry run already."""
    HOOK = ".claude/hooks/hook.py"
    HOOK_V1 = "print('hook v1')\n"

    def symlink(self, link: Path, target: Path, is_dir=False):
        if link.exists() or link.is_symlink():
            if link.is_dir() and not link.is_symlink():
                import shutil
                shutil.rmtree(link)
            else:
                link.unlink()
        try:
            os.symlink(target, link, target_is_directory=is_dir)
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"this system does not let the test create a symlink ({e})")

    def assert_dry_run_refuses(self, protected_file: Path):
        before = protected_file.read_bytes()
        code, out, err = self.plan(self.source(changes={self.HOOK: "print('hook v2')\n"}))
        self.assertEqual(code, 1, out)
        self.assertIn("link or junction", err)
        self.assertEqual(protected_file.read_bytes(), before)
        self.assertFalse(self.planfile.exists())

    def test_owned_file_linked_to_a_note(self):
        note = self.base / "content" / "important.md"
        note.write_text(self.HOOK_V1, encoding="utf-8")  # same bytes: it looks pristine
        self.symlink(self.base / self.HOOK, note)
        self.assert_dry_run_refuses(note)

    def test_owned_folder_linked_into_notes(self):
        folder = self.base / "content" / "hooks-copy"
        folder.mkdir()
        (folder / "hook.py").write_text(self.HOOK_V1, encoding="utf-8")
        self.symlink(self.base / ".claude" / "hooks", folder, is_dir=True)
        self.assert_dry_run_refuses(folder / "hook.py")

    def test_owned_file_linked_to_readme(self):
        self.symlink(self.base / self.HOOK, self.base / "README.md")
        self.assert_dry_run_refuses(self.base / "README.md")

    def test_owned_file_linked_to_a_file_outside_the_manifest(self):
        mine = self.base / "my-own" / "skill.md"
        mine.parent.mkdir()
        mine.write_text(self.HOOK_V1, encoding="utf-8")
        self.symlink(self.base / self.HOOK, mine)
        self.assert_dry_run_refuses(mine)

    @unittest.skipUnless(os.name == "nt", "junctions exist only on Windows")
    def test_owned_folder_through_a_junction(self):
        import _winapi
        import shutil
        folder = self.base / "content" / "hooks-copy"
        folder.mkdir()
        (folder / "hook.py").write_text(self.HOOK_V1, encoding="utf-8")
        shutil.rmtree(self.base / ".claude" / "hooks")
        _winapi.CreateJunction(str(folder), str(self.base / ".claude" / "hooks"))
        self.assert_dry_run_refuses(folder / "hook.py")

    def test_link_planted_after_the_dry_run(self):
        code, out, err = self.plan(self.source(changes={self.HOOK: "print('hook v2')\n"}))
        self.assertEqual(code, 0, err)
        note = self.base / "content" / "important.md"
        note.write_text(self.HOOK_V1, encoding="utf-8")
        self.symlink(self.base / self.HOOK, note)  # same content: the stale check passes
        code, out, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("link or junction", err)
        self.assertEqual(note.read_text(encoding="utf-8"), self.HOOK_V1)


class DirtyBookkeepingTest(SafetyCase):
    def test_uncommitted_stamp_is_not_overwritten(self):
        for staged in (False, True):
            with self.subTest(staged=staged):
                self.base = make_instance(self.tmp.path / f"kb-stamp-{staged}")
                stamp = self.base / kt.STAMP
                stamp.write_text(json.dumps(json.loads(stamp.read_text(encoding="utf-8")),
                                            indent=4), encoding="utf-8")  # same data, edited
                if staged:
                    fx.git(self.base, "add", kt.STAMP)
                code, out, err = self.plan(self.source(changes={".claude/hooks/hook.py": "v2\n"}))
                self.assertEqual(code, 0, err)
                self.assertIn("uncommitted changes in planned paths", out)
                before = snapshot(self.base)
                code, out, err = self.apply()
                self.assertEqual(code, 1)
                self.assertIn(kt.STAMP, err)
                self.assertEqual(snapshot(self.base), before)

    NEW_KEY = {"AGENTS.template.md": "# {{KB_NAME}}\n\n{{NEW_KEY}}\n"}

    def test_uncommitted_render_inputs_are_not_overwritten(self):
        for staged in (False, True):
            with self.subTest(staged=staged):
                self.base = make_instance(self.tmp.path / f"kb-values-{staged}")
                values = self.base / kt.ONBOARD_VALUES
                data = json.loads(values.read_text(encoding="utf-8"))
                data["KB_OWNER"] = "edited, not committed"
                values.write_text(json.dumps(data), encoding="utf-8")
                if staged:
                    fx.git(self.base, "add", kt.ONBOARD_VALUES)
                code, out, err = self.plan(self.source(changes=self.NEW_KEY), "--rerender")
                self.assertEqual(code, 0, err)
                before = snapshot(self.base)
                code, out, err = self.apply({"values": {"NEW_KEY": "answer"}})
                self.assertEqual(code, 1)
                self.assertIn(kt.ONBOARD_VALUES, err)
                self.assertEqual(snapshot(self.base), before)

    def test_untracked_render_inputs_of_an_old_base_are_fine(self):
        fx.git(self.base, "rm", "-q", "--cached", kt.ONBOARD_VALUES)
        fx.git(self.base, "commit", "-q", "-m", "as bases before 0.2.0 had it")
        code, out, err = self.plan(self.source(changes=self.NEW_KEY), "--rerender")
        self.assertEqual(code, 0, err)
        code, out, err = self.apply({"values": {"NEW_KEY": "answer"}})
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads((self.base / kt.ONBOARD_VALUES).read_text(
            encoding="utf-8"))["NEW_KEY"], "answer")


class RaceTest(SafetyCase):
    """Something changes a checked target after resolve_mutations() and before (or
    between) the writes. Apply must notice at that step, put everything back, and write
    nothing anywhere."""
    CHANGES = {".claude/hooks/hook.py": "print('hook v2')\n",
               ".claude/skills/new/a.md": "a\n", ".claude/skills/new/b.md": "b\n",
               ".claude/skills/demo/scripts/tool.py": None}

    def setUp(self):
        super().setUp()
        code, out, err = self.plan(self.source(changes=self.CHANGES))
        self.assertEqual(code, 0, err)
        self.outside = self.tmp.path / "outside"
        self.outside.mkdir()
        self.before = snapshot(self.base)

    def swap_for_link(self, rel: str, junction=False):
        import shutil
        path = self.base / rel
        shutil.rmtree(path)
        try:
            if junction:
                import _winapi
                _winapi.CreateJunction(str(self.outside), str(path))
            else:
                os.symlink(self.outside, path, target_is_directory=True)
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"this system does not let the test create a link ({e})")

    def after_resolution(self, sabotage):
        """Strike after every check before the transaction (resolve_mutations, the git
        check, the backup), right as the transaction starts."""
        real = upgrade.transaction

        def wrapper(*a, **k):
            sabotage()
            self.sabotaged = snapshot(self.base)
            return real(*a, **k)
        with mock.patch.object(upgrade, "transaction", wrapper):
            return self.apply()

    def after_writes(self, n, sabotage):
        real, calls = upgrade._write, {"n": 0}

        def wrapper(path, data):
            real(path, data)
            calls["n"] += 1
            if calls["n"] == n:
                sabotage()
        with mock.patch.object(upgrade, "_write", wrapper):
            return self.apply()

    def assert_stopped(self, result):
        code, out, err = result
        self.assertEqual(code, 1, out)
        self.assertIn("Nothing was changed", err)
        self.assertEqual(list(self.outside.iterdir()), [])
        plan = json.loads(self.planfile.read_text(encoding="utf-8"))
        self.assertNotIn("applied", plan)

    def test_content_changed_after_the_checks(self):
        hook = self.base / ".claude/hooks/hook.py"
        result = self.after_resolution(lambda: hook.write_text("print('racing edit')\n", encoding="utf-8"))
        self.assert_stopped(result)
        self.assertIn("changed while the update was running", result[2])
        self.assertEqual(snapshot(self.base), self.sabotaged)

    def test_content_changed_between_two_writes(self):
        manifest = self.base / ".kb-manifest.json"
        racing = b'{"edited": "while apply ran"}\n'
        result = self.after_writes(1, lambda: manifest.write_bytes(racing))
        self.assert_stopped(result)
        files, dirs = self.before
        self.assertEqual(snapshot(self.base), ({**files, ".kb-manifest.json": racing}, dirs))

    def test_parent_swapped_for_a_symlink_after_the_checks(self):
        (self.outside / "hook.py").write_text("print('hook v1')\n", encoding="utf-8")
        result = self.after_resolution(lambda: self.swap_for_link(".claude/hooks"))
        code, out, err = result
        self.assertEqual(code, 1, out)
        self.assertIn("link or junction", err)
        self.assertEqual((self.outside / "hook.py").read_text(encoding="utf-8"), "print('hook v1')\n")
        self.assertEqual([p.name for p in self.outside.iterdir()], ["hook.py"])
        self.assertEqual(snapshot(self.base), self.sabotaged)

    @unittest.skipUnless(os.name == "nt", "junctions exist only on Windows")
    def test_parent_swapped_for_a_junction_after_the_checks(self):
        result = self.after_resolution(lambda: self.swap_for_link(".claude/skills/demo", junction=True))
        self.assert_stopped(result)
        self.assertEqual(snapshot(self.base), self.sabotaged)

    def test_created_folder_swapped_for_a_link_between_writes(self):
        # Write 1 is the hook, write 2 creates .claude/skills/new/ for a.md; then the new
        # folder becomes a link out of the base before b.md is written into it.
        result = self.after_writes(2, lambda: self.swap_for_link(".claude/skills/new"))
        code, out, err = result
        self.assertEqual(code, 1, out)
        self.assertIn("link or junction", err)
        self.assertEqual(list(self.outside.iterdir()), [])
        self.assertEqual((self.base / ".claude/hooks/hook.py").read_bytes(),
                         self.before[0][".claude/hooks/hook.py"])
        self.assertTrue((self.base / ".claude/skills/demo/scripts/tool.py").is_file())


class ProvenanceTest(SafetyCase):
    """R5-1 (the maintainer's decision): before any code from a source runs, the base's
    own engine says where the source comes from, and a switch of repository needs the
    owner's explicit consent."""

    def fetch(self, *args, opener=None, ok=True):
        code, out, err = fx.run("fetch", "--instance", str(self.base), *args, opener=opener)
        if not ok:
            self.assertEqual(code, 1, out)
            return err
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def other_repo_source(self):
        manifest = json.loads(fx.manifest("0.3.0"))
        manifest["repository"] = "someone/fork"
        return self.source(manifest=manifest)

    def clone(self, origin: str | None, claims: str = fx.REPO):
        repo = self.tmp.path / f"tpl{self.n}"
        self.n += 1
        fx.git_init(repo)
        manifest = json.loads(fx.manifest("0.3.0"))
        manifest["repository"] = claims
        sha = fx.commit_tree(repo, {**fx.template("0.3.0"),
                                    ".kb-manifest.json": json.dumps(manifest).encode()},
                             "release", tag="v0.3.0")
        if origin:
            fx.git(repo, "remote", "add", "origin", origin)
        return repo, sha

    def test_a_local_clone_only_claims_even_with_our_origin(self):
        # Any clone can name the template repository as its origin remote; that setting
        # proves nothing about where its commits came from.
        origin = f"https://github.com/{fx.REPO}.git"
        repo, sha = self.clone(origin, claims=fx.REPO)
        err = self.fetch("--source", str(repo), ok=False)
        self.assertIn("cannot show where it comes from", err)
        self.assertIn("is a setting of that clone, not proof", err)
        prov = self.fetch("--source", str(repo), "--allow-repository", fx.REPO)["provenance"]
        self.assertEqual(prov, {"repository": None, "claimed_repository": fx.REPO,
                                "version": "0.3.0", "tag": None, "commit": sha,
                                "from": str(repo), "origin_remote": origin, "verified": None,
                                "base_repository": fx.REPO, "same_repository": None})

    def test_consent_must_name_the_claimed_repository(self):
        repo, _ = self.clone("git@github.com:someone/fork.git", claims="someone/fork")
        self.fetch("--source", str(repo), "--allow-repository", fx.REPO, ok=False)
        out = self.fetch("--source", str(repo), "--allow-repository", "Someone/Fork")
        self.assertEqual(out["provenance"]["claimed_repository"], "someone/fork")

    def test_repository_names_ignore_case(self):
        archive = fx.zip_bytes(fx.template("0.3.0"), comment="f" * 40)
        out = self.fetch("--repo", fx.REPO.upper(), "--to", "0.3.0", opener=lambda url: archive)
        self.assertIs(out["provenance"]["same_repository"], True)

    def test_fetch_reports_a_download(self):
        archive = fx.zip_bytes(fx.template("0.3.0"), comment="c" * 40)
        out = self.fetch("--to", "0.3.0", opener=lambda url: archive)
        prov = out["provenance"]
        self.assertEqual((prov["tag"], prov["commit"], prov["same_repository"]),
                         ("v0.3.0", "c" * 40, True))
        self.assertEqual(prov["from"], f"https://github.com/{fx.REPO}/archive/refs/tags/v0.3.0.zip")
        self.assertIn(f"over HTTPS from github.com/{fx.REPO}", prov["verified"])
        self.assertEqual(out["warnings"], [])
        self.assertTrue(out["engine"].endswith("upgrade.py"))

    def test_folder_or_zip_only_claims(self):
        folder = str(self.source())
        # Claiming to be the base's own repository is not enough: nothing proves it.
        err = self.fetch("--source", folder, ok=False)
        self.assertIn(f"--allow-repository {fx.REPO}", err)
        prov = self.fetch("--source", folder, "--allow-repository", fx.REPO)["provenance"]
        self.assertEqual((prov["repository"], prov["claimed_repository"], prov["commit"],
                          prov["tag"], prov["verified"], prov["same_repository"]),
                         (None, fx.REPO, "unknown", None, None, None))
        z = self.tmp.path / "claims.zip"
        z.write_bytes(fx.zip_bytes(fx.template("0.3.0"), comment="d" * 40))
        out = self.fetch("--source", str(z), "--allow-repository", fx.REPO)
        # A zip comment is the archive's own word: shown, but not verified, and no tag.
        self.assertEqual((out["provenance"]["commit"], out["provenance"]["tag"],
                          out["provenance"]["verified"]), ("d" * 40, None, None))
        self.assertTrue(any("nothing here proves either" in w for w in out["warnings"]))

    def test_download_from_another_repository_is_judged_by_its_url(self):
        # The fork's archive claims to be ours; what counts is where it was downloaded from.
        archive = fx.zip_bytes(fx.template("0.3.0"), comment="e" * 40)
        args = ("--repo", "someone/fork", "--to", "0.3.0")
        err = self.fetch(*args, opener=lambda url: archive, ok=False)
        self.assertIn("--allow-repository someone/fork", err)
        out = self.fetch(*args, "--allow-repository", "someone/fork", opener=lambda url: archive)
        prov = out["provenance"]
        self.assertEqual((prov["repository"], prov["claimed_repository"], prov["same_repository"]),
                         ("someone/fork", fx.REPO, False))
        self.assertTrue(any("says it is" in w for w in out["warnings"]))

    def test_other_repository_needs_consent_before_it_is_unpacked(self):
        src = self.other_repo_source()
        err = self.fetch("--source", str(src), ok=False)
        self.assertIn("Nothing was run or changed", err)
        self.assertIn("--allow-repository someone/fork", err)
        out = self.fetch("--source", str(src), "--allow-repository", "someone/fork")
        self.assertEqual(out["provenance"]["claimed_repository"], "someone/fork")
        self.assertTrue(any("someone/fork" in w for w in out["warnings"]))

    def test_plan_refuses_another_repository_without_consent(self):
        src = self.other_repo_source()
        before = snapshot(self.base)
        code, out, err = self.plan(src)
        self.assertEqual(code, 1)
        self.assertIn("--allow-repository someone/fork", err)
        self.assertEqual(snapshot(self.base), before)
        self.assertFalse(self.planfile.exists())
        code, out, err = self.plan(src, "--allow-repository", "someone/other")
        self.assertEqual(code, 1)
        code, out, err = self.plan(src, "--allow-repository", "someone/fork")
        self.assertEqual(code, 0, err)
        self.assertIn("repository someone/fork", out)


class CommitGuardTest(SafetyCase):
    """R6-1: commit takes only what apply left, read once and committed as read."""
    CHANGES = {".claude/hooks/hook.py": "print('hook v2')\n",
               ".claude/skills/demo/scripts/tool.py": None}
    HOOK, TOOL = ".claude/hooks/hook.py", ".claude/skills/demo/scripts/tool.py"

    def setUp(self):
        super().setUp()
        code, out, err = self.plan(self.source(changes=self.CHANGES))
        self.assertEqual(code, 0, err)
        code, out, err = self.apply()
        self.assertEqual(code, 0, err)

    def git_state(self):
        return (fx.git(self.base, "rev-parse", "HEAD"), fx.git(self.base, "write-tree"),
                fx.git(self.base, "status", "--porcelain"))

    def commit(self):
        return fx.run("commit", "--plan", str(self.planfile))

    def assert_refused(self, *paths):
        before = self.git_state()
        code, out, err = self.commit()
        self.assertEqual(code, 1, out)
        self.assertIn("changed after apply", err)
        for p in paths:
            self.assertIn(p, err)
        self.assertEqual(self.git_state(), before)  # no commit, index untouched

    def test_applied_write_edited_before_commit(self):
        (self.base / self.HOOK).write_text("print('edited by a sync client')\n", encoding="utf-8")
        self.assert_refused(self.HOOK)

    def test_applied_delete_restored_before_commit(self):
        (self.base / self.TOOL).parent.mkdir(parents=True, exist_ok=True)  # as a sync client would
        (self.base / self.TOOL).write_text("print('tool v1')\n", encoding="utf-8")
        self.assert_refused(self.TOOL)

    def test_edited_stamp_before_commit(self):
        stamp = self.base / kt.STAMP
        stamp.write_text(stamp.read_text(encoding="utf-8") + " ", encoding="utf-8")
        self.assert_refused(kt.STAMP)

    def test_change_between_the_checks_and_the_commit(self):
        real = upgrade.build_commit_index

        def racing(instance, index, contents):
            result = real(instance, index, contents)
            (self.base / self.HOOK).write_text("print('late edit')\n", encoding="utf-8")
            return result
        before = self.git_state()
        with mock.patch.object(upgrade, "build_commit_index", racing):
            code, out, err = self.commit()
        self.assertEqual(code, 1, out)
        self.assertIn("changed after apply", err)
        self.assertEqual(self.git_state()[:2], before[:2])

    def test_commit_holds_exactly_what_apply_left(self):
        code, out, err = self.commit()
        self.assertEqual(code, 0, err)
        self.assertEqual(fx.git(self.base, "show", f"HEAD:{self.HOOK}"), "print('hook v2')")
        names = set(fx.git(self.base, "show", "--name-only", "--format=", "HEAD").splitlines())
        self.assertIn(self.TOOL, names)
        self.assertEqual(fx.git(self.base, "status", "--porcelain"), "")


class RollbackTest(SafetyCase):
    CHANGES = {".claude/hooks/hook.py": "print('hook v2')\n",                 # update
               ".claude/skills/new/deep/SKILL.md": "new\n",                    # add, new folders
               ".claude/skills/demo/scripts/tool.py": None,                    # delete
               "AGENTS.template.md": "# {{KB_NAME}}\n\n{{NEW_KEY}}\n"}         # re-render
    DECISIONS = {"rerender": ["AGENTS.md"], "values": {"NEW_KEY": "answer"}}  # + values

    def run_with_fault(self, fail_at: int | None):
        calls = {"n": 0}
        real_write, real_unlink = upgrade._write, upgrade._unlink

        def counted(fn):
            def inner(*a, **k):
                calls["n"] += 1
                if calls["n"] == fail_at:
                    raise OSError("injected failure")
                return fn(*a, **k)
            return inner
        with mock.patch.object(upgrade, "_write", counted(real_write)), \
                mock.patch.object(upgrade, "_unlink", counted(real_unlink)):
            result = self.apply(self.DECISIONS)
        return result, calls["n"]

    def fresh(self, i):
        self.base = make_instance(self.tmp.path / f"kb{i}")
        code, out, err = self.plan(self.source(changes=self.CHANGES))
        self.assertEqual(code, 0, err)

    def test_a_failure_at_any_step_restores_the_base(self):
        self.fresh(0)
        (code, out, err), total = self.run_with_fault(None)
        self.assertEqual(code, 0, err)
        self.assertGreaterEqual(total, 6)  # update, add, delete, re-render, values, stamp
        for i in range(1, total + 1):
            with self.subTest(step=i):
                self.fresh(i)
                before = snapshot(self.base)
                (code, out, err), _ = self.run_with_fault(i)
                self.assertEqual(code, 1)
                self.assertIn("rolled back", err)
                self.assertEqual(snapshot(self.base), before)
                plan = json.loads(self.planfile.read_text(encoding="utf-8"))
                self.assertNotIn("applied", plan)

    def test_stamp_is_written_last(self):
        self.fresh(0)
        order = []
        real_write = upgrade._write

        def record(path, data):
            order.append(Path(path).name)
            return real_write(path, data)
        with mock.patch.object(upgrade, "_write", record):
            code, out, err = self.apply(self.DECISIONS)
        self.assertEqual(code, 0, err)
        # The stamp is the last file written in the base; recording the plan as applied
        # (outside the base) is the transaction's final step.
        self.assertEqual(order[-2:], [kt.STAMP, self.planfile.name])

    def test_failing_to_record_the_plan_rolls_the_base_back(self):
        self.fresh(0)
        before = snapshot(self.base)
        with mock.patch.object(upgrade, "save_plan", side_effect=OSError("disk full")):
            code, out, err = self.apply(self.DECISIONS)
        self.assertEqual(code, 1)
        self.assertIn("recording the plan as applied", err)
        self.assertIn("rolled back", err)
        self.assertEqual(snapshot(self.base), before)
        self.assertNotIn("applied", json.loads(self.planfile.read_text(encoding="utf-8")))

    def test_rollback_keeps_a_file_changed_after_apply_wrote_it(self):
        for target, label in ((".claude/hooks/hook.py", "updated"),
                              (".claude/skills/new/deep/SKILL.md", "added")):
            with self.subTest(file=label):
                self.fresh(label)
                before = snapshot(self.base)
                state, real_write = {"fail_next": False}, upgrade._write
                edited = b"someone else's edit, made while apply ran\n"

                def racing(path, data):
                    # Apply writes the target, a sync client or an editor changes it,
                    # and the next write fails.
                    if state["fail_next"]:
                        state["fail_next"] = False  # once: the rollback may write again
                        raise OSError("injected failure")
                    real_write(path, data)
                    if Path(path) == (self.base / target).resolve():
                        Path(path).write_bytes(edited)
                        state["fail_next"] = True
                with mock.patch.object(upgrade, "_write", racing):
                    code, out, err = self.apply(self.DECISIONS)
                self.assertEqual(code, 1)
                self.assertIn("rollback is incomplete", err)
                self.assertIn(target, err)
                self.assertEqual((self.base / target).read_bytes(), edited)
                files, dirs = snapshot(self.base)
                files.pop(target)
                expected = dict(before[0])
                expected.pop(target, None)
                self.assertEqual(files, expected)
                self.assertNotIn("applied", json.loads(self.planfile.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
