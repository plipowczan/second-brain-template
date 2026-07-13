---
name: export
description: Use when user says "export [[Note]] ...", "export #tag", "export FOLDER", "export --public ...", "wyeksportuj notatki", "create a bundle/pack of notes". Packs selected wiki notes into a portable zip bundle (manifest + notes) importable into any other brain via /import. Two privacy levels - me (default, verbatim) and --public (redaction pipeline for bundles leaving your trust boundary). Read-only for the vault (public level writes one local report).
---

# EXPORT

## When to use

Trigger phrases: "export [[A]] [[B]]", "export #crypto", "export AI/TOOLS", "wyeksportuj",
"make a bundle of X". Produces a `brain-pack-*.zip` that another kb-template brain imports
with `/import`.

**Privacy levels:**

| Level | Flag | For | Behavior |
|-------|------|-----|----------|
| `me` | none (default) | your own brains | verbatim copies — the flow below, steps 1–5 |
| `public` | `--public` (alias `--level public`) | strangers / open publication | redaction pipeline — extra steps 3a–3c |

Unknown level value → abort before any work. A future `trusted` level may join the enum.

**Read-only guarantee:** export never creates, edits, or deletes notes and never touches
the 3 indexes. `me` writes nothing but the bundle zip. `--public` additionally writes
exactly one local redaction report to `content/_outputs/reports/` (build-excluded,
outside the index protocol) — nothing else.

**Interaction budget:** `me` = 2 prompts (selection confirm, link closure).
`--public` = 3 (plus the redaction verdict table). Never ask per note.

## Bundle format (v1)

```
brain-pack-<slug>-<YYYY-MM-DD>.zip
├─ manifest.json
└─ notes/
   └─ AI/TOOLS/Serena.md          # source folder path preserved
```

```json
{
  "format": 1,
  "source": "brain",
  "exported": "2026-07-11",
  "notes": [
    { "path": "AI/TOOLS/Serena.md", "title": "Serena", "sha256": "<hex of file bytes>" }
  ]
}
```

- `source` — this brain's name. Heuristic: `title:` frontmatter of `content/ABOUT/About.md`
  if it names the vault, else the repo folder name.
- `sha256` — hash of the exact shipped bytes (at `--public`: the redacted bytes); gives
  `/import` free integrity checks and idempotent re-import.
- **The manifest is identical in shape at every privacy level** — no privacy key, no
  per-note redaction flags. A public bundle is structurally indistinguishable from a full
  one; the only record of redaction is the local report.

## Workflow

### 1. Resolve the selector (catalog.md only — never grep content/)

Read `content/_indexes/vault-map.md`, then `content/_indexes/catalog.md`. Accepted selectors,
mixable in one call:

| Selector | Resolution |
|----------|------------|
| `[[Note]] [[Other]]` | look up each title's folder section in catalog.md → path |
| `#tag` | every catalog entry whose `[tags]` contain the tag, across all folders |
| `TOPIC/SUB` | all entries of that catalog folder section |

- **Ambiguous title** (same title in two folders): list all matching paths; the user picks
  during the confirmation step (step 2) — no extra prompt round.
- **Exclusions:** notes under `_indexes/`, `_outputs/`, `_raw/`, `_graveyard/`, `templates/`,
  any underscore-prefixed file or folder (`_privacy.md` can never ship), and non-`.md` files
  are dropped from resolution but named in the confirmation list as "omitted (excluded)".
- **Empty selection:** report "selector resolved to 0 notes" and stop. No file is created.

### 2. Confirm the selection

Show the resolved list (full paths + count) and ask once: "Pack these N notes?".
Include any ambiguity picks and exclusion notices in this same prompt. Do not proceed
without approval.

### 3. Offer depth-1 link closure (never automatic)

From `content/_indexes/graph.md` **Outgoing** lines of the selected notes, collect link
targets **outside** the selection. If any exist, show them with per-target link counts:

```
Selection links to 3 notes outside the pack:
- [[Claude Code]] (4 links)
- [[MCP]] (2)
- [[Obsidian]] (1)
Add? [all / pick / none]
```

Add approved neighbors to the selection. If no outside neighbors — skip this step silently.
At `me` level these were the final prompts; steps 4–5 run unattended.

### 3a. `--public` only — redact working copies

Load the policy, then produce a redacted **working copy** of every selected note in the
session scratchpad (never inside `content/`; sources stay byte-identical).

**Default policy** (applies to every vault):

