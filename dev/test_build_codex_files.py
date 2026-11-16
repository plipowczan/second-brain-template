#!/usr/bin/env python3
"""Tests for dev/build_codex_files.py. Run: python -m unittest -v (from dev/).

Each test builds a small git tree of its own: a copy of the template's
`.kb-manifest.json` and fixture skills, not a copy of the repository's skills."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = HERE / "build_codex_files.py"

# Frontmatter the stub must keep line for line: a comment, a key Codex does not know, and
# a quoted ` #` that YAML must not read as a comment.
ALPHA = ("---\n"
         "name: alpha\n"
         "# a comment the stub keeps\n"
         "description: 'Use when the user says \"alpha\" or \"export #tag\". It''s quoted.'\n"
         "allowed-tools: Bash, Read\n"
         "---\n"
         "\n"
         "# Alpha\n"
         "\n"
         "Run `python .claude/skills/alpha/scripts/run.py`.\n")
BETA = ("---\n"
        "name: beta\n"
        "user-invocable: true\n"
        "description: Use when the user says \"beta\". Plain, on one line, and whole.\n"
        "---\n"
        "\n"
        "# Beta\n"
        "\n"
        "Read `references/guide.md`.\n")

# The fixed body of a stub (design D3).
BODY = ("\n"
        "This skill's instructions are in `.claude/skills/{s}/SKILL.md`. Read that file and\n"
        "follow it. Its folder, `.claude/skills/{s}/`, is this skill's base directory.\n"
        "If that file does not exist, tell the user that this skill was removed from this base,\n"
        "and stop.\n")

# `.codex/hooks.json` (design D5).
HOOKS = ('{\n'
         '  "hooks": {\n'
         '    "SessionStart": [\n'
         '      {\n'
         '        "hooks": [\n'
         '          {\n'
         '            "type": "command",\n'
         '            "command": "python .claude/hooks/load_vault_map.py"\n'
         '          }\n'
         '        ]\n'
         '      }\n'
         '    ]\n'
         '  }\n'
         '}\n')

STUB_A = ".agents/skills/alpha/SKILL.md"
STUB_B = ".agents/skills/beta/SKILL.md"
HOOKS_PATH = ".codex/hooks.json"
GAMMA = ".claude/skills/gamma/SKILL.md"


def expected_stub(source: str, skill: str) -> bytes:
    head = source.split("\n---\n", 1)[0]  # "---\n" and the frontmatter lines
    return (head + "\n---\n" + BODY.format(s=skill)).encode("utf-8")


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def snapshot(root: Path) -> dict:
    """Every folder and file under `root` outside `.git/`, with bytes and mtime."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        if here == root and ".git" in dirnames:
            dirnames.remove(".git")
        for d in dirnames:
            out[(here / d).relative_to(root).as_posix() + "/"] = None
        for f in filenames:
            p = here / f
            out[p.relative_to(root).as_posix()] = (p.read_bytes(), p.stat().st_mtime_ns)
    return out


class BuildCodexFilesTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "tree"
        self.repo.mkdir()
        shutil.copyfile(ROOT / ".kb-manifest.json", self.repo / ".kb-manifest.json")
        self.put(".claude/skills/alpha/SKILL.md", ALPHA)
        self.put(".claude/skills/alpha/scripts/run.py", "print('alpha')\n")
        self.put(".claude/skills/alpha/notes.md", "# Notes of alpha\n")
        self.put(".claude/skills/beta/SKILL.md", BETA)
        self.put(".claude/skills/beta/references/guide.md", "# Guide\n")
        self.put(".gitignore", ".venv/\n")
        git(self.repo, "init", "-q")
        git(self.repo, "add", "-A")

    def tearDown(self):
        self.tmp.cleanup()

    # --- helpers ---------------------------------------------------------------------

    def put(self, rel, text, track=False):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        if track:
            git(self.repo, "add", "--", rel)

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.repo), *args],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    def generate(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def check(self):
        return self.run_script("--check")

    def lines_naming(self, out: str, *needles) -> list[str]:
        return [ln for ln in out.splitlines() if all(n in ln for n in needles)]

    def assert_check_names(self, path):
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertTrue(self.lines_naming(r.stdout, path), r.stdout)

    def files_under(self, rel):
        base = self.repo / rel
        return sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())

    # --- write mode ------------------------------------------------------------------

    def test_stub_is_frontmatter_plus_fixed_body(self):
        self.generate()
        self.assertEqual((self.repo / STUB_A).read_bytes(), expected_stub(ALPHA, "alpha"))
        self.assertEqual((self.repo / STUB_B).read_bytes(), expected_stub(BETA, "beta"))
        # Nothing else under .agents/skills/<skill>/: no scripts, no other Markdown.
        self.assertEqual(self.files_under(".agents/skills"), ["alpha/SKILL.md", "beta/SKILL.md"])

    def test_hooks_json_is_d5(self):
        self.generate()
        self.assertEqual((self.repo / HOOKS_PATH).read_bytes(), HOOKS.encode("utf-8"))
        self.assertEqual(self.files_under(".codex"), ["hooks.json"])

    def test_second_run_changes_nothing(self):
        self.generate()
        before = snapshot(self.repo)
        self.generate()
        self.assertEqual(snapshot(self.repo), before)

    def test_check_writes_nothing(self):
        before = snapshot(self.repo)  # no Codex file at all
        self.assertEqual(self.check().returncode, 1)
        self.assertEqual(snapshot(self.repo), before)

        self.generate()
        self.put(STUB_A, "stale\n")
        (self.repo / HOOKS_PATH).unlink()
        self.put(".agents/skills/source-command-b-qa/SKILL.md", "wrapper\n")
        before = snapshot(self.repo)
        self.assertEqual(self.check().returncode, 1)
        self.assertEqual(snapshot(self.repo), before)

    def test_write_deletes_files_without_source(self):
        self.generate()
        self.put(".agents/skills/source-command-b-qa/SKILL.md", "wrapper\n", track=True)
        self.put(".agents/skills/alpha/scripts/run.py", "copy\n")
        self.put(".agents/skills/README.md", "stray\n")
        self.generate()
        self.assertFalse((self.repo / ".agents/skills/source-command-b-qa").exists())
        self.assertEqual(self.files_under(".agents/skills"), ["alpha/SKILL.md", "beta/SKILL.md"])
        self.assertEqual(self.check().returncode, 0)

    def test_write_writes_nothing_when_a_frontmatter_fails(self):
        self.put(GAMMA, "---\nname: gamma\ndescription: Says \"export #tag\" here.\n---\n",
                 track=True)
        self.put(".agents/skills/source-command-b-qa/SKILL.md", "wrapper\n")
        before = snapshot(self.repo)
        r = self.run_script()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertTrue(self.lines_naming(r.stdout, GAMMA, "description"), r.stdout)
        self.assertEqual(snapshot(self.repo), before)

    def test_write_writes_nothing_when_a_continued_description_is_cut(self):
        cases = {
            "continuation line": ("---\nname: gamma\ndescription: Use for archive requests\n"
                                  "  or export #tag requests.\n---\n"),
            "anchor": "---\nname: gamma\ndescription: &d Use for export #tag requests.\n---\n",
        }
        for case, source in cases.items():
            with self.subTest(case):
                self.put(GAMMA, source, track=True)
                before = snapshot(self.repo)
                r = self.run_script()
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertTrue(self.lines_naming(r.stdout, GAMMA, "description"), r.stdout)
                self.assertEqual(snapshot(self.repo), before)

    # --- the check: Codex files ------------------------------------------------------

    def test_generated_tree_passes(self):
        self.generate()
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_check_fails_on_stale_stub(self):
        self.generate()
        p = self.repo / STUB_A
        p.write_bytes(p.read_bytes().replace(b"alpha", b"alpha2", 1))
        self.assert_check_names(STUB_A)

    def test_check_fails_on_missing_stub(self):
        self.generate()
        (self.repo / STUB_B).unlink()
        self.assert_check_names(STUB_B)

    def test_check_fails_on_missing_hooks_json(self):
        self.generate()
        (self.repo / HOOKS_PATH).unlink()
        self.assert_check_names(HOOKS_PATH)

    def test_check_fails_on_absolute_path_in_hooks_json(self):
        self.generate()
        p = self.repo / HOOKS_PATH
        p.write_text(HOOKS.replace("python .claude", "python C:\\\\kb\\\\.claude"),
                     encoding="utf-8", newline="\n")
        self.assert_check_names(HOOKS_PATH)

    def test_check_fails_on_folder_with_no_source(self):
        self.generate()
        self.put(".agents/skills/source-command-b-qa/SKILL.md", "Use the `brain-qa` skill.\n")
        self.assert_check_names(".agents/skills/source-command-b-qa")

    def test_check_fails_on_stray_file_in_stub_folder(self):
        self.generate()
        self.put(".agents/skills/alpha/scripts/run.py", "print('copy')\n")
        self.assert_check_names(".agents/skills/alpha/scripts/run.py")

    def test_crlf_stub_is_no_difference(self):
        self.generate()
        p = self.repo / STUB_A
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_excluded_and_ignored_paths_skipped(self):
        self.generate()
        junk = [".agents/skills/__pycache__/x.cpython-313.pyc",
                ".agents/skills/alpha/__pycache__/y.pyc",
                ".agents/skills/alpha/.DS_Store",
                ".agents/skills/.DS_Store"]
        for rel in junk:
            self.put(rel, b"\0junk")
        # Git-ignored, never tracked: not a skill, and not read.
        self.put(".claude/skills/alpha/.venv/lib/pkg/README.md", b"\xff\xfe not text, no frontmatter")
        self.put(".claude/skills/alpha/.venv/SKILL.md", b"---\nname: [broken\n")
        r = self.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.generate()
        for rel in junk:
            self.assertTrue((self.repo / rel).is_file(), rel)
        self.assertFalse((self.repo / ".agents/skills/.venv").exists())

    def test_untracked_skill_gets_no_stub(self):
        self.put(".claude/skills/draft/SKILL.md", "---\nname: draft\ndescription: Not added yet.\n---\n")
        self.generate()
        self.assertFalse((self.repo / ".agents/skills/draft").exists())

    def test_link_in_a_written_path_blocks_writing(self):
        self.generate()
        shutil.rmtree(self.repo / ".agents/skills/alpha")
        try:
            os.symlink(self.repo / ".claude/skills/alpha", self.repo / ".agents/skills/alpha",
                       target_is_directory=True)
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"cannot create a symbolic link here: {e}")
        r = self.run_script()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertTrue(self.lines_naming(r.stdout, ".agents/skills/alpha"), r.stdout)
        # The stub was not written through the link over the source.
        self.assertEqual((self.repo / ".claude/skills/alpha/SKILL.md").read_text(encoding="utf-8"),
                         ALPHA)
        self.assertEqual(self.check().returncode, 1)

    # --- the check: source frontmatter -----------------------------------------------

    def assert_frontmatter_fails(self, source, field):
        self.put(GAMMA, source, track=True)
        r = self.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertTrue(self.lines_naming(r.stdout, GAMMA, field), r.stdout)

    def test_check_fails_on_bad_frontmatter(self):
        cases = {
            "no frontmatter block": ("# Gamma\n\nNo frontmatter.\n", "frontmatter"),
            "unclosed frontmatter block": ("---\nname: gamma\ndescription: Open.\n", "frontmatter"),
            "invalid YAML": ("---\nname: gamma\ndescription: Turns sources into notes "
                             "across every note they touch: shows one plan.\n---\n",
                             "description"),
            "missing name": ("---\ndescription: No name.\n---\n", "name"),
            "non-string name": ("---\nname: [gamma]\ndescription: A list name.\n---\n", "name"),
            "missing description": ("---\nname: gamma\n---\n", "description"),
            "non-string description": ("---\nname: gamma\ndescription: 42\n---\n", "description"),
            "unquoted ` #`": ("---\nname: gamma\ndescription: Use when the user says "
                              "\"export #tag\" or \"export FOLDER\".\n---\n", "description"),
            "unquoted ` #` on a continuation line": (
                "---\nname: gamma\ndescription: Use for archive requests\n"
                "  or export #tag requests.\n---\n", "description"),
            "unquoted ` #`, value starts on the next line": (
                "---\nname: gamma\ndescription:\n  Use for export #tag requests.\n---\n",
                "description"),
            "unquoted ` #` after an anchor": (
                "---\nname: gamma\ndescription: &desc Use for export #tag requests.\n---\n",
                "description"),
            "unquoted ` #` after a tag": (
                "---\nname: gamma\ndescription: !!str Use for export #tag requests.\n---\n",
                "description"),
            "unquoted ` #`, quoted key": (
                "---\nname: gamma\n\"description\": Use for export #tag requests.\n---\n",
                "description"),
            "comment line inside the value": (
                "---\nname: gamma\ndescription: Use for export\n  #tag requests.\n---\n",
                "description"),
        }
        for case, (source, field) in cases.items():
            with self.subTest(case):
                self.assert_frontmatter_fails(source, field)

    def test_whole_descriptions_pass(self):
        cases = {
            "double-quoted": '---\nname: gamma\ndescription: "Says \\"export #tag\\"."\n---\n',
            "folded block": "---\nname: gamma\ndescription: >-\n  Says export #tag,\n  on two lines.\n---\n",
            "plain on two lines": "---\nname: gamma\ndescription: Says one thing\n  and another.\n---\n",
            "plain with a blank line": "---\nname: gamma\ndescription: Says one thing\n\n  and another.\n---\n",
            "`#` with no space before it": "---\nname: gamma\ndescription: Use for C# notes.\n---\n",
            "quoted, then a comment": "---\nname: gamma\ndescription: 'Says export #tag.' # a note\n---\n",
            "CRLF source": "---\r\nname: gamma\r\ndescription: Plain.\r\n---\r\n",
        }
        for case, source in cases.items():
            with self.subTest(case):
                self.put(GAMMA, source, track=True)
                self.generate()
                r = self.check()
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
