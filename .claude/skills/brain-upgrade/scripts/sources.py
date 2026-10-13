#!/usr/bin/env python3
"""Update sources for brain-upgrade (design D3), standard library only.

A source is one template tree held in memory as {posix path: bytes}:

- a plain directory (an unpacked release), used as is;
- a git working copy, read with `git archive <ref>` so that untracked and ignored files
  never leak in; the ref defaults to the tag `v<version>`, else HEAD with a warning;
- a release `.zip`: one top-level folder is stripped, the commit comes from the zip
  comment that `git archive` writes;
- a download of `https://github.com/<repo>/archive/refs/tags/v<version>.zip`, saved to
  the temp directory so it can be reused offline.
"""

from __future__ import annotations

import io
import json
import os
import re
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import kbtemplate as kt

API = "https://api.github.com/repos/{repo}/releases/latest"
ARCHIVE = "https://github.com/{repo}/archive/refs/tags/v{version}.zip"
_SHA = re.compile(r"[0-9a-f]{40}\Z")


class OfflineError(kt.TemplateError):
    """The network was needed and could not be reached."""


def private_dir() -> Path:
    """A new directory under the OS temp dir that only this user can read or write
    (`mkdtemp`: unpredictable name, mode 0700), for archives, plans and unpacked trees."""
    return Path(tempfile.mkdtemp(prefix="kb-upgrade-"))




class Source:
    """One template tree. `manifest` is None for an old release without one (a base)."""

    def __init__(self, kind: str, location: str, files: dict[str, bytes], *,
                 commit: str | None = None, ref: str | None = None,
                 release: bool | None = None, warnings: list[str] | None = None,
                 archive: str | None = None, require_manifest: bool = True):
        kt.check_paths(files, location)
        self.kind, self.location, self.files = kind, location, files
        self.commit, self.ref, self.release = commit, ref, release
        self.warnings = list(warnings or [])
        self.archive = archive
        # Set only for a download: the repository whose GitHub archive URL was fetched
        # over HTTPS. A tree's own manifest only claims a repository.
        self.origin_repository: str | None = None
        self.origin_url: str | None = None
        raw = files.get(kt.MANIFEST)
        if raw is None and require_manifest:
            raise kt.TemplateError(
                f"{location} has no {kt.MANIFEST}: it is not a template release that "
                "brain-upgrade can install (0.2.0 or newer)")
        self.manifest = kt.Manifest.from_bytes(raw) if raw is not None else None
        self.version = self.manifest.version if self.manifest else None
        self.index = kt.HistoryIndex.from_bytes(files.get(kt.INDEX))
        self._hashes: dict[str, str] = {}

    def hash(self, path: str) -> str | None:
        if path not in self.files:
            return None
        if path not in self._hashes:
            self._hashes[path] = kt.content_hash(self.files[path])
        return self._hashes[path]

    def by_class(self, manifest: kt.Manifest | None = None) -> dict[str, list[str]]:
        """Paths of this tree per class (by `manifest`, default its own); None = ignored."""
        manifest = manifest or self.manifest
        out: dict = {c: [] for c in kt.CLASS_ORDER}
        out[None] = []
        for path in sorted(self.files):
            out[manifest.classify(path)].append(path)
        return out

    def owned(self, manifest: kt.Manifest | None = None) -> dict[str, str]:
        paths = self.by_class(manifest)["owned"]
        for p in paths:
            if kt.protected(p):
                raise kt.TemplateError(
                    f"{self.location}: its manifest makes {p!r} a template file, but notes, "
                    "README.md and brain-upgrade's own files always belong to the base. "
                    "Nothing was changed.")
        return {p: self.hash(p) for p in paths}

    def indexed(self, manifest: kt.Manifest | None = None) -> dict[str, str]:
        """Owned files as the history index sees them: without the index itself."""
        return {p: h for p, h in self.owned(manifest).items() if p != kt.INDEX}

    def matches_state(self, index: kt.HistoryIndex, state: int, manifest: kt.Manifest) -> bool:
        """True when this tree's owned files are exactly those of an indexed state."""
        want = {p: h for p, h in index.release_files(state).items()
                if manifest.classify(p) == "owned"}
        return want == self.indexed(manifest)

    def proven_release(self, version: str, index: kt.HistoryIndex | None = None,
                       manifest: kt.Manifest | None = None) -> bool:
        """Is this tree the release `version` itself (not just a tree carrying its number)?"""
        if self.release is not None and self.version == version:
            return self.release
        index = index or self.index
        manifest = manifest or self.manifest
        state = index.releases().get(version)
        if state is None or manifest is None:
            return False
        return self.matches_state(index, state, manifest)

    def describe(self) -> dict:
        return {"kind": self.kind, "location": self.location, "version": self.version,
                "commit": self.commit, "ref": self.ref, "release": self.release,
                "archive": self.archive,
                "repository": self.manifest.repository if self.manifest else None}

    def materialize(self, dest: Path) -> Path:
        """Write the tree to `dest` (for running its engine). Returns `dest`."""
        dest.mkdir(parents=True, exist_ok=True)
        for path, data in self.files.items():
            target = dest / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return dest


# --- readers -------------------------------------------------------------------------

