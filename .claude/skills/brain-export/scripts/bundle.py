#!/usr/bin/env python3
"""Brain note-bundle tool (format 1).

Deterministic half of /export and /import: packs selected notes into a zip
bundle with a manifest, unpacks + verifies bundles, and compares note files.
All LLM judgement (selection, triage, placement) stays in the skills.

Bundle layout:
    brain-pack-<slug>-<YYYY-MM-DD>.zip
    ├─ manifest.json   {format, source, exported, notes:[{path, title, sha256}]}
    └─ notes/<SOURCE/FOLDER/PATH>/<Note>.md   (verbatim copies)

Commands (run from repo root):
    pack   --source NAME --out FILE.zip PATH [PATH ...]   paths relative to content/
    unpack --bundle FILE.zip --dest DIR                    extract + verify, JSON to stdout
    same   FILE_A FILE_B                                   newline-normalized equality

Exit codes: 0 ok, 1 usage/IO error, 2 validation failure (bad manifest/hash).
"""

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

FORMAT_VERSION = 1
CONTENT = Path("content")
EXCLUDED_TOPS = {"_indexes", "_outputs", "_raw", "_graveyard", "templates"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def note_title(path: Path, data: bytes) -> str:
    """Frontmatter title, else filename stem."""
    m = re.search(rb'^---\s*\n(.*?)\n---', data, re.DOTALL)
    if m:
        t = re.search(rb'^title:\s*["\']?(.+?)["\']?\s*$', m.group(1), re.MULTILINE)
        if t:
            return t.group(1).decode("utf-8", "replace")
    return path.stem


def unsafe_member(path: str) -> bool:
    """Reject path traversal in bundle member paths (zip slip)."""
    parts = path.split("/")
    return (
        path.startswith("/")
        or "\\" in path
        or re.match(r"^[A-Za-z]:", path) is not None
        or any(p in ("", ".", "..") for p in parts)
    )


def excluded(rel: Path) -> bool:
    return (
        rel.suffix.lower() != ".md"
        or not rel.parts
        or rel.parts[0] in EXCLUDED_TOPS
        or any(p.startswith("_") for p in rel.parts)
    )


def cmd_pack(args: argparse.Namespace) -> int:
    notes, skipped = [], []
    for raw in args.paths:
        rel = Path(raw.replace("\\", "/"))
        if excluded(rel):
            skipped.append(rel.as_posix())
            continue
        src = CONTENT / rel
        if not src.is_file():
            print(f"error: not a file: {src}", file=sys.stderr)
            return 1
        data = src.read_bytes()
        notes.append({"path": rel.as_posix(), "title": note_title(rel, data),
                      "sha256": sha256_bytes(data), "_data": data})
    if not notes:
        print("error: empty selection after exclusions", file=sys.stderr)
        return 1

    manifest = {
        "format": FORMAT_VERSION,
        "source": args.source,
        "exported": args.date or dt.date.today().isoformat(),
        "notes": [{k: n[k] for k in ("path", "title", "sha256")} for n in notes],
    }
    out = Path(args.out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        for n in notes:
            zf.writestr("notes/" + n["path"], n["_data"])
    print(json.dumps({"ok": True, "bundle": str(out), "packed": len(notes),
                      "skipped_excluded": skipped}, ensure_ascii=False))
    return 0


def cmd_unpack(args: argparse.Namespace) -> int:
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    errors = []
    with zipfile.ZipFile(args.bundle) as zf:
        try:
            manifest = json.loads(zf.read("manifest.json"))
        except KeyError:
            print(json.dumps({"ok": False, "errors": ["manifest.json missing"]}))
            return 2
        if manifest.get("format") != FORMAT_VERSION:
            print(json.dumps({"ok": False, "errors": [
                f"unsupported bundle format {manifest.get('format')!r}, this tool knows format {FORMAT_VERSION}"]}))
            return 2
        names = set(zf.namelist())
        for name in names:
            if name != "manifest.json" and unsafe_member(name.removeprefix("notes/")):
                errors.append(f"unsafe zip member: {name}")
        notes_root = (dest / "notes").resolve()
        for n in manifest.get("notes", []):
            if unsafe_member(n["path"]):
                errors.append(f"unsafe path in manifest: {n['path']}")
                continue
            member = "notes/" + n["path"]
            if member not in names:
                errors.append(f"missing in zip: {n['path']}")
                continue
            data = zf.read(member)
            if sha256_bytes(data) != n["sha256"]:
                errors.append(f"sha256 mismatch: {n['path']}")
                continue
            target = (notes_root / Path(*n["path"].split("/"))).resolve()
            if notes_root not in target.parents:
                errors.append(f"path escapes staging dir: {n['path']}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        if not errors:
            (dest / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, "dest": str(dest), "format": manifest["format"],
                      "source": manifest["source"], "exported": manifest["exported"],
                      "notes": manifest["notes"]}, ensure_ascii=False))
    return 0


def normalized(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def cmd_same(args: argparse.Namespace) -> int:
    same = normalized(Path(args.file_a)) == normalized(Path(args.file_b))
    print(json.dumps({"same": same}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pack", help="pack notes into a bundle zip")
    p.add_argument("--source", required=True, help="source brain name for the manifest")
    p.add_argument("--out", required=True, help="output zip path")
    p.add_argument("--date", help="override export date (tests)")
    p.add_argument("paths", nargs="+", help="note paths relative to content/")
    p.set_defaults(fn=cmd_pack)

    p = sub.add_parser("unpack", help="extract bundle to staging dir + verify hashes")
    p.add_argument("--bundle", required=True)
    p.add_argument("--dest", required=True)
    p.set_defaults(fn=cmd_unpack)

    p = sub.add_parser("same", help="newline-normalized byte equality of two files")
    p.add_argument("file_a")
    p.add_argument("file_b")
    p.set_defaults(fn=cmd_same)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
