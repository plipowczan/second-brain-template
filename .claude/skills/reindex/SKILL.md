---
name: reindex
description: Use when user says "reindex", "update indexes", "rebuild indexes", "odśwież indeksy", or when an index file is missing/stale. Full rebuild of `_indexes/vault-map.md`, `catalog.md`, `graph.md` from all wiki notes.
---

# REINDEX

## When to use

Trigger phrases: "reindex", "update indexes", "rebuild indexes", "odśwież indeksy", or bootstrap. Use when:

- Indexes are missing or corrupted.
- An index `updated:` timestamp is stale relative to the newest note file.
- The user explicitly requests a reindex.

## Workflow

Full rebuild of all three index files from scratch is done by a deterministic script — **run it, don't hand-edit the indexes.**

```bash
python .claude/skills/reindex/scripts/build_indexes.py
```

Requires `python` on PATH with `PyYAML` (`pip install pyyaml` if missing). On success it prints a one-line summary, e.g. `OK notes=301 edges=1564 incoming_targets=228 tags=421 dated=297`. It overwrites `content/_indexes/{vault-map,catalog,graph}.md` in place with a fresh `updated:` timestamp on each.

After running, **spot-check the output** before reporting done:

1. `total_notes` / `entries` / `nodes` match the script's printed `notes=` count.
2. Any notes you just created/renamed appear in `catalog.md` and resolve as graph nodes (`grep "^FOLDER/Title <-" graph.md`).
3. No ghost targets (trailing `\`, unresolved title-links). If a wikilink target doesn't resolve, the usual cause is **filename ≠ wikilink** — Obsidian resolves links by filename, so rename the file to match `[[Link Text]]`, then re-run.

### What the script does (for reference / manual fallback)

1. Scans all `.md` files under `content/`, excluding `_raw/`, `_indexes/`, `_outputs/`, `templates/`, and `.obsidian/`.
2. Per note: parses YAML frontmatter (title, date, type, tags, summary); summary falls back to the first meaningful body line (~15 words) if no `summary:` field. Extracts wikilinks, handling aliases (`[[A|B]]`), header anchors (`[[A#h]]`), and Obsidian table-escaped pipes (`[[A\|B]]`).
3. Builds `vault-map.md` — folder table (counts, type breakdown, top-5 tags), tag cloud, 15 most-recent dated notes.
4. Builds `catalog.md` — one entry line per note in folder sections, per CLAUDE.md format.
5. Builds `graph.md` — outgoing links (targets resolved to full paths via filename) and reverse-mapped incoming links.

If editing the generation logic, change `scripts/build_indexes.py` (not the indexes directly), then re-run.

## See also

CLAUDE.md "Navigation Protocol" — defines the exact format of each index file.
