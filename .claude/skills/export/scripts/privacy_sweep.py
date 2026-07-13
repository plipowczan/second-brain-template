#!/usr/bin/env python3
"""Deterministic privacy-pattern sweep for /export --public (format-1 bundles).

Scans a directory of markdown files (the redacted staging copies) for hard
patterns that should never ship in a public bundle. Report-only: never edits.
The LLM audit pass catches contextual leaks (names, allusions); this net
catches machine-recognizable ones.

Usage:
    python privacy_sweep.py <dir>

Output: one JSON object on stdout:
    {"clean": bool, "files_scanned": N, "hits": [{file, line, class, context}]}
Context is a truncated line excerpt — stays local, never enters the bundle.

Exit codes: 0 clean, 1 usage error, 2 hits found.

Pattern set v1 (extend from real misses, see design OQ1). Deliberately
conservative — false positives erode trust in the sweep:
- phone shapes require '+' prefix or space/dash groups (never dots), so
  arXiv ids like 2410.14684 do not match;
- no raw entropy detection — sha256 hashes legitimately appear in notes;
  only known key prefixes and JWT structure match.
"""

import json
import re
import sys
from pathlib import Path

PATTERNS = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    # +48123456789 / +48 123 456 789 / 123-456-789 — separator groups or E.164, no dots
    ("phone", re.compile(r"(?<![\d.])(?:\+\d{1,3}[ -]?\d{3}[ -]?\d{3}[ -]?\d{3,6}|\d{3}[ -]\d{3}[ -]\d{3})(?![\d.])")),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[ ]?(?:\d[ ]?){11,30}\b")),
    # 16-digit card in groups of 4 (space/dash separated or contiguous)
    ("card", re.compile(r"(?<!\d)(?:\d{4}[ -]){3}\d{4}(?!\d)")),
    ("api-key", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|xox[bp]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}|ya29\.[0-9A-Za-z_-]{20,})")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("btc-wallet", re.compile(r"\b(?:bc1[a-z0-9]{25,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")),
    ("eth-wallet", re.compile(r"\b0x[a-fA-F0-9]{40}\b")),
]


def scan_file(path: Path, rel: str, hits: list) -> None:
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for cls, rx in PATTERNS:
            for m in rx.finditer(line):
                excerpt = line.strip()
                if len(excerpt) > 120:
                    start = max(0, m.start() - 40)
                    excerpt = "…" + line[start:start + 100].strip() + "…"
                hits.append({"file": rel, "line": lineno, "class": cls, "context": excerpt})


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: privacy_sweep.py <dir>", file=sys.stderr)
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1
    hits: list = []
    files = sorted(root.rglob("*.md"))
    for f in files:
        scan_file(f, f.relative_to(root).as_posix(), hits)
    print(json.dumps({"clean": not hits, "files_scanned": len(files), "hits": hits},
                     ensure_ascii=False, indent=2))
    return 2 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
