"""Test fixtures for brain-upgrade: small template trees, git repos and instances,
all in temporary directories. Imported by the test_*.py suites (not a test itself)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import kbtemplate as kt  # noqa: E402
import sources  # noqa: E402
import upgrade  # noqa: E402


# --- the temp directory --------------------------------------------------------------
# The engine makes its folders (kb-upgrade-...) in the system temp directory. The tests
# run it against a temp directory of their own, so that a folder a test leaves behind is
# seen, and other sessions' folders in the shared one are neither seen nor touched. The
# test runners (tests/run_tests.py, tests/run_skill_tests.py) own one directory for a
# whole run and name it in KB_TEST_TEMP; run on its own (python -m unittest), a suite
# makes one here. `tempfile` caches its directory, so tempfile.tempdir is set as well as
# the variables every subprocess (git) inherits.

TEMP_VARS = ("TMP", "TEMP", "TMPDIR")


def isolate_temp() -> Path:
    given = os.environ.get("KB_TEST_TEMP")
    if given and Path(given).is_dir():
        root = given
    else:
        global _OWN_TEMP
        _OWN_TEMP = tempfile.TemporaryDirectory(prefix="brain-upgrade-tests-")
        root = _OWN_TEMP.name
    for var in TEMP_VARS + ("KB_TEST_TEMP",):
        os.environ[var] = root
    tempfile.tempdir = root
    return Path(root)


_OWN_TEMP = None
TEMP_ROOT = isolate_temp()
# Every temporary folder the engine reported in this process (plan's "Temporary folder"
# lines, fetch's temp_folders), handed to its own `cleanup` at the end of each module.
REPORTED: list[str] = []
_FOLDER_LINE = re.compile(r"^Temporary folder \([^)]*\): (.+?)\s*$", re.M)


def reported_folders(argv, code: int, out: str, err: str) -> list[str]:
    found = _FOLDER_LINE.findall(out) + _FOLDER_LINE.findall(err)
    if argv and argv[0] == "fetch" and code == 0:
        try:
            found += json.loads(out).get("temp_folders", [])
        except ValueError:
            pass
    return found


def temp_folders_of(out: str) -> dict[str, list[str]]:
    """The "Temporary folder (<purpose>): <path>" lines of one output, by purpose."""
    found: dict[str, list[str]] = {}
    for m in re.finditer(r"^Temporary folder \(([^)]*)\): (.+?)\s*$", out, re.M):
        found.setdefault(m.group(1), []).append(m.group(2))
    return found


def leftover_temp_folders() -> list[str]:
    return sorted(p.name for p in TEMP_ROOT.glob(sources.TEMP_PREFIX + "*") if p.is_dir())


def tear_down_module() -> None:
    """`tearDownModule` of every suite: the folders the engine reported go through its own
    `cleanup` (which must accept them), then no kb-upgrade-* folder may be left. One that
    is left was never reported, or was not deleted by the step that should have; it is
    swept so the next module starts clean, and the module fails."""
    folders = list(dict.fromkeys(REPORTED))
    REPORTED.clear()
    if folders:
        code, out, err = run("cleanup", "--path", *folders)
        if code != 0:
            raise AssertionError(f"cleanup refused reported folders: {err}")
    left = leftover_temp_folders()
    for name in left:
        shutil.rmtree(TEMP_ROOT / name, ignore_errors=True)
    if left:
        raise AssertionError(f"temporary folders left in {TEMP_ROOT}: {', '.join(left)}")

RENDER_PY = (HERE.parent.parent / "brain-onboard" / "scripts" / "render.py").read_bytes()

CLASSES = {
    "author": ["openspec/**", "CONTRIBUTING.md", "CLAUDE.local.md", "dev/**"],
    "rendered": {
        "CLAUDE.md": "CLAUDE.template.md",
        "AGENTS.md": "AGENTS.template.md",
        "content/WRITING_STYLE.md": "content/WRITING_STYLE.template.md",
    },
    "owned": [".claude/**", ".githooks/**", ".github/**", "tests/**", ".kb-manifest.json",
              ".gitattributes", ".gitignore", "schema.yml", "CHANGELOG.md", "LICENSE"],
    "seeded": ["content/**", "README.md"],
}
EXCLUDE = ["**/__pycache__/**", "**/*.pyc", ".claude/settings.local.json", "graft/**",
           ".kb-template.json", ".kb-onboard.json", ".kb-upgrade-backup/**"]
REPO = "example/kb-template"
# The owner's consent to a source that cannot prove its origin (a folder, a zip, a local
# clone): plan and fetch refuse such a source without it. Explicit options given after
# it in a call win, since argparse keeps the last one.
CONSENT = ("--allow-repository", REPO)
VALUES = {"KB_NAME": "Test KB", "KB_OWNER": "Owner", "PRIMARY_LANGUAGE": "English"}


def manifest(version: str, executable=()) -> str:
    data = {"format": 1, "version": version, "repository": REPO, "classes": CLASSES,
            "exclude": EXCLUDE}
    if executable:
        data["executable"] = list(executable)
    return json.dumps(data, indent=2) + "\n"


def changelog(*versions: str, unreleased: str | None = None) -> str:
    """A CHANGELOG with one Added entry per version (newest first in the arguments)."""
    out = ["# Changelog", ""]
    if unreleased:
        out += ["## [Unreleased]", "", "### Added", f"- {unreleased}", ""]
    for v in versions:
        out += [f"## [{v}] - 2026-01-01", "", "### Added", f"- feature of {v}", ""]
        if v.endswith(".0") and v != "0.1.0":
            out += ["### Changed", f"- **BREAKING: change in {v}**", ""]
    return "\n".join(out) + "\n"


def template(version: str = "0.2.0", changes: dict | None = None, executable=()) -> dict[str, bytes]:
    """A template tree; `changes` replaces files by path (value None deletes the path)."""
    files = {
        ".kb-manifest.json": manifest(version, executable),
        "CHANGELOG.md": changelog(version, "0.1.0") if version != "0.1.0" else changelog("0.1.0"),
        ".claude/skills/demo/SKILL.md": "---\nname: demo\n---\n# Demo skill v1\n",
        ".claude/skills/demo/scripts/tool.py": "print('tool v1')\n",
        ".claude/skills/brain-onboard/scripts/render.py": RENDER_PY.decode("utf-8"),
        ".claude/hooks/hook.py": "print('hook v1')\n",
        ".gitignore": "__pycache__/\n",
        "schema.yml": "types: [note]\n",
        "LICENSE": "MIT\n",
        "AGENTS.template.md": "# {{KB_NAME}}\n\nOwner: {{KB_OWNER}}\n",
        "CLAUDE.template.md": "@AGENTS.md\n",
        "content/WRITING_STYLE.template.md": "Language: {{PRIMARY_LANGUAGE}}\n",
        "content/REFERENCE/Example.md": "# Example\n",
        "content/templates/book.md": "# {{title}}\n",
        "README.md": "# Template README\n",
        "CONTRIBUTING.md": "# Contributing to the template\n",
        "openspec/config.yaml": "schema: spec-driven\n",
    }
    for path, value in (changes or {}).items():
        if value is None:
            files.pop(path, None)
        else:
            files[path] = value
    return {p: (v.encode("utf-8") if isinstance(v, str) else v) for p, v in files.items()}


def write_tree(root: Path, files: dict[str, bytes]) -> Path:
    for path, data in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr}")
    return r.stdout.strip()


def git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Test")
    git(root, "config", "core.autocrlf", "false")
    git(root, "config", "commit.gpgsign", "false")


def commit_tree(repo: Path, files: dict[str, bytes], message: str, tag: str | None = None) -> str:
    """Replace the repo's tracked tree with `files`, commit, optionally tag. Returns SHA."""
    for p in git(repo, "ls-files").splitlines():
        (repo / p).unlink()
    write_tree(repo, files)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    if tag:
        git(repo, "tag", "-a", tag, "-m", tag)
    return git(repo, "rev-parse", "HEAD")