def read_dir_paths(root: Path) -> list[str]:
    """Every file under `root` as a POSIX relative path, skipping `.git` (a folder, or the
    file a submodule or worktree has in its place)."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if name != ".git":
                out.append((Path(dirpath) / name).relative_to(root).as_posix())
    return sorted(out)


def read_dir(root: Path) -> dict[str, bytes]:
    return {p: (root / p).read_bytes() for p in read_dir_paths(root)}


def read_zip(data: bytes, where: str) -> tuple[dict[str, bytes], str | None]:
    """Files of a zip with a single top-level folder stripped, and the commit comment."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise kt.TemplateError(f"{where} is not a zip archive: {e}") from e
    comment = zf.comment.decode("ascii", "ignore").strip()
    commit = comment if _SHA.match(comment) else None
    members = [i for i in zf.infolist() if not i.is_dir()]
    names = [m.filename for m in members]
    kt.check_paths(names, where)
    tops = {n.split("/", 1)[0] for n in names}
    strip = len(tops) == 1 and all("/" in n for n in names)
    files = {}
    for m in members:
        name = m.filename.split("/", 1)[1] if strip else m.filename
        if name:
            files[name] = zf.read(m)
    return files, commit


def read_git(root: Path, ref: str) -> dict[str, bytes]:
    data = kt.git(root, "archive", "--format=tar", ref, text=False).stdout
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        for m in tf.getmembers():
            if m.isfile():
                files[m.name] = tf.extractfile(m).read()
    return files


# --- resolution ----------------------------------------------------------------------

def from_dir(path: Path, require_manifest: bool = True) -> Source:
    return Source("dir", str(path), read_dir(path), require_manifest=require_manifest)


def from_zip(path: Path, require_manifest: bool = True) -> Source:
    files, commit = read_zip(path.read_bytes(), str(path))
    return Source("zip", str(path), files, commit=commit, archive=str(path),
                  require_manifest=require_manifest)


def _manifest_version_at(root: Path, ref: str) -> str | None:
    r = kt.git(root, "show", f"{ref}:{kt.MANIFEST}", check=False)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout).get("version")
    except json.JSONDecodeError:
        return None


def from_git(root: Path, ref: str | None = None, require_manifest: bool = True) -> Source:
    warnings = []
    if ref is None:
        version = _manifest_version_at(root, "HEAD")
        tag = f"v{version}" if version else None
        if tag and kt.tag_commit(root, tag) and _manifest_version_at(root, tag) == version:
            ref = tag
        else:
            ref = "HEAD"
            head = (kt.head_commit(root) or "")[:12]
            warnings.append(
                f"not a release: {root} HEAD ({head}) is not the tag v{version}; it is "
                f"installed as {version} plus unreleased changes")
    commit = kt.git(root, "rev-parse", "--verify", f"{ref}^{{commit}}", check=False).stdout.strip()
    if not commit:
        raise kt.TemplateError(f"{root}: no such git ref: {ref}")
    src = Source("git", str(root), read_git(root, ref), commit=commit, ref=ref,
                 warnings=warnings, require_manifest=require_manifest)
    src.origin_url = kt.git(root, "remote", "get-url", "origin", check=False).stdout.strip() or None
    version = src.version
    if version is not None:
        src.release = kt.tag_commit(root, f"v{version}") == commit
    return src


def default_open(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "brain-upgrade",
                                               "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def latest_version(repository: str, opener=default_open) -> str:
    kt.check_repository_name(repository, "download")
    url = API.format(repo=repository)
    try:
        data = json.loads(opener(url).decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise kt.TemplateError(f"{url}: HTTP {e.code}; no published release found") from e
    except (urllib.error.URLError, OSError) as e:
        raise OfflineError(offline_message(repository)) from e
    tag = data.get("tag_name", "")
    kt.parse_version(tag)
    return tag.lstrip("v")


def offline_message(repository: str, version: str | None = None) -> str:
    name = repository.split("/")[-1]
    what = f"v{version}" if version else "the latest release"
    return (f"cannot download {what} of {repository} (no network?). Nothing was changed. "
            f"Pass a release archive or a local clone instead: --source "
            f"<path to {name}-{version or 'X.Y.Z'}.zip> or --source <path to a clone of "
            f"{repository}>.")


def download(repository: str, version: str | None = None, opener=default_open,
             dest: Path | None = None) -> Source:
    """Download a release archive (the latest when `version` is None)."""
    kt.check_repository_name(repository, "download")
    version = version or latest_version(repository, opener)
    url = ARCHIVE.format(repo=repository, version=version)
    try:
        data = opener(url)
    except urllib.error.HTTPError as e:
        raise kt.TemplateError(f"{url}: HTTP {e.code}; is v{version} a published release?") from e
    except (urllib.error.URLError, OSError) as e:
        raise OfflineError(offline_message(repository, version)) from e
    dest = dest or private_dir()
    path = dest / f"{repository.split('/')[-1]}-v{version}.zip"
    path.write_bytes(data)
    files, commit = read_zip(data, url)
    src = Source("download", url, files, commit=commit, archive=str(path),
                 release=True, require_manifest=False)
    src.origin_repository = repository
    if src.version not in (None, version):
        raise kt.TemplateError(f"{url} carries version {src.version}, expected {version}")
    return src


def resolve(source: str | None, *, ref: str | None = None, to: str | None = None,
            repository: str | None = None, opener=default_open,
            dest: Path | None = None, require_manifest: bool = True) -> Source:
    """Resolve `--source` (a directory, git clone or zip), else download a release."""
    if source is None:
        src = download(repository or kt.DEFAULT_REPOSITORY, to, opener, dest)
        if src.manifest is None and require_manifest:
            raise kt.TemplateError(
                f"{src.location} has no {kt.MANIFEST}: that release predates brain-upgrade")
        return src
    path = Path(source).expanduser()
    if path.is_dir():
        if kt.is_git_root(path):
            return from_git(path, ref or (f"v{to}" if to else None), require_manifest)
        if ref:
            raise kt.TemplateError(f"--ref needs a git working copy; {path} is not one")
        return from_dir(path, require_manifest)
    if path.is_file():
        return from_zip(path, require_manifest)
    raise kt.TemplateError(f"--source {source}: no such directory or .zip file")
