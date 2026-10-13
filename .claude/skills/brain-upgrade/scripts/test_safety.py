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
          ".git/config", "a:stream"]


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
        for path in ("../outside.txt", "content/REFERENCE/Example.md", "README.md"):
            with self.subTest(path=path):
                code, out, err = self.plan(self.source(changes={".claude/hooks/hook.py": "v2\n"}))
                self.assertEqual(code, 0, err)
                self.tamper(path)
                before = snapshot(self.base)
                code, out, err = self.apply()
                self.assertEqual(code, 1)
                self.assertEqual(snapshot(self.base), before)
                self.assertFalse((self.tmp.path / "outside.txt").exists())

    def test_link_out_of_the_base_refused(self):
        outside = self.tmp.path / "elsewhere"
        outside.mkdir()
        link = self.base / ".claude" / "linked"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("cannot create a directory symlink here")
        fx.git(self.base, "add", "-A")
        fx.git(self.base, "commit", "-q", "-m", "link")
        code, out, err = self.plan(self.source(changes={".claude/linked/x.md": "x\n"}))
        self.assertEqual(code, 0, err)
        code, out, err = self.apply()
        self.assertEqual(code, 1)
        self.assertIn("outside the base", err)
        self.assertEqual(list(outside.iterdir()), [])


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
        self.assertEqual(order[-1], kt.STAMP)


if __name__ == "__main__":
    unittest.main()
