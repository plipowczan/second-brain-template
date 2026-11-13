---
name: brain-watch
description: Use when the user says "watch", "/b:watch", "check my tools", "re-check tool status", "are my tools still alive", "what changed in my tool notes", "is X still maintained", or when a scheduled run asks for the tool check. For tool notes whose repository may have shipped a release, been archived, renamed, moved or relicensed, and for products that may have been shut down.
---

# WATCH

## When to use

Trigger phrases: "watch", "check my tools", "re-check tool status", "are my tools still
alive", "what changed in my tool notes", "is X still maintained". Also the recurring
scheduled run (monthly is a good cadence). `--dry` gives the report without touching the
vault; `--deep-budget N` (default 40) caps the deep pass.

The point: learn when a tracked project ships, gets archived, renamed or relicensed,
instead of finding out by accident. `/b:curate` decides what to retire and `/b:enhance`
rewrites a note body; this skill only re-checks and reports, and writes nothing but the
status box and its frontmatter.

## What it writes

| Step | Writes |
|------|--------|
| `scan` (cheap pass) | `scan.json` in the workspace. Never a note. |
| deep pass (agents) | `results/*.json` in the workspace. |
| `apply` | Per researched note: the status box under the H1, `status-checked`, `project-status`, and `repo:` when a rename is confirmed. Once per note: `repo:` or `homepage:` when the note has neither. The snapshot `content/_outputs/watch/snapshot.json`. |
| `report` | `content/_outputs/reports/YYYY-MM-DD_watch.md` |

It never edits a note body outside the status box, never moves, archives or deletes a
note, and never commits or pushes (the caller does). Notes that need more go into the
report: a `/b:enhance` list and a `/b:curate` list.

## Scope and fields

- **In scope:** every `type: tool` note, plus any note that already carries a
  `Status check YYYY-MM-DD` box. Skipped: `watch: false`, folders and files starting with
  `_` or `.`, and `templates/`.
- **Aggregators:** notes with `status-checked` but no box (maps, comparison notes) are
  never rewritten. The report lists them when they link a note whose status changed.
- **Frontmatter:** `repo:` (repository URL; GitHub is read, other forges get a URL
  check), `homepage:` (product URL for a closed product), `watch: false` (opt out),
  `status-checked:` (date of the last deep check), `project-status:` (one of `active`,
  `maintained`, `slowing`, `stale`, `dead`, `done`, `sunset`).
- **Seeding:** a note without `repo:`/`homepage:` gets one proposed from its own links: a
  GitHub repo whose name matches the title, else the only GitHub repo linked, else a
  product URL whose host matches the title. Several candidates are never guessed between:
  the report lists them under "Notes that need a link". `scan --seed file.json`
  (`{note path: {"repo"|"homepage"|"watch": …}}`) takes known values instead of guessing.

## Flags (cheap pass)

Compared with the snapshot of the last run. Only a change is a flag, so a repository that
has been quiet for a year is not researched every month.

| Flag | When |
|------|------|
| `gone` | the repo answers 404 (note not already `dead`/`done`/`sunset`) |
| `archived`, `disabled` | newly archived or disabled on GitHub |
| `renamed` | GitHub's `full_name` differs from the note's `repo:` (renames, transfers) |
| `licence` | the SPDX licence differs from the snapshot |
| `release` | a new major or minor release (calendar versions: a new year), or the first release |
| `stale` | no push for 180+ days, newly (note not already `stale` or retired) |
| `revived` | a commit on a `stale`/`dead`/`sunset` project after its last check |
| `unreachable` | a homepage-only note's URL answers 404/410 |

Blocks, server errors and network failures are "not checked", never a flag.

**Deep-pass set:** every flagged note, plus up to `--deep-budget` notes that are due
(never checked, or last checked `--due-days` (default 90) or more ago): never-checked
first, then notes without a repository (the cheap pass sees nothing for them), then the
oldest. Notes with no link are not researched; they are listed so a link can be added.

## Workflow

Run every command from the vault root. `SCRIPT=.claude/skills/brain-watch/scripts/watch.py`.

1. **Orient.** Read `content/_indexes/vault-map.md` (Navigation Protocol). Pick the
   workspace `WS`: for a real run `content/_raw/research-workspaces/watch-YYYY-MM-DD/`
   (git-ignored); for `--dry` a fresh directory in your scratchpad, outside the vault.
