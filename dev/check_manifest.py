#!/usr/bin/env python3
"""Release check for the template source (author tool, never ships to instances).

Fails (exit 1, one line per problem) when:
  - a tracked file matches no class in `.kb-manifest.json` (or matches `exclude`);
  - the manifest version differs from the newest `## [X.Y.Z]` heading in CHANGELOG.md;
  - package.json has a `version` field;
  - a section heading (### Added, ### Fixed, ...) repeats within one version block;
  - the manifest's `executable` list and the files tracked as executable (mode 100755)
    differ, in either direction: an entry would ship no bit, or a bit nothing carries.

Usage:  python dev/check_manifest.py [--root PATH]   (default: this repository)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "brain-upgrade" / "scripts"))

import kbtemplate as kt  # noqa: E402


def problems(root: Path) -> list[str]:
    out = []
    try:
        manifest = kt.Manifest.load(root)
    except kt.TemplateError as e:
        return [str(e)]

    for path in kt.tracked_files(root):
        if manifest.classify(path) is None:
            why = "is excluded" if manifest.excluded(path) else "matches no class"
            out.append(f"unclassified: {path} {why} in {kt.MANIFEST}")

    changelog = root / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8") if changelog.is_file() else ""
    newest = kt.newest_release(text)
    if newest != manifest.version:
        out.append(f"version: {kt.MANIFEST} says {manifest.version}, "
                   f"the newest CHANGELOG.md release is {newest}")
    for block in kt.parse_changelog(text):
        seen = set()
        for s in block["sections"]:
            if s["heading"] in seen:
                out.append(f"changelog: [{block['version']}] has ### {s['heading']} more than once")
            seen.add(s["heading"])

    pkg = root / "package.json"
    if pkg.is_file() and "version" in json.loads(pkg.read_text(encoding="utf-8")):
        out.append(f"package.json: remove the \"version\" field; the version lives in {kt.MANIFEST}")

    tracked = executable_in_index(root)
    for path in sorted(set(manifest.executable) - tracked):
        out.append(f"executable: {path} is listed in {kt.MANIFEST} but is not tracked as "
                   f"executable (git update-index --chmod=+x -- {path})")
    for path in sorted(tracked - set(manifest.executable)):
        out.append(f"executable: {path} is tracked as executable but not listed in {kt.MANIFEST}")
    return out


def executable_in_index(root: Path) -> set[str]:
    """The paths tracked with mode 100755. Read from the index, so a release is checked
    as staged, and on Windows it is the only place the mode exists."""
    listing = kt.git(root, "ls-files", "-s", "-z").stdout
    records = (rec.split("\t", 1) for rec in filter(None, listing.split("\0")))
    return {path for meta, path in records if meta.split(" ")[0] == kt.MODE_EXECUTABLE}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    found = problems(Path(args.root))
    for p in found:
        print(p)
    if found:
        return 1
    print("manifest check ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