def zip_of(repo: Path, ref: str, dest: Path, prefix: str = "kb-template-x/") -> Path:
    """A release archive the way GitHub makes it: git archive with a top folder."""
    subprocess.run(["git", "-C", str(repo), "archive", "--format=zip", f"--prefix={prefix}",
                    "-o", str(dest), ref], check=True)
    return dest


def zip_bytes(files: dict[str, bytes], comment: str = "", prefix: str = "kb-template-x/") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for p, data in files.items():
            zf.writestr(prefix + p, data)
        zf.comment = comment.encode("ascii")
    return buf.getvalue()


def run(*argv: str, opener=None) -> tuple[int, str, str]:
    """Run upgrade.py in-process; returns (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = upgrade.main(list(argv), opener=opener)
    REPORTED.extend(reported_folders(argv, code, out.getvalue(), err.getvalue()))
    return code, out.getvalue(), err.getvalue()


def onboard(instance: Path, values: dict | None = None, git_repo: bool = True) -> None:
    """What /b:onboard does to a fresh copy: render, stamp, delete templates and author
    files. The copy must already hold the template tree."""
    import planner
    values = dict(VALUES if values is None else values)
    (instance / kt.ONBOARD_VALUES).write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    man = kt.Manifest.load(instance)
    for out, tpl in man.rendered.items():
        data, missing, err = planner.render(RENDER_PY, (instance / tpl).read_bytes(), values)
        assert data is not None, (missing, err)
        (instance / out).write_bytes(data)
    code, stdout, stderr = run("stamp", "--instance", str(instance))
    assert code == 0, stderr
    for tpl in man.rendered.values():
        (instance / tpl).unlink()
    code, stdout, stderr = run("prune-author", "--instance", str(instance))
    assert code == 0, stderr
    if git_repo:
        git(instance, "add", "-A")
        git(instance, "commit", "-q", "-m", "onboard")


def tree_hashes(root: Path) -> dict[str, str]:
    """Every file under root (outside .git) -> hash; for "nothing changed" checks."""
    import sources
    return {p: kt.content_hash((root / p).read_bytes()) for p in sources.read_dir_paths(root)}


class TempDir:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)

    def cleanup(self):
        self._tmp.cleanup()


# --- a template history for adoption -------------------------------------------------
# P0  before 0.1.0: old skill paths, no CHANGELOG/LICENSE/.github
# P1  v0.1.0 (tag): still the old paths
# P2  between releases: skills renamed to brain-*
# P3  v0.2.0 (tag): manifest, index built in release mode

TPL = {
    "AGENTS.template.md": "# {{KB_NAME}}\n\nOwner: {{KB_OWNER}}\n",
    "CLAUDE.template.md": "@AGENTS.md\n",
    "content/WRITING_STYLE.template.md": "Language: {{PRIMARY_LANGUAGE}}\n",
    "content/REFERENCE/Example.md": "# Example\n",
    "README.md": "# Template README\n",
    "schema.yml": "types: [note]\n",
}
P0 = {**TPL,
      ".claude/skills/ingest/SKILL.md": "ingest v0\n",
      ".claude/skills/onboard/scripts/render.py": RENDER_PY.decode(),
      ".claude/hooks/hook.py": "hook v0\n",
      ".gitignore": "__pycache__/\n.kb-onboard.json\n"}
P1 = {**P0,
      ".claude/skills/ingest/SKILL.md": "ingest v1\n",
      ".claude/hooks/hook.py": "hook v1\n",
      "LICENSE": "MIT\n",
      "CHANGELOG.md": changelog("0.1.0"),
      ".github/workflows/kb.yml": "on: push\n"}
P2 = {k: v for k, v in P1.items() if not k.startswith((".claude/skills/ingest/", ".claude/skills/onboard/"))}
P2.update({".claude/skills/brain-ingest/SKILL.md": "ingest v1\n",
           ".claude/skills/brain-onboard/scripts/render.py": RENDER_PY.decode(),
           ".claude/hooks/hook.py": "hook v2\n",
           "CONTRIBUTING.md": "# Contributing to the template\n",
           ".gitignore": "__pycache__/\n"})
P3 = {**P2,
      ".kb-manifest.json": manifest("0.2.0"),
      "CHANGELOG.md": changelog("0.2.0", "0.1.0"),
      ".claude/skills/brain-upgrade/SKILL.md": "upgrade\n"}


def enc(files):
    return {p: v.encode() if isinstance(v, str) else v for p, v in files.items()}


def build_history(repo: Path, executable=()) -> dict:
    """`executable`: files every state ships, listed as executable by 0.2.0's manifest."""
    extra = {p: "#!/bin/sh\n" for p in executable}
    git_init(repo)
    shas = {"P0": commit_tree(repo, enc({**P0, **extra}), "pre-release state")}
    shas["P1"] = commit_tree(repo, enc({**P1, **extra}), "release 0.1.0", tag="v0.1.0")
    shas["P2"] = commit_tree(repo, enc({**P2, **extra}), "rename skills")
    # The release commit: stage, index the staged tree as 0.2.0, commit, tag.
    top = manifest("0.2.0", executable)
    commit_tree(repo, enc({**P3, **extra, ".kb-manifest.json": top}),
                "release 0.2.0 (without index yet)")
    git(repo, "reset", "-q", "--soft", "HEAD~1")
    index = kt.build_index(repo, kt.Manifest.from_bytes(top.encode()), release_tree=True)
    write_tree(repo, {kt.INDEX: kt.dump_index(index)})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "release 0.2.0")
    git(repo, "tag", "-a", "v0.2.0", "-m", "v0.2.0")
    shas["P3"] = git(repo, "rev-parse", "HEAD")
    return shas
