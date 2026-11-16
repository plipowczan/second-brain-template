#!/usr/bin/env python3
"""Write the Codex files from the Claude Code skills (author tool, never ships to instances).

Skills are edited only in `.claude/skills/`. For each skill whose
`.claude/skills/<skill>/SKILL.md` is tracked and in the owned class, this writes a stub,
`.agents/skills/<skill>/SKILL.md`: the source's frontmatter lines, unchanged, and a fixed
body that points the agent at the source. It also writes `.codex/hooks.json`, whose
SessionStart hook runs `.claude/hooks/load_vault_map.py`, and deletes every other file
under `.agents/skills/` (paths the manifest excludes aside).

`--check` writes nothing and fails (exit 1, one line per problem) when:
  - a stub or `.codex/hooks.json` differs from what this script writes (line endings
    aside), or is missing;
  - `.agents/skills/` holds a folder or a file with no source skill;
  - a source frontmatter is not valid YAML, lacks a string `name` or `description`, or
    a comment follows an unquoted description, so YAML reads less of it than the file
    holds;
  - a path this script writes runs through a symbolic link or junction.
Write mode fails on the last two kinds and then writes nothing.

Usage:  python dev/build_codex_files.py [--root PATH] [--check]   (default: this repository)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "brain-upgrade" / "scripts"))

import kbtemplate as kt  # noqa: E402

try:
    import yaml  # noqa: E402
except ImportError:  # pragma: no cover - CI installs requirements.txt
    print("PyYAML is missing: pip install -r requirements.txt")
    raise SystemExit(2)

SOURCES = ".claude/skills"
STUBS = ".agents/skills"
HOOKS = ".codex/hooks.json"
RUN = "python dev/build_codex_files.py"

# design.md D3. `{skill}` is the skill's folder name.
BODY = ("\n"
        "This skill's instructions are in `.claude/skills/{skill}/SKILL.md`. Read that file and\n"
        "follow it. Its folder, `.claude/skills/{skill}/`, is this skill's base directory.\n"
        "If that file does not exist, tell the user that this skill was removed from this base,\n"
        "and stop.\n")

# design.md D5, byte for byte. No `additionalContextLimit` (Paweł, 2026-11-16).
HOOKS_JSON = ('{\n'
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
              '}\n').encode("utf-8")

_TOP_KEY = re.compile(r"([A-Za-z0-9_-]+)\s*:(?:\s|$)")


def skills(root: Path, manifest: kt.Manifest) -> list[str]:
    """Folder names under `.claude/skills/` whose `SKILL.md` is tracked, owned, on disk."""
    out = []
    for path in kt.tracked_files(root):
        parts = path.split("/")
        if (len(parts) == 4 and "/".join(parts[:2]) == SOURCES and parts[3] == "SKILL.md"
                and manifest.classify(path) == "owned" and (root / path).is_file()):
            out.append(parts[2])
    return sorted(out)


def frontmatter_lines(text: str) -> list[str] | None:
    """The lines from the first line `---` to the next line `---`, both left out; None
    when the file does not start with such a block. A trailing CR is not part of a line."""
    lines = [ln[:-1] if ln.endswith("\r") else ln for ln in text.split("\n")]
    if lines[0] != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            return lines[1:i]
    return None


def key_at(lines: list[str], index: int) -> str | None:
    """The top-level key whose entry holds frontmatter line `index` (0-based)."""
    for ln in reversed(lines[:index + 1]):
        m = _TOP_KEY.match(ln)
        if m:
            return m.group(1)
    return None


def comment_after_plain(src: str, key: str) -> bool:
    """True when `key`'s value is an unquoted (plain) scalar and a YAML comment follows it
    before the next entry. YAML then drops the text from that ` #` on, on its line and on
    any line after it. Read from YAML's own nodes, so a tag, an anchor or a quoted key
    makes no difference. A quoted or block value keeps its `#`, so it is never cut."""
    root = yaml.compose(src, Loader=yaml.SafeLoader)
    if not isinstance(root, yaml.MappingNode):
        return False
    value = None
    for k, v in root.value:  # the last entry wins, as in YAML
        if isinstance(k, yaml.ScalarNode) and k.value == key:
            value = v
    if not isinstance(value, yaml.ScalarNode) or value.style is not None:
        return False
    end = value.end_mark.index
    # Between a value and the next node there is only white space and comments.
    starts = [n.start_mark.index for pair in root.value for n in pair]
    stop = min((s for s in starts if s >= end), default=len(src))
    return "#" in src[end:stop]


def frontmatter_problems(rel: str, text: str | None) -> list[str]:
    where = f"frontmatter: {rel}"
    if text is None:
        return [f"{where}: frontmatter: not UTF-8 text"]
    lines = frontmatter_lines(text)
    if lines is None:
        return [f"{where}: frontmatter: no frontmatter block (the file must start with a "
                f"line --- and close the block with another)"]
    try:
        data = yaml.safe_load("\n".join(lines))
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        field = (key_at(lines, mark.line) if mark else None) or "frontmatter"
        problem = getattr(e, "problem", None) or str(e).splitlines()[0]
        at = f", line {mark.line + 2} of the file" if mark else ""
        return [f"{where}: {field}: not valid YAML ({problem}{at}); wrap the value in "
                f"single quotes"]
    if not isinstance(data, dict):
        return [f"{where}: frontmatter: not a YAML mapping of keys to values"]
    out = []
    for key in ("name", "description"):
        value = data.get(key)
        if key not in data:
            out.append(f"{where}: {key}: missing")
        elif value is None:
            out.append(f"{where}: {key}: empty")
        elif not isinstance(value, str) or not value.strip():
            out.append(f"{where}: {key}: must be a non-empty string, YAML reads {value!r}")
    desc = data.get("description")
    if isinstance(desc, str) and comment_after_plain("\n".join(lines), "description"):
        out.append(f"{where}: description: YAML reads only its first {len(desc)} "
                   f"characters (a ' #' in an unquoted value starts a comment); wrap the "
                   f"value in single quotes")
    return out


def stub(skill: str, lines: list[str]) -> bytes:
    head = "---\n" + "".join(ln + "\n" for ln in lines) + "---\n"
    return (head + BODY.format(skill=skill)).encode("utf-8")


def read_text(path: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None


def disk_entries(root: Path, manifest: kt.Manifest) -> tuple[list[str], list[str]]:
    """Files, and links, under `.agents/skills/` on disk (tracked or not), as POSIX paths,
    minus the paths the manifest excludes. Links are listed, never followed."""
    files, links = [], []
    base = root / STUBS
    if not base.is_dir():
        return files, links
    for dirpath, dirnames, filenames in os.walk(base):
        here = Path(dirpath)
        for name in list(dirnames):
            if kt.is_link(here / name):
                dirnames.remove(name)
                links.append((here / name).relative_to(root).as_posix())
        for name in filenames:
            rel = (here / name).relative_to(root).as_posix()
            if manifest.excluded(rel):
                continue
            (links if kt.is_link(here / name) else files).append(rel)
    return sorted(files), sorted(links)


def plan(root: Path):
    """(problems that block writing, problems of the Codex files, the files this writes
    with their bytes, the files it deletes, the number of skills)."""
    manifest = kt.Manifest.load(root)
    names = skills(root, manifest)
    blocking, stale = [], []
    expected = {}
    for skill in names:
        rel = f"{SOURCES}/{skill}/SKILL.md"
        text = read_text(root / rel)
        found = frontmatter_problems(rel, text)
        blocking += found
        if not found:
            expected[f"{STUBS}/{skill}/SKILL.md"] = stub(skill, frontmatter_lines(text))
    expected[HOOKS] = HOOKS_JSON

    for top in (STUBS, HOOKS):
        link = kt.link_in_path(root, top)
        if link:
            blocking.append(f"link: {link}: is a symbolic link or junction; this script never "
                            f"writes through one. Delete it and run {RUN}")
    files, links = ([], []) if kt.link_in_path(root, STUBS) else disk_entries(root, manifest)
    for rel in links:
        blocking.append(f"link: {rel}: is a symbolic link or junction under {STUBS}/; "
                        f"delete it and run {RUN}")

    for rel, data in expected.items():
        h = kt.file_hash(root / rel)
        if h is None:
            stale.append(f"missing: {rel}: not there; run {RUN}")
        elif h != kt.content_hash(data):
            stale.append(f"stale: {rel}: differs from what {RUN} writes; run it")

    # A skill whose frontmatter failed has no expected stub, but its stub is no stray.
    stub_paths = {f"{STUBS}/{skill}/SKILL.md" for skill in names}
    deletions, orphans = [], set()
    for rel in files:
        if rel in expected or rel in stub_paths:
            continue
        parts = rel.split("/")
        deletions.append(rel)
        if len(parts) > 3 and parts[2] not in names:
            if parts[2] not in orphans:
                orphans.add(parts[2])
                stale.append(f"stray: {STUBS}/{parts[2]}/: no source skill "
                             f"({SOURCES}/{parts[2]}/SKILL.md); run {RUN} to delete it")
        elif len(parts) > 3:
            stale.append(f"stray: {rel}: a stub's folder holds only SKILL.md; run {RUN} "
                         f"to delete it")
        else:
            stale.append(f"stray: {rel}: no source skill; run {RUN} to delete it")
    return blocking, stale, expected, deletions, len(names)


def remove_empty_folders(root: Path) -> None:
    base = root / STUBS
    for dirpath, _, _ in os.walk(base, topdown=False):
        here = Path(dirpath)
        if here != base and not any(here.iterdir()):
            here.rmdir()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 when a Codex file is not what this writes")
    args = ap.parse_args(argv)
    root = Path(args.root)
    try:
        blocking, stale, expected, deletions, count = plan(root)
    except kt.TemplateError as e:
        print(e)
        return 1

    if args.check or blocking:
        found = blocking + stale
        for p in found:
            print(p)
        if blocking and not args.check:
            print("nothing was written")
        if found:
            return 1
        print(f"codex files ok: {count} stubs and {HOOKS}")
        return 0

    for rel in deletions:
        (root / rel).unlink()
        print(f"deleted: {rel}")
    if deletions:
        remove_empty_folders(root)
    # Compared after the deletions: on a case-insensitive disk a deleted `Alpha/SKILL.md`
    # was also `alpha/SKILL.md`.
    written = 0
    for rel, data in expected.items():
        path = root / rel
        if kt.file_hash(path) == kt.content_hash(data):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)  # bytes as given: LF, and no executable bit
        written += 1
        print(f"wrote: {rel}")
    state = "written" if written or deletions else "up to date"
    print(f"codex files {state}: {count} stubs and {HOOKS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