| Class | Action |
|-------|--------|
| Secrets, credentials, keys | always cut — and flag to the user: they should not live in notes at all |
| Third-party PII: person names, client companies | always cut |
| Health data | always cut |
| Finance specifics: amounts, wallets, strategies | always cut |
| Rates, contract terms, commercial identifiers | always cut |
| Personal/commercial context | genericize ("my client's real-estate platform" → "a real-estate platform") |
| Tools used, howtos, technical opinions, the fact of using something | keep |

**Vault overrides — `content/_privacy.md`** (optional): extra always-cut terms and explicit
exceptions ("the vault owner's name is public"). Extends/overrides the defaults. Absent →
defaults alone, silently.

**Wikilink leak rule** — links targeting excluded notes or notes matching the policy:
1. De-personalize the title, keep the wikilink: `[[My Crypto Strategy]]` → `[[Crypto Strategy]]`.
2. Title itself is the private datum (person/client name) → genericize the surrounding text
   ("a client project") or cut the sentence when it loses meaning.
3. Aliased links `[[Private Note|alias]]`: keep the alias text, de-personalize the target.
Every transformation counts in "what was cut". (Deliberate exception to the import-side
"broken links stay verbatim" rule — that rule protects graph re-stitching between your own
vaults; here the title would leak to strangers.)

Per-note verdict:
- `include` — nothing to cut, original file ships;
- `redact` — redacted copy ships;
- `exclude` — unsalvageable (the note's substance is itself private, e.g. a personal
  finance strategy) — drop from the bundle instead of shipping a husk.

### 3b. `--public` only — verdict table (interaction 3)

One approvable table, whole-table approval, full diff on demand inside the same prompt:

```
Redaction (5 notes):
| note | verdict | what was cut |
| Serena | redact | client project name ×1 |
| Wiring Serena into a Codebase | redact | client monorepo context ×3, link de-personalized ×1 |
| My Crypto Strategy | exclude | unsalvageable (finance) |
| GrepRAG | include | — |
Approve? [yes / edit verdicts / show diff [[X]]]
```

### 3c. `--public` only — verification nets (autonomous)

After approval, before zipping, two nets over the redacted/included copies:

1. **Deterministic sweep** — report-only, never edits:

   ```bash
   python .claude/skills/export/scripts/privacy_sweep.py "<scratchpad>/export-staging"
   ```

   Scans for emails, phone shapes, IBAN/card numbers, API-key prefixes, JWTs, crypto
   wallets. Exit 2 + JSON hits when something survived redaction.

2. **Adversarial audit** — a fresh-context LLM pass over the same copies with the policy +
   `_privacy.md`, role: "find remaining private information".

Hits → fix the copy, log to the report. False positives (sweep context lines show them) →
dismiss in the report, no edit. A hit that **flips a verdict** (redact→exclude) →
re-present only the affected rows — the sole permitted 4th interaction, expected rare.

### 4. Pack

```bash
python .claude/skills/export/scripts/bundle.py pack \
  --source "<brain name>" \
  --out "brain-pack-<slug>-<YYYY-MM-DD>.zip" \
  "AI/TOOLS/Serena.md" "CODE/TOOLS/Git.md" ...
```

- Paths are relative to `content/`. The script re-checks exclusions, computes hashes,
  writes `manifest.json` and the note copies, prints a JSON receipt.
- At `--public`: run pack from a staging `content/`-shaped dir where `redact`-verdict
  notes are the redacted copies and `include`-verdict notes are the originals
  (`bundle.py` packs whatever bytes it is pointed at; `excluded` notes simply aren't listed).
- `<slug>` — short kebab description of the selection (e.g. `crypto`, `ai-tools`).
- Default output location: repo root. The user may give any other path.

### 5. Report

`me`: state bundle path, note count, total size, omitted-as-excluded list. Vault untouched.

`--public`: additionally write `content/_outputs/reports/export-<date>-<slug>.md` with:
selection, per-note verdicts, the full cut log (every redaction and link transformation),
sweep/audit hits and how each was resolved (fixed / dismissed as false positive), bundle
path. The report stays local — **never** goes into the bundle (its cut descriptions are
themselves a meta-leak).

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/bundle.py` | `pack` / `unpack` / `same` — deterministic bundle format tool (shared with `/import`) |
| `scripts/privacy_sweep.py` | report-only pattern sweep of redacted copies (`--public` net #1) |
| `scripts/test_bundle.py`, `scripts/test_privacy_sweep.py` | unit tests; run each with `python <path>` |
