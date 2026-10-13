#!/usr/bin/env python3
"""Shared helpers for brain-upgrade (standard library only).

- content hashes that ignore CRLF/LF differences (design D5);
- the template manifest `.kb-manifest.json`: classes, globs, classification;
- the instance stamp `.kb-template.json`;
- SemVer ordering and `CHANGELOG.md` sections;
- the history index `known-hashes.json` (design D9);
- small git wrappers.

Imported by `upgrade.py` and by the template's `dev/` tools. Nothing here writes to an
instance except `write_stamp`.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

MANIFEST = ".kb-manifest.json"
STAMP = ".kb-template.json"
ONBOARD_VALUES = ".kb-onboard.json"
INDEX = ".claude/skills/brain-upgrade/known-hashes.json"
BACKUP_DIR = ".kb-upgrade-backup"
CLASS_ORDER = ("author", "rendered", "owned", "seeded")
STAMP_FORMAT = 1
INDEX_FORMAT = 1
DEFAULT_REPOSITORY = "plipowczan/second-brain-template"


class TemplateError(Exception):
    """A problem the owner has to act on; the message says what to do."""


# --- path safety ---------------------------------------------------------------------
# Every path brain-upgrade reads, writes or deletes comes from data it did not write
# itself: archive member names, the source's manifest and history index, the base's
# stamp. One rule for all of them: a relative POSIX path that names the same single
# place inside the base on every OS.

WRITING_STYLE = "content/WRITING_STYLE.md"
_DRIVE = re.compile(r"^[A-Za-z]:")


def path_problem(path) -> str | None:
    """Why `path` is not a safe relative path, or None when it is."""
    if not isinstance(path, str) or not path:
        return "empty"
    if "\\" in path:
        return "backslash"
    if path.startswith("/"):
        return "absolute or UNC"
    if _DRIVE.match(path):
        return "drive letter"
    if ":" in path:
        return "':' (a Windows stream name)"
    if "\0" in path:
        return "NUL byte"
    for seg in path.split("/"):
        if seg in ("", ".", ".."):
            return "empty, '.' or '..' segment"
        if seg != seg.rstrip(". "):
            return "a segment ends with a dot or a space"
        if seg.casefold() == ".git":
            return "inside .git"
    return None


def case_collisions(paths) -> list[tuple[str, str]]:
    """Pairs of paths that would be one file (or a file and a folder) on a
    case-insensitive filesystem such as Windows or macOS."""
    seen: dict[str, str] = {}
    out = []
    for p in sorted(paths):
        key = p.casefold()
        if key in seen and seen[key] != p:
            out.append((seen[key], p))
        seen.setdefault(key, p)
    for p in sorted(paths):
        parts = p.casefold().split("/")
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i])
            if prefix in seen:
                out.append((seen[prefix], p))
    return out


def check_paths(paths, where: str) -> None:
    """Raise TemplateError naming the first unsafe or colliding path."""
    paths = list(paths)
    for p in paths:
        why = path_problem(p)
        if why:
            raise TemplateError(f"{where}: unsafe path {p!r} ({why}). Nothing was changed.")
    clash = case_collisions(paths)
    if clash:
        a, b = clash[0]
        raise TemplateError(f"{where}: {a!r} and {b!r} would be the same file on Windows "
                            "or macOS. Nothing was changed.")


def protected(path: str) -> bool:
    """Paths an upgrade never writes or deletes as a file action, whatever a manifest
    says: the owner's notes and README.md, and brain-upgrade's own bookkeeping. The one
    exception, content/WRITING_STYLE.md on a requested re-render, is handled by callers."""
    p = path.casefold()
    return (p == "readme.md" or p.startswith("content/") or p in (STAMP, ONBOARD_VALUES)
            or p.startswith(BACKUP_DIR + "/"))


def check_pattern(pattern, where: str) -> None:
    if (not isinstance(pattern, str) or not pattern or "\\" in pattern
            or pattern.startswith("/") or _DRIVE.match(pattern)
            or any(seg in (".", "..") for seg in pattern.split("/"))):
        raise TemplateError(f"{where}: unsafe pattern {pattern!r}. Nothing was changed.")


# --- hashing -------------------------------------------------------------------------

def content_hash(data: bytes) -> str:
    """`sha256:<hex>`; text (no NUL byte) is hashed with CRLF turned into LF first."""
    if b"\0" not in data:
        data = data.replace(b"\r\n", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str | None:
    """Hash of a file on disk, or None when it does not exist."""
    return content_hash(path.read_bytes()) if path.is_file() else None


def is_binary(data: bytes) -> bool:
    return b"\0" in data


# --- globs and the manifest ----------------------------------------------------------

_GLOB_CACHE: dict[str, re.Pattern] = {}


def glob_regex(pattern: str) -> re.Pattern:
    """Translate a manifest glob to a regex over POSIX relative paths.

    `**` matches any number of path segments (including none), `*` and `?` stay inside
    one segment. `dir/**` matches everything under `dir/`.
    """
    if pattern in _GLOB_CACHE:
        return _GLOB_CACHE[pattern]
    i, out = 0, []
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    rx = re.compile("".join(out) + r"\Z")
    _GLOB_CACHE[pattern] = rx
    return rx


def glob_match(pattern: str, path: str) -> bool:
    return glob_regex(pattern).match(path) is not None


class Manifest:
    """`.kb-manifest.json` of one template tree."""

    def __init__(self, data: dict):
        if not isinstance(data, dict) or data.get("format") != 1:
            raise TemplateError(f"{MANIFEST}: unsupported or missing format (expected 1)")
        classes = data.get("classes") or {}
        self.data = data
        self.version = str(data.get("version", ""))
        parse_version(self.version)
        self.repository = data.get("repository") or DEFAULT_REPOSITORY
        self.author = list(classes.get("author", []))
        self.rendered = dict(classes.get("rendered", {}))
        self.owned = list(classes.get("owned", []))
        self.seeded = list(classes.get("seeded", []))
        self.exclude = list(data.get("exclude", []))
        self.render_sources = {src: out for out, src in self.rendered.items()}
        for p in self.author + self.owned + self.seeded + self.exclude:
            check_pattern(p, MANIFEST)
        check_paths(list(self.rendered) + list(self.render_sources), f"{MANIFEST} rendered")
        for out in self.rendered:
            if protected(out) and out != WRITING_STYLE:
                raise TemplateError(f"{MANIFEST}: rendered output {out!r} belongs to the base; "
                                    "only CLAUDE.md-style files and content/WRITING_STYLE.md "
                                    "may be rendered. Nothing was changed.")

    @classmethod
    def from_bytes(cls, data: bytes) -> "Manifest":
        try:
            return cls(json.loads(data.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise TemplateError(f"{MANIFEST} is not valid JSON: {e}") from e

    @classmethod
    def load(cls, root: Path) -> "Manifest":
        path = Path(root) / MANIFEST
        if not path.is_file():
            raise TemplateError(f"no {MANIFEST} in {root} (a template older than 0.2.0?)")
        return cls.from_bytes(path.read_bytes())

    def excluded(self, path: str) -> bool:
        return any(glob_match(p, path) for p in self.exclude)

    def classify(self, path: str) -> str | None:
        """Class of a path in a template tree (first match wins), None if it never ships."""
        if self.excluded(path):
            return None
        if any(glob_match(p, path) for p in self.author):
            return "author"
        if path in self.rendered or path in self.render_sources:
            return "rendered"
        if any(glob_match(p, path) for p in self.owned):
            return "owned"
        if any(glob_match(p, path) for p in self.seeded):
            return "seeded"
        return None


# --- versions and the changelog ------------------------------------------------------

_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?\Z")


def parse_version(v: str) -> tuple:
    """Sort key for a SemVer string; a pre-release sorts before its release."""
    m = _SEMVER.match(str(v).lstrip("v"))
    if not m:
        raise TemplateError(f"not a SemVer version: {v!r}")
    major, minor, patch, pre = m.groups()
    return (int(major), int(minor), int(patch), 0 if pre else 1, pre or "")


_VERSION_HEAD = re.compile(r"^## \[([^\]]+)\](?:\s*-\s*(\S+))?\s*$")
_SECTION_HEAD = re.compile(r"^### (.+?)\s*$")


def parse_changelog(text: str) -> list[dict]:
    """Version blocks of a Keep a Changelog file, newest first.

    Each block: {version, date, sections: [{heading, entries: [{text, breaking}]}]}.
    Entries are the top-level `- ` bullets with their continuation lines.
    """
    blocks: list[dict] = []
    block = section = entry = None
    for line in text.replace("\r\n", "\n").split("\n"):
        m = _VERSION_HEAD.match(line)
        if m:
            block = {"version": m.group(1), "date": m.group(2), "sections": []}
            blocks.append(block)
            section = entry = None
            continue
        if block is None:
            continue
        if line.strip() == "---":
            block = section = entry = None
            continue
        m = _SECTION_HEAD.match(line)
        if m:
            section = {"heading": m.group(1), "entries": []}
            block["sections"].append(section)
            entry = None
            continue
        if section is None:
            continue
        if line.startswith("- "):
            entry = {"text": line[2:]}
            section["entries"].append(entry)
        elif entry is not None and (line.startswith(" ") or not line.strip()):
            entry["text"] += "\n" + line
    for b in blocks:
        for s in b["sections"]:
            for e in s["entries"]:
                e["text"] = e["text"].rstrip()
                e["breaking"] = "BREAKING" in e["text"].split("\n", 1)[0]
    return blocks


def changelog_range(text: str, after: str | None, upto: str) -> list[dict]:
    """Blocks newer than `after` and no newer than `upto`, plus a non-empty
    `[Unreleased]` (what a source between releases carries). `after=None` = all."""
    lo = parse_version(after) if after else None
    hi = parse_version(upto)
    out = []
    for b in parse_changelog(text):
        if b["version"].lower() == "unreleased":
            if any(s["entries"] for s in b["sections"]):
                out.append(b)
            continue
        try:
            key = parse_version(b["version"])
        except TemplateError:
            continue
        if (lo is None or key > lo) and key <= hi:
            out.append(b)
    return out


def changelog_version(text: str, version: str) -> list[dict]:
    """Only the block of one released version."""
    return [b for b in parse_changelog(text) if b["version"] == version]


def newest_release(text: str) -> str | None:
    for b in parse_changelog(text):
        if b["version"].lower() != "unreleased":
            return b["version"]
    return None


# --- the stamp ----------------------------------------------------------------------

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_stamp(root: Path) -> dict | None:
    path = Path(root) / STAMP
    if not path.is_file():
        return None
    try:
        stamp = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise TemplateError(f"{STAMP} is not valid JSON: {e}") from e
    if stamp.get("format") != STAMP_FORMAT:
        raise TemplateError(f"{STAMP}: unsupported format {stamp.get('format')!r}")
    stamp.setdefault("files", {})
    stamp.setdefault("rendered", {})
    check_paths(stamp["files"], f"{STAMP} files")
    for p in stamp["files"]:
        if protected(p):
            raise TemplateError(f"{STAMP}: {p!r} cannot be a template file; notes, README.md "
                                "and brain-upgrade's own files belong to the base. Nothing "
                                "was changed.")
    check_paths(list(stamp["rendered"]) + [e.get("template") for e in stamp["rendered"].values()
                                            if isinstance(e, dict)], f"{STAMP} rendered")
    check_paths(stamp.get("seeded") or {}, f"{STAMP} seeded")
    return stamp


def make_stamp(repository: str, version: str, commit: str | None, files: dict,
               rendered: dict, seeded: dict | None = None) -> dict:
    """`files`: owned path -> hash as the template shipped it; `rendered`: output path ->
    {template, template_hash, output_hash}; `seeded`: starter file -> shipped hash, used
    only to tell the owner what changed upstream."""
    return {
        "format": STAMP_FORMAT,
        "repository": repository,
        "version": version,
        "commit": commit,
        "updated": utc_now(),
        "files": dict(sorted(files.items())),
        "rendered": dict(sorted(rendered.items())),
        "seeded": dict(sorted((seeded or {}).items())),
    }


def dump_json(data) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_stamp(root: Path, stamp: dict) -> Path:
    path = Path(root) / STAMP
    path.write_bytes(dump_json(stamp))
    return path


# --- git -----------------------------------------------------------------------------

def git_available() -> bool:
    return shutil.which("git") is not None


def git(root: Path, *args: str, check: bool = True, text: bool = True,
        input=None) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=text,
                       input=input, **({"encoding": "utf-8"} if text else {}))
    if check and r.returncode != 0:
        err = r.stderr if text else r.stderr.decode("utf-8", "replace")
        raise TemplateError(f"git {' '.join(args)} failed: {err.strip()}")
    return r


def is_git_root(root: Path) -> bool:
    """True when `root` is the top of a git working tree (and git is installed)."""
    if not git_available():
        return False
    r = git(root, "rev-parse", "--show-toplevel", check=False)
    if r.returncode != 0:
        return False
    return Path(r.stdout.strip()).resolve() == Path(root).resolve()


def tag_commit(root: Path, tag: str) -> str | None:
    r = git(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}", check=False)
    return r.stdout.strip() or None if r.returncode == 0 else None


def head_commit(root: Path) -> str | None:
    r = git(root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}", check=False)
    return r.stdout.strip() or None if r.returncode == 0 else None


def tracked_files(root: Path) -> list[str]:
    out = git(root, "ls-files", "-z").stdout
    return sorted(p for p in out.split("\0") if p)


# --- the history index ---------------------------------------------------------------

class HistoryIndex:
    """`known-hashes.json`: every hash each owned/author path had in template history.

    Layout: {"format": 1, "repository", "states": [{commit, date, release, in}],
    "files": {path: {hash: [state, ...]}}}. States are in topological order (parents
    first); `in` lists the releases whose history contains the state.
    """

    def __init__(self, data: dict | None = None):
        data = data or {"format": INDEX_FORMAT, "states": [], "files": {}}
        if data.get("format") != INDEX_FORMAT:
            raise TemplateError(f"known-hashes.json: unsupported format {data.get('format')!r}")
        self.data = data
        self.states = data.get("states", [])
        self.files = data.get("files", {})
        check_paths(self.files, "known-hashes.json")
        for p in self.files:
            if protected(p):
                raise TemplateError(f"known-hashes.json: {p!r} cannot be a template file. "
                                    "Nothing was changed.")

    @classmethod
    def from_bytes(cls, data: bytes | None) -> "HistoryIndex":
        return cls(json.loads(data.decode("utf-8")) if data else None)

    def known(self, path: str, h: str | None) -> bool:
        return h is not None and h in self.files.get(path, {})

    def states_of(self, path: str, h: str) -> list[int]:
        return self.files.get(path, {}).get(h, [])

    def releases(self) -> dict[str, int]:
        """version -> state number of each tagged release in the index."""
        return {s["release"]: i for i, s in enumerate(self.states) if s.get("release")}

    def release_files(self, state: int) -> dict[str, str]:
        """path -> hash of every indexed file present in one state."""
        out = {}
        for path, hashes in self.files.items():
            for h, states in hashes.items():
                if state in states:
                    out[path] = h
        return out

    def in_release(self, state: int, version: str) -> bool:
        """True when `state` is the release `version` or one of its ancestors."""
        return version in self.states[state].get("in", [])

    def latest_hash(self, path: str) -> str | None:
        """The hash a path had in the newest state that shipped it."""
        found = [(s, h) for h, states in self.files.get(path, {}).items() for s in states]
        return max(found)[1] if found else None


def build_index(repo: Path, manifest: Manifest, release_tree: bool = False) -> dict:
    """Walk every commit reachable from HEAD of the template repo `repo` and index the
    hash of each owned- or author-class file (classified by `manifest`).

    A state is kept when its indexed files differ from the previous state's or when a
    `v*` tag names it. Each state lists the releases whose history contains it, so
    adoption can tell an older state from a newer or parallel one. With `release_tree`,
    the staged tree (`git write-tree`) is added as the newest state and labelled with the
    manifest version: the release commit itself, before it exists.
    """
    tags = {}
    refs = git(repo, "for-each-ref", "--format=%(refname:short) %(objectname) %(*objectname)",
               "refs/tags/v*").stdout
    for line in refs.splitlines():
        name, obj, peeled = (line.split(" ") + ["", ""])[:3]
        try:
            parse_version(name[1:])
        except TemplateError:
            continue
        tags[peeled or obj] = name[1:]

    log = git(repo, "log", "--topo-order", "--reverse", "--format=%H %cs", "HEAD").stdout
    commits = [tuple(line.split(" ", 1)) for line in log.splitlines() if line.strip()]
    history = {}  # release -> commits reachable from its tag
    for sha, version in tags.items():
        history[version] = set(git(repo, "rev-list", sha).stdout.split())
    if release_tree:
        history[manifest.version] = {sha for sha, _ in commits} | {None}
    trees: list[tuple[str | None, str, str | None, str]] = [
        (sha, date, tags.get(sha), sha) for sha, date in commits]
    if release_tree:
        tree = git(repo, "write-tree").stdout.strip()
        cl = git(repo, "show", f"{tree}:CHANGELOG.md", check=False).stdout or ""
        date = next((b["date"] for b in parse_changelog(cl)
                     if b["version"] == manifest.version), None) or utc_now()[:10]
        trees.append((None, date, manifest.version, tree))

    blob_hash: dict[str, str] = {}
    states, files, prev = [], {}, None
    for commit, date, release, treeish in trees:
        listing = git(repo, "ls-tree", "-r", "-z", treeish).stdout
        snap = {}
        for rec in listing.split("\0"):
            if not rec:
                continue
            meta, path = rec.split("\t", 1)
            mode, kind, blob = meta.split(" ")
            if kind != "blob" or path == INDEX:
                continue
            if manifest.classify(path) not in ("owned", "author"):
                continue
            snap[path] = blob
        if snap == prev and not release:
            continue
        prev = snap
        need = [b for b in snap.values() if b not in blob_hash]
        if need:
            data = git(repo, "cat-file", "--batch", text=False,
                       input=("\n".join(need) + "\n").encode()).stdout
            pos = 0
            for blob in need:
                header_end = data.index(b"\n", pos)
                size = int(data[pos:header_end].split(b" ")[2])
                body = data[header_end + 1:header_end + 1 + size]
                blob_hash[blob] = content_hash(body)
                pos = header_end + 1 + size + 1
        state = len(states)
        states.append({"commit": commit, "date": date, "release": release,
                       "in": sorted((v for v, seen in history.items() if commit in seen),
                                    key=parse_version)})
        for path, blob in snap.items():
            files.setdefault(path, {}).setdefault(blob_hash[blob], []).append(state)
    return {
        "format": INDEX_FORMAT,
        "repository": manifest.repository,
        "states": states,
        "files": {p: dict(sorted(h.items())) for p, h in sorted(files.items())},
    }


def dump_index(index: dict) -> bytes:
    """Stable serialisation: the same history always gives the same bytes."""
    return (json.dumps(index, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
