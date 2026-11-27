#!/usr/bin/env python3
"""Broken wikilinks and orphan notes. Run from the vault root (the folder that holds
content/); prints {"broken", "orphan_count", "orphans"} as JSON.

Importable: scan() walks the notes and resolves their links, and metrics.py builds its
link metrics on it, so lint and the review count orphans the same way.

A link resolves by the last part of its target, the note's file name without `.md`,
with a case-insensitive fallback; folders in the target do not pick a file. A note is an
orphan when no link anywhere (its own included) resolves to its name, compared without
case. Links to templates/, attachments and images or PDFs are valid but name no note."""
import json
import os
import re
import sys

ROOT = "content"
EXCLUDE_TOP = {"_raw", "_indexes", "_outputs", "_graveyard", "templates", "ATTACHMENTS", ".obsidian"}
EXCLUDE_FILES = {"WRITING_STYLE.md", "WRITING_STYLE_ANALYSIS.md", "_index.md"}
LINK = re.compile(r'\[\[([^\]]+)\]\]')
FILE_EXT = (".jpg", ".jpeg", ".webm", ".gif", ".svg", ".webp")


def name_key(name):
    """The form in which lint compares note names: case does not count."""
    return name.lower()


def walk_notes(root=ROOT):
    """[(path, name)] for every note under root, in os.walk order. path is root joined
    with the note's relative path, with forward slashes; name is the file name without
    `.md`. Skips the infrastructure folders, templates, meta files and `_` files."""
    notes = []
    for dp, dn, fns in os.walk(root):
        rel = os.path.relpath(dp, root)
        if rel != ".":
            top = rel.split(os.sep)[0]
            if top in EXCLUDE_TOP or top.startswith("."):
                dn[:] = []
                continue
        for fn in fns:
            if not fn.endswith(".md"):
                continue
            if fn.endswith(".template.md") or fn in EXCLUDE_FILES:
                continue
            if fn.startswith("_"):
                continue  # underscore prefix = infrastructure, not a note (as in build_indexes.py)
            notes.append((os.path.join(dp, fn).replace("\\", "/"), fn[:-3]))
    return notes


def strip_code(t):
    """Remove fenced blocks and inline code spans, whose links are examples."""
    t = re.sub(r'```.*?```', '', t, flags=re.DOTALL)
    t = re.sub(r'`[^`\n]*`', '', t)
    return t


def link_targets(text):
    """The target of every wikilink outside code, in order: alias (`|`, also the
    table-escaped `\\|`) and heading (`#`) removed, blanks dropped."""
    out = []
    for raw in LINK.findall(strip_code(text)):
        tgt = raw.replace("\\|", "|").split("|")[0].split("#")[0].strip()
        if tgt:
            out.append(tgt)
    return out


def scan(root=ROOT):
    """Walk the notes under root and resolve every link. Returns a dict:

    - notes: [(path, name)] as walk_notes() gives them;
    - incoming: the set of names links resolve to (a link's last part when a note has
      exactly that name, else its lower-case form);
    - broken: {path: [target, ...]} for links that resolve to nothing, in walk order;
    - orphans: names of the notes no link resolves to, sorted (a name twice when two
      orphan files share it);
    - orphan_notes: [(path, name)] of those notes, in walk order;
    - edges: [(source path, target name)], one per link that resolves to a note,
      self-links included; the target is the form that went into incoming;
    - other_links: [(source path, target)] for valid links that name no note:
      templates/, attachments, images and PDFs."""
    notes = walk_notes(root)
    names = set()
    paths = set()
    for p, name in notes:
        relp = os.path.relpath(p, root).replace("\\", "/")[:-3]
        names.add(name)
        paths.add(relp)
        paths.add(relp.lower())
    names_l = {name_key(n) for n in names}

    broken, incoming, edges, other = {}, set(), [], []
    for p, _ in notes:
        with open(p, encoding="utf-8") as f:
            text = f.read()
        for tgt in link_targets(text):
            base = tgt.split("/")[-1]
            low = tgt.lower()
            ok = (tgt in paths or low in paths or base in names or name_key(base) in names_l
                  or tgt.startswith("templates/") or low.endswith(".png") or low.endswith(".pdf")
                  or "ATTACHMENTS" in tgt or low.endswith(FILE_EXT))
            if not ok:
                broken.setdefault(p, []).append(tgt)
            elif base in names:
                incoming.add(base)
                edges.append((p, base))
            elif name_key(base) in names_l:
                incoming.add(name_key(base))
                edges.append((p, name_key(base)))
            else:
                other.append((p, tgt))

    incoming_l = {name_key(x) for x in incoming}
    orphan_notes = [(p, n) for p, n in notes if n not in incoming and name_key(n) not in incoming_l]
    return {"notes": notes, "incoming": incoming, "broken": broken,
            "orphans": sorted(n for _, n in orphan_notes), "orphan_notes": orphan_notes,
            "edges": edges, "other_links": other}


def report(result):
    """The JSON object the script prints."""
    return {"broken": result["broken"], "orphan_count": len(result["orphans"]),
            "orphans": result["orphans"]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # avoid cp1252 crash on non-Latin content
    print(json.dumps(report(scan(ROOT)), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
