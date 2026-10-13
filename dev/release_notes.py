#!/usr/bin/env python3
"""Print one version's section of CHANGELOG.md, without its heading, for the notes of
a GitHub Release (author tool).

Usage:  python dev/release_notes.py X.Y.Z > notes.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def section(text: str, version: str) -> str | None:
    head = re.compile(rf"^## \[{re.escape(version)}\][^\n]*\n", re.MULTILINE)
    m = head.search(text)
    if not m:
        return None
    rest = text[m.end():]
    end = re.search(r"^## \[|^---\s*$", rest, re.MULTILINE)
    return (rest[:end.start()] if end else rest).strip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)
    text = (Path(args.root) / "CHANGELOG.md").read_text(encoding="utf-8")
    notes = section(text, args.version)
    if notes is None:
        print(f"CHANGELOG.md has no ## [{args.version}] section", file=sys.stderr)
        return 1
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
