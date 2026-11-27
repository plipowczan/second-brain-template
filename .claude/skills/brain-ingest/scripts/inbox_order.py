#!/usr/bin/env python3
"""The inbox in the order /b:ingest --backlog takes it: the sources oldest first, the
attachments, the files nobody can ingest, and for each source whether its content is
already archived in content/_raw/processed/. Read-only: it moves and writes nothing.

Usage (run from the vault root, or pass --root <vault root>):
    python inbox_order.py [--limit N] [--root <vault root>]

Prints one JSON object:
    {"sources": [{"path": "content/_raw/inbox/<rel>", "basis": "name"|"frontmatter"|"mtime",
                  "key": "<ISO date or UTC datetime the order used>",
                  "duplicate_of": "content/_raw/processed/<file>" | null}],
     "attachments": ["content/_raw/inbox/<rel>", ...],
     "unusable": [{"path": "...", "reason": "empty"|"unreadable"}],
     "take": ["<path>", ...],    the first N sources (all of them without --limit)
     "remaining": N}             the sources not in take

- Every file under content/_raw/inbox/, folders included; names starting with "." (and
  everything in such a folder) are left out.
- Attachments are image and media files, by extension (ATTACHMENT_EXT, any case). They
  move with the source that references them and never count as a source.
- Every other file is a source (ingest reads whatever lands in the inbox, PDFs
  included), unless it is unusable: 0 bytes, a text file (TEXT_EXT) holding only
  whitespace ("empty"), or a file that cannot be opened or read ("unreadable").
- Oldest first: the first real YYYY-MM-DD date in the file name ("name"), else the
  frontmatter date: of a file that starts with "---" ("frontmatter", a time and an
  offset count when given), else the modification time ("mtime", whole seconds).
  All are compared as UTC datetimes, a date as its midnight; ties go by path.
- duplicate_of: the first file by path under content/_raw/processed/ (all folders)
  whose SHA-256 equals the source's, else null.

Exit codes: 0 done, 1 no content/ under the root, 2 usage error.
"""

import argparse
import codecs
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

INBOX = Path("content") / "_raw" / "inbox"
PROCESSED = Path("content") / "_raw" / "processed"
ATTACHMENT_EXT = {
    # images
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".tif", ".tiff", ".heic",
    ".heif", ".avif", ".ico",
    # video
    ".webm", ".mp4", ".mov", ".m4v", ".mkv", ".avi", ".wmv",
    # audio
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus",
}
TEXT_EXT = {".md", ".txt", ".html", ".htm", ".csv", ".json", ".xml"}
CHUNK = 1 << 20
HEAD_BYTES = 16384      # enough for any frontmatter worth reading
FRONTMATTER_LINES = 50  # the first lines only
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# Every position where a date starts, so "2026-13-40_2025-02-03" still finds the second.
NAME_DATE = re.compile(r"(?<![0-9])(?=([0-9]{4})-([0-9]{2})-([0-9]{2})(?![0-9]))")
DATE_KEY = re.compile(r"date[ \t]*:")
DATE_VALUE = re.compile(
    r"date[ \t]*:[ \t]*(['\"]?)([0-9]{4})-([0-9]{2})-([0-9]{2})"
    r"(?:[T ]([0-9]{1,2}):([0-9]{2})(?::([0-9]{2})(?:\.[0-9]+)?)?)?"
    r"[ \t]*(Z|[+-][0-9]{2}:?[0-9]{2})?\1[ \t]*(?:#.*)?")


def walk(top, errors=None):
    """(full path, path relative to top with "/") of every file under top, sorted, with
    hidden files and folders left out. A folder that cannot be listed is added to
    errors as its relative path."""
    found = []

    def failed(err):
        if errors is not None and err.filename:
            try:
                errors.append(Path(err.filename).relative_to(top).as_posix())
            except ValueError:
                pass

    for dirpath, dirnames, filenames in os.walk(top, onerror=failed):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if not name.startswith("."):
                full = Path(dirpath) / name
                found.append((full, full.relative_to(top).as_posix()))
    return found


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(path, text):
    """(reason, digest, head, stat): reason is None for a usable file, else "empty" or
    "unreadable". head is the first HEAD_BYTES bytes, for the frontmatter."""
    try:
        st = os.stat(path)
    except OSError:
        return "unreadable", None, None, None
    if st.st_size == 0:
        return "empty", None, None, None
    h, head = hashlib.sha256(), b""
    blank = text
    decoder = codecs.getincrementaldecoder("utf-8-sig")(errors="replace")
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(CHUNK), b""):
                h.update(chunk)
                if len(head) < HEAD_BYTES:
                    head += chunk[:HEAD_BYTES - len(head)]
                if blank and decoder.decode(chunk).strip():
                    blank = False
    except OSError:
        return "unreadable", None, None, None
    if blank and not decoder.decode(b"", final=True).strip():
        return "empty", None, None, None
    return None, h.hexdigest(), head, st


