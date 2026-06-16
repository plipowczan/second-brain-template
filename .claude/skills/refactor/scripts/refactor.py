#!/usr/bin/env python3
"""Note surgery with link integrity.

Primitives:
  rename  — rename a note file, rewrite every wikilink that targets it (keeping
            |alias and #heading), and update the note's own `title:`.
  relink  — rewrite wikilink targets across the vault WITHOUT renaming a file
            (used by the refactor skill to merge notes).

Merge and split are orchestrated by the refactor skill on top of these.

Usage:
  python refactor.py rename --old "Old Title" --new "New Title"
  python refactor.py relink --old "Old Title" --new "Target Title"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

CONTENT = "content"
EXCLUDE = {"_raw", "_indexes", "_outputs", "templates", ".obsidian", "ATTACHMENTS"}
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")


class RefactorError(Exception):
    pass


def iter_notes(root=CONTENT):
    for dp, dn, fns in os.walk(root):
        rel = os.path.relpath(dp, root)
        if rel != ".":
            top = rel.split(os.sep)[0]
            if top in EXCLUDE or top.startswith("."):
                dn[:] = []
                continue
        for fn in fns:
            if fn.endswith(".md"):
                yield os.path.join(dp, fn)


def find_note(title, root=CONTENT):
    matches = [p for p in iter_notes(root) if os.path.basename(p)[:-3] == title]
    if not matches:
        raise RefactorError(f"no note titled {title!r}")
    if len(matches) > 1:
        raise RefactorError(f"ambiguous title {title!r}: {sorted(matches)}")
    return matches[0]


def rewrite_link_target(inside, old, new):
    """Given the text inside [[...]], return the rewritten inside if its target
    basename equals `old`, else None (leave untouched)."""
    target = inside
    alias = heading = ""
    if "|" in target:
        target, rest = target.split("|", 1)
        alias = "|" + rest
    if "#" in target:
        target, rest = target.split("#", 1)
        heading = "#" + rest
    base = target.split("/")[-1]
    if base != old:
        return None
    prefix = target[: len(target) - len(base)]
    return f"{prefix}{new}{heading}{alias}"


def rewrite_text(text, old, new):
    def repl(m):
        out = rewrite_link_target(m.group(1), old, new)
        return f"[[{out}]]" if out is not None else m.group(0)
    return WIKILINK.sub(repl, text)


def relink(old, new, root=CONTENT):
    changed = []
    for p in list(iter_notes(root)):
        txt = open(p, encoding="utf-8").read()
        new_txt = rewrite_text(txt, old, new)
        if new_txt != txt:
            open(p, "w", encoding="utf-8").write(new_txt)
            changed.append(p.replace("\\", "/"))
    return {"changed": sorted(set(changed))}


def rename(old, new, root=CONTENT):
    src = find_note(old, root)
    dst = os.path.join(os.path.dirname(src), new + ".md")
    if os.path.exists(dst):
        raise RefactorError(f"target already exists: {dst}")
    changed = []
    for p in list(iter_notes(root)):
        txt = open(p, encoding="utf-8").read()
        new_txt = rewrite_text(txt, old, new)
        if p == src:
            new_txt = re.sub(
                r'(?m)^(title:\s*")' + re.escape(old) + r'(")',
                r"\g<1>" + new + r"\g<2>", new_txt)
        if new_txt != txt:
            open(p, "w", encoding="utf-8").write(new_txt)
            changed.append(p.replace("\\", "/"))
    os.rename(src, dst)
    return {"renamed": [src.replace("\\", "/"), dst.replace("\\", "/")],
            "changed": sorted(set(changed))}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Note surgery with link integrity.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("rename", "relink"):
        sp = sub.add_parser(name)
        sp.add_argument("--old", required=True)
        sp.add_argument("--new", required=True)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # avoid cp1252 crash on non-Latin content
    try:
        result = rename(args.old, args.new) if args.cmd == "rename" else relink(args.old, args.new)
    except RefactorError as e:
        print(f"refactor error: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
