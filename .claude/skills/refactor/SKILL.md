---
name: refactor
description: Use when the user says "rename note", "move note", "merge notes", "split note", or "refactor [[Note]]". Renames, moves, merges, or splits notes while repairing every wikilink and rebuilding the indexes.
---

# REFACTOR

## When to use

Restructuring notes without breaking wikilinks: rename, move, merge, or split.

Run all commands from the repo root (the scripts resolve `content/` relative to
the current directory). After any operation, rebuild indexes:
`python .claude/skills/reindex/scripts/build_indexes.py`.

## Rename or move

```bash
python .claude/skills/refactor/scripts/refactor.py rename --old "Old Title" --new "New Title"
```
Renames the file, rewrites every `[[Old Title]]` reference (preserving `|alias`
and `#heading`), and updates the note's own `title:`. To **move** a note to a
different folder, run `rename` (if also retitling), then move the file with `git mv`
— wikilinks resolve by filename, so moving the file alone does not break links;
just reindex afterward.

## Merge B into A

1. Append B's body into A (de-duplicate overlapping content).
2. Re-point links: `python .claude/skills/refactor/scripts/refactor.py relink --old "B" --new "A"`.
3. Delete B's file.
4. Reindex.

## Split A into A + C

1. Create the new note C (correct frontmatter) and move the relevant section into it.
2. Add `[[C]]` from A and `[[A]]` from C so the two stay connected.
3. Reindex.

## After every operation

Rebuild indexes and run `/lint` to confirm no broken links were introduced.