def name_date(name):
    """(UTC midnight, "YYYY-MM-DD") of the first real date in name, or None."""
    for m in NAME_DATE.finditer(name):
        try:
            d = datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=timezone.utc)
        except ValueError:
            continue
        return d, d.strftime("%Y-%m-%d")
    return None


def offset(value):
    if value in (None, "Z"):
        return timezone.utc
    sign = -1 if value[0] == "-" else 1
    digits = value[1:].replace(":", "")
    return timezone(sign * timedelta(hours=int(digits[:2]), minutes=int(digits[2:])))


def frontmatter_date(head):
    """(UTC datetime, key) from the frontmatter date: in head, or None."""
    text = head.decode("utf-8", errors="replace")
    if text.startswith("﻿"):
        text = text[1:]
    lines = text.split("\n")
    if lines[0].rstrip() != "---":
        return None
    for line in lines[1:FRONTMATTER_LINES]:
        line = line.rstrip()
        if line in ("---", "..."):
            return None
        if not DATE_KEY.match(line):
            continue
        m = DATE_VALUE.fullmatch(line)
        if not m:
            return None
        try:
            d = datetime(int(m[2]), int(m[3]), int(m[4]), tzinfo=timezone.utc)
        except ValueError:
            return None
        if m[5] is None:
            return d, d.strftime("%Y-%m-%d")
        try:
            t = datetime(d.year, d.month, d.day, int(m[5]), int(m[6]), int(m[7] or 0),
                         tzinfo=offset(m[8])).astimezone(timezone.utc)
        except ValueError:
            return d, d.strftime("%Y-%m-%d")  # a time that cannot be: the date alone
        return t, t.strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


def mtime_key(mtime):
    try:
        t = datetime.fromtimestamp(int(mtime), tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        t = EPOCH
    return t, t.strftime("%Y-%m-%dT%H:%M:%SZ")


def processed_index(root, sizes):
    """{sha256: path} of the files under _raw/processed/ whose size equals a source's,
    the first by path for each content. Only those are hashed: the archive grows."""
    top = root / PROCESSED
    if not sizes or not top.is_dir():
        return {}
    index = {}
    for full, rel in sorted(walk(top), key=lambda e: (e[1].casefold(), e[1])):
        try:
            if os.stat(full).st_size not in sizes:
                continue
            digest = sha256(full)
        except OSError:
            continue
        index.setdefault(digest, (PROCESSED / rel).as_posix())
    return index


def order(root):
    top = root / INBOX
    sources, attachments, unusable, folder_errors = [], [], [], []
    if top.is_dir():
        files = walk(top, folder_errors)
    else:
        files = []
    for rel in folder_errors:
        unusable.append({"path": (INBOX / rel).as_posix(), "reason": "unreadable"})
    for full, rel in files:
        path = (INBOX / rel).as_posix()
        ext = os.path.splitext(full.name)[1].lower()
        if ext in ATTACHMENT_EXT:
            attachments.append(path)
            continue
        reason, digest, head, st = inspect(full, ext in TEXT_EXT)
        if reason:
            unusable.append({"path": path, "reason": reason})
            continue
        basis, found = "name", name_date(full.name)
        if not found:
            basis, found = "frontmatter", frontmatter_date(head)
        if not found:
            basis, found = "mtime", mtime_key(st.st_mtime)
        sources.append({"path": path, "basis": basis, "when": found[0], "key": found[1],
                        "digest": digest, "size": st.st_size})
    index = processed_index(root, {s["size"] for s in sources})
    sources.sort(key=lambda s: (s["when"], s["path"].casefold(), s["path"]))
    out = [{"path": s["path"], "basis": s["basis"], "key": s["key"],
            "duplicate_of": index.get(s["digest"])} for s in sources]
    by_path = lambda p: (p.casefold(), p)  # noqa: E731
    attachments.sort(key=by_path)
    unusable.sort(key=lambda u: by_path(u["path"]))
    return out, attachments, unusable


def positive(value):
    try:
        n = int(value)
    except ValueError:
        n = 0
    if n < 1:
        raise argparse.ArgumentTypeError(f"must be a whole number of at least 1, not {value!r}")
    return n


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="inbox_order.py", allow_abbrev=False,
        description="List content/_raw/inbox/ in the order /b:ingest --backlog takes it.")
    parser.add_argument("--limit", type=positive, metavar="N",
                        help="put the first N sources in take (default: all)")
    parser.add_argument("--root", default=".",
                        help="the vault root, the folder that holds content/ (default: the current folder)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.root)
    if not (root / "content").is_dir():
        print(f"inbox_order: error: no content/ under {root}: run from the vault root or "
              f"pass --root", file=sys.stderr)
        return 1
    sources, attachments, unusable = order(root)
    take = [s["path"] for s in sources[:args.limit]] if args.limit else [s["path"] for s in sources]
    print(json.dumps({"sources": sources, "attachments": attachments, "unusable": unusable,
                      "take": take, "remaining": len(sources) - len(take)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
