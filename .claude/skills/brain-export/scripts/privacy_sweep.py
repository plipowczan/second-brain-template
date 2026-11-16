#!/usr/bin/env python3
"""Deterministic privacy-pattern sweep for /export --public (format-1 bundles).

Scans a directory of markdown files (the redacted staging copies) for hard
patterns that should never ship in a public bundle. Report-only: never edits.
The LLM audit pass catches contextual leaks (names, allusions); this net
catches machine-recognizable ones.

Usage (run from the vault root, or pass --root):
    python privacy_sweep.py [--root <vault>] <dir>
    python privacy_sweep.py [--root <vault>] --terms

Sweep output: one JSON object on stdout:
    {"clean": bool, "files_scanned": N, "terms": {file: count | null},
     "hits": [{file, line, class, context}]}
Context is a truncated line excerpt with every private term masked as
[private]. It stays local and never enters the bundle. A file path that
contains a private term is a hit on line 0. "terms" counts the always-cut
terms read from each privacy file; null means the file is not there.

--terms prints the always-cut terms the redaction step must cut:
    {"terms": [{"term", "forms"}], "sources": {file: count | null}}

Exit codes: 0 clean (or --terms), 1 usage error, 2 hits found.

Private terms come from the "## Always cut" section of content/_privacy.md
and of the git-ignored content/_privacy.local.md, parsed and matched as
brain-watch does: HTML comments are ignored, each term also matches joined,
hyphenated and underscored, and without diacritics when that leaves at least
four letters ("Łąka Wiśnia" → laka-wisnia), case does not matter, and a term
never matches inside a longer word.

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
import unicodedata
from pathlib import Path

PRIVACY_FILES = ("_privacy.md", "_privacy.local.md")

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


# --- Private terms. private_terms(), term_forms() and private_hit() behave like
# their namesakes in brain-watch/scripts/watch.py, so /b:watch and /b:export
# --public cut the same names. Change both together: test_privacy_sweep.py
# compares the two whenever brain-watch is installed next to this skill.

def terms_by_source(root):
    """{privacy file name: its always-cut terms, or None when the file is not there}."""
    out = {}
    for name in PRIVACY_FILES:
        p = Path(root) / "content" / name
        if not p.exists():
            out[name] = None
            continue
        found = []
        text = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S)
        sec = re.search(r"^##\s+Always cut[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
        for line in (sec.group(1).splitlines() if sec else []):
            m = re.match(r"\s*[-*]\s+(.+)", line)
            if not m:
                continue
            item = m.group(1).strip()
            q = re.match(r'"([^"]+)"|“([^”]+)”', item)
            term = (q.group(1) or q.group(2)) if q else re.split(r"\s+[—–-]\s+", item)[0].strip()
            if len(term) >= 2 and term not in found:
                found.append(term)
        out[name] = found
    return out


def private_terms(root):
    """Terms from the "Always cut" section of content/_privacy.md and of the git-ignored
    content/_privacy.local.md (for names whose mere presence in the repository is a leak)."""
    terms = []
    for found in terms_by_source(root).values():
        for t in found or []:
            if t not in terms:
                terms.append(t)
    return terms


def fold(s):
    """s without diacritics: ł → l, then NFKD with the combining marks dropped
    ("Żółw Łąka" → "Zolw Laka"), as names are often written in slugs and URLs."""
    s = unicodedata.normalize("NFKD", s.replace("ł", "l").replace("Ł", "L"))
    return "".join(c for c in s if not unicodedata.combining(c))


def term_forms(term):
    """A term as written and as it shows up in slugs and URLs: "Acme Labs" also matches
    acmelabs, acme-labs and acme_labs, and "Łąka Wiśnia" also lakawisnia, laka-wisnia.
    A folded form shorter than 4 letters is left out: "Wąs" would match "was"."""
    words = re.split(r"[\s_-]+", term.strip())
    forms = {term.strip(), "".join(words), "-".join(words), "_".join(words)}
    if len(re.sub(r"\W", "", fold(term))) >= 4:
        forms |= {fold(f) for f in forms}
    return forms - {""}


def private_hit(text, terms):
    return any(re.search(r"(?<![^\W_])" + re.escape(form) + r"(?![^\W_])", text, re.I)
               for t in terms for form in term_forms(t))


def mask(text, terms):
    """text with every private term (and its slug forms) replaced by [private]."""
    for t in terms:
        for form in sorted(term_forms(t), key=len, reverse=True):
            text = re.sub(r"(?<![^\W_])" + re.escape(form) + r"(?![^\W_])", "[private]", text, flags=re.I)
    return text


# --- Sweep

def excerpt(line, start, terms=()):
    """The line with private terms masked, cut to 100 characters around start when long.
    Masking comes first, so the cut can never leave part of a term in the excerpt."""
    masked = mask(line, terms)
    start = len(mask(line[:start], terms))
    text = masked.strip()
    if len(text) > 120:
        s = max(0, start - 40)
        text = "…" + masked[s:s + 100].strip() + "…"
    return text


def scan_file(path: Path, rel: str, hits: list, terms=()) -> None:
    if terms and private_hit(rel, terms):
        hits.append({"file": rel, "line": 0, "class": "private-term", "context": "(file path)"})
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for cls, rx in PATTERNS:
            for m in rx.finditer(line):
                hits.append({"file": rel, "line": lineno, "class": cls,
                             "context": excerpt(line, m.start(), terms)})
        if terms and private_hit(line, terms):
            hits.append({"file": rel, "line": lineno, "class": "private-term",
                         "context": excerpt(line, 0, terms)})


def parse_args(argv):
    """(root, dir, terms_only), or None on a usage error."""
    root, rest, terms_only = ".", [], False
    it = iter(argv)
    for a in it:
        if a == "--root":
            root = next(it, None)
            if root is None:
                return None
        elif a == "--terms":
            terms_only = True
        elif a.startswith("-"):
            return None
        else:
            rest.append(a)
    if len(rest) > 1 or terms_only == bool(rest):
        return None
    return root, (rest[0] if rest else None), terms_only


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # avoid a cp1252 crash on non-Latin terms
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args is None:
        print("usage: privacy_sweep.py [--root <vault>] <dir>\n"
              "       privacy_sweep.py [--root <vault>] --terms", file=sys.stderr)
        return 1
    root, target, terms_only = args
    if not (Path(root) / "content").is_dir():
        # From the wrong directory the private terms would silently be missing.
        print(f"error: no content/ under {root}: run from the vault root or pass --root",
              file=sys.stderr)
        return 1
    by_source = terms_by_source(root)
    terms = private_terms(root)
    counts = {name: (None if found is None else len(found)) for name, found in by_source.items()}
    if terms_only:
        print(json.dumps({"terms": [{"term": t, "forms": sorted(term_forms(t))} for t in terms],
                          "sources": counts}, ensure_ascii=False, indent=2))
        return 0
    tree = Path(target)
    if not tree.is_dir():
        print(f"error: not a directory: {tree}", file=sys.stderr)
        return 1
    hits: list = []
    files = sorted(tree.rglob("*.md"))
    for f in files:
        scan_file(f, f.relative_to(tree).as_posix(), hits, terms)
    print(json.dumps({"clean": not hits, "files_scanned": len(files), "terms": counts,
                      "hits": hits}, ensure_ascii=False, indent=2))
    return 2 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
