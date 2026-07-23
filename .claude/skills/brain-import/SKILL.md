---
name: brain-import
description: Use when user says "import <file.zip>", "zaimportuj paczkę", "import bundle/pack of notes". Imports a brain-pack zip (made by /export in another brain) into this vault - validates, triages collisions, places notes into this vault's taxonomy, stamps provenance, updates all 3 indexes, writes a report. At most 2 user prompts per run.
---

# IMPORT

## When to use

Trigger: "import <path/to/brain-pack-*.zip>". The bundle was produced by `/b:export` in
another (or this) brain. Result: notes land in `content/`, indexes updated, report written.

**Interaction budget — hard rule:** at most **2 prompts** per run, each a single
approve-or-edit table, regardless of bundle size. Never ask per note.

1. **Prompt A — collision triage** (skipped when no collisions)
2. **Prompt B — folder mapping** (skipped when every incoming folder exists here)

Everything else is autonomous; outcomes go to the report.

## Bundle format

Same as `/b:export` (see `.claude/skills/brain-export/SKILL.md`): zip with `manifest.json`
(`format: 1`, `source`, `exported`, `notes[{path, title, sha256}]`) + `notes/` tree.

## Workflow

### Phase 1 — Validate (abort before any vault write)

Unpack to a **staging dir in the session scratchpad** (never inside `content/`):

```bash
python .claude/skills/brain-export/scripts/bundle.py unpack \
  --bundle "<path/to/pack.zip>" --dest "<scratchpad>/import-staging"
```

The script verifies: `format` is known (else abort naming the unsupported version),
every manifest entry exists in the zip, recomputed sha256 matches. Non-zero exit /
`"ok": false` → **abort with the script's error list; the vault is untouched.**
On success stdout carries the manifest (source, exported, notes list).

### Phase 2 — Classify (read indexes, bucket every note)

Read this vault's `content/_indexes/vault-map.md`, then the `catalog.md` sections
matching incoming paths. Bucket each manifest note:

| Bucket | Condition | Action |
|--------|-----------|--------|
| `new-direct` | no note at target path, folder exists | write at source path, no question |
| `new-unmapped` | no note at target path, folder absent from this vault | row in Prompt B |
| `identical` | note exists AND `bundle.py same <staged> <existing>` → true | auto-skip, no LLM compare, no index churn |
| `collision` | note exists, contents differ | content-compare → row in Prompt A |

For `collision`, read both versions and propose one verdict:

- `skip` — target strictly richer or equal in substance
- `merge` — incoming adds real material (name what)
- `keep-target` — target newer/better and incoming adds nothing worth weaving
- `rename` — different entities sharing a title → import as `<Title> (<source>).md`

### Phase 3 — Prompt A: collision triage (one table, or skip)

```
Collisions (3):
| note | verdict | why |
|------|---------|-----|
| Serena | skip | identical in substance, target has extra Install section |
| MCP | merge | incoming adds "Streaming" section |
| Claude Code | keep-target | target newer, richer |
Approve? [yes / edit verdicts]
```

User approves or edits verdicts as a whole. Zero collisions → skip the prompt.

### Phase 4 — Prompt B: folder mapping (one table, or skip)

For every `new-unmapped` note propose the closest folder from **this vault's**
vault-map taxonomy:

```
Missing folders (2):
| note | source folder | proposed here |
|------|---------------|---------------|
| My Crypto Strategy | CRYPTO/NOTES | INVESTMENTS/KNOWLEDGE/INFO |
Approve? [yes / adjust]
```

**Never `mkdir` a source-path folder absent from this vault's taxonomy without approval
via this table.** The target brain owns its structure (set at onboarding). The user may
still answer "create CRYPTO/NOTES" — that is approval.

### Phase 5 — Execute (autonomous)

For every note being written:

1. **New notes:** copy the staged file to the target path.
2. **Merges:** follow `/b:refactor` merge discipline — weave incoming material into the
   existing note; **never delete user-authored target content; preserve every existing
   frontmatter field.**
3. **Renames:** write incoming as `<Title> (<source>).md` at the mapped folder.
4. **Provenance stamp** on every written note (new + merged), preserving all other fields:

   ```yaml
   imported-from: <manifest.source>
   imported: <today YYYY-MM-DD>
   agent-created: true   # only if not already present
   ```

5. **Broken wikilinks: leave character-for-character intact.** Never strip to plain text,
   never rewrite, never annotate inline. A later bundle carrying the missing note
   re-stitches the graph for free. They are enumerated in the report instead.

### Phase 6 — Batch index update (one pass)

Update all three indexes covering **exactly** the executed changes (skips cause zero churn):

- `catalog.md` — add one entry per new note, update entries of merged notes
- `vault-map.md` — folder counts, top-tags, Recent Changes (one import line naming source + count)
- `graph.md` — outgoing edges of written notes + incoming edges of their targets

### Phase 7 — Mini-lint + report

Lint **only the imported set**: broken wikilinks (with occurrence counts), frontmatter
completeness. Write the report to:

```
content/_outputs/reports/import-<YYYY-MM-DD>-<source>.md
```

Contents: notes written (paths + bucket), triage verdicts as executed, folder mappings
applied, broken links with counts, skipped/identical list.

**No-op detection:** when every manifest note landed in the `identical` bucket, end with
zero prompts, zero vault writes, zero index changes, and a report line
"bundle already fully imported — no-op".

## Scripts

Uses `/b:export`'s bundle tool: `.claude/skills/brain-export/scripts/bundle.py`
(`unpack` = extract + verify, `same` = newline-normalized equality).