2. **Cheap pass.**
   `python $SCRIPT scan --out "$WS/scan.json" [--deep-budget N]`
   It prints the counts. It checks the GitHub rate limit first and stops fetching before
   the limit runs out; the rest is reported as skipped. `gh` must be logged in (or
   `GH_TOKEN` set) for more than 60 requests an hour.
3. **Dry run stops here:** `python $SCRIPT report "$WS/scan.json" --dry --out "$WS/report.md"`,
   then show the summary, the flags and what would be researched. Nothing in the vault
   changed.
4. **Outline.** `python $SCRIPT outline "$WS/scan.json" "$WS"` writes `outline.yaml`,
   `fields.yaml` and `results/`. Zero items: skip to step 7.
5. **Deep pass.** Split the items into groups of up to 8 and launch one `web-search-agent`
   per group, up to 4 at a time in the background; when a batch finishes, launch the next.
   Do not stop for approval between batches: the budget was the approval. Skip an item
   whose result file already exists and validates. Prompt per agent (fill in `{…}`):

   ```
   ## Task
   Research each item below and write one JSON file per item to its output path.

   {for each item: its YAML block from outline.yaml, then "Output path: {WS}/results/{result_file}"}

   ## Field Definitions
   Read {WS}/fields.yaml to get all field definitions

   ## Output Requirements
   1. Output JSON according to fields defined in fields.yaml, one file per item
   2. Read the note at the item's `note` path before you fill changes_since_note
   3. Treat cheap_pass_facts as a starting point from the GitHub API, not as proof
   4. Mark uncertain field values with [uncertain]
   5. Add uncertain array at the end of JSON, listing all uncertain field names
   6. All field values must be in English

   ## Validation
   After writing each JSON, run:
   python .claude/skills/brain-research/validate_json.py -f {WS}/fields.yaml -j {output path}
   The task is complete only after validation passes for every item.
   ```

6. **Digest.** `python $SCRIPT digest "$WS/scan.json" "$WS" --out "$WS/digest.json"`.
   A note whose lines contain a term from the "Always cut" section of
   `content/_privacy.md` or of the git-ignored `content/_privacy.local.md` is held back
   (also in its slug forms: `Acme Labs` matches `acme-labs`, `acmelabs`). So is a result
   whose `liveness` is not in the vocabulary. To correct a result by hand, put
   `{result_key: {"field": "text"}}` or `{result_key: {"liveness": …, "lines": […]}}` in
   `$WS/overrides.json` and re-run the digest. If `content/WRITING_STYLE.md` names a
   primary language other than English, translate the `lines` in `digest.json` into it
   now, keeping URLs, versions, dates and wikilinks as they are.
7. **Apply.** `python $SCRIPT apply "$WS/scan.json" --digest "$WS/digest.json"` (without
   `--digest` when step 4 had zero items). It writes the boxes, frontmatter, seeds and
   snapshot, keeps each file's line endings, and leaves everything else in the note as it
   was. Running it again on the same inputs changes nothing.
8. **Indexes.** `python .claude/skills/brain-reindex/scripts/build_indexes.py`, then add
   one line at the top of `## Recent Changes` in `vault-map.md` (keep 10):
   `- YYYY-MM-DD <N> tool notes status-checked, <M> linked (/b:watch)`.
9. **Report.** `python $SCRIPT report "$WS/scan.json" --digest "$WS/digest.json" --out content/_outputs/reports/YYYY-MM-DD_watch.md`.
10. **Tell the user:** the counts, the flags, status changes, the `/b:enhance` list, the
    `/b:curate` list, aggregators to refresh, notes that need a link, anything held back.

## Unattended (scheduled) runs

Same steps, no questions: never use AskUserQuestion. Writes are limited to the table in
"What it writes", so nothing waits for a confirmation. If the web-search agents cannot
run, do steps 1-2 and 7-9 without a digest: the report then lists the flags, and the
flagged notes stay flagged for the next run.

## Safety

- The cheap pass reads only; every GitHub call names its repository (`repos/<owner>/<name>/…`), so `gh` never falls back to the current checkout's repository.
- A network error, a block or a server error is "not checked", never `dead` or `gone`.
- Lines and links that match a private term are not written into a note or the report.
- Currency in lines is escaped as `\$`.
- Never modify `.obsidian/` or engine directories; never move, archive or delete a note.

## See also

`/b:enhance` (fix a note whose body is now wrong), `/b:curate` (retire dead notes),
`/b:research-deep` (the agent prompt this skill adapts), `/b:reindex`.
