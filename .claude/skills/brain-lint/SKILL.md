---
name: brain-lint
description: Use when user says "lint", "health check", "audit". Checks vault for missing frontmatter, broken wikilinks, orphans, stub notes, inconsistent tags, TODO markers, stale content, source paths that lead nowhere and open contradictions; names a next step for every finding and ends with what to fix first; saves report to `_outputs/reports/`. Says when the vault is too small to lint.
---

# LINT

## When to use

Trigger phrases: "lint", "health check", "audit". The user wants a health report for the vault.

## Workflow

1. **Run the scanners** (see Scripts). If `lint_scan.py` reports a `total` below **10** notes, tell the user it is too early for a lint — with that few notes there are no patterns to find and every finding is noise — give the count, and stop. Save no report.
2. Check the vault for the following classes of issues:
   1. Missing or incomplete frontmatter (no `title`, `date`, `tags`, or `type`).
   2. Broken wikilinks (cross-reference `content/_indexes/graph.md` against actual files).
   3. Orphan notes (no incoming wikilinks).
   4. Stub notes (very short body, mostly empty sections).
   5. Inconsistent tags (typos, near-duplicates like `book` vs `books`).
   6. Outstanding TODO markers (`#todo`, `#todo/replace`, `#todo/complete`).
   7. Missing `summary:` field in frontmatter.
   8. Notes that should logically link to one another but do not (semantic neighbors absent from `graph.md`).
   9. Stale content (notes with `date:` older than 1 year and no `agent-reviewed:` within the last year).
   10. Template compliance — every note's `type:` matches one of the allowed values from CLAUDE.md.
   11. **Warning:** source paths that lead nowhere — a `_raw/` path in `source:` / `sources:` that does not exist (`missing_source_file`).
   12. **Warning:** open contradictions — notes carrying a `> [!contradiction]` callout the owner has not resolved (`contradiction`).
3. **Write the report** to `content/_outputs/reports/YYYY-MM-DD_health-report.md`:
   - **Every finding names the note and the next step** — the edit to make or the skill to run. For example:
     - `[[Note]] — no summary: add a one-line summary:`
     - `[[Note]] — stub (120 chars): run /b:enhance [[Note]]`
     - `[[Note]] — source _raw/inbox/talk.md is gone: replace it with _raw/processed/2026-07-02_talk.md`
     - `[[Note]] — 2 open contradictions: decide which claim holds, then remove the callout`
   - **Issues and warnings apart.** The classes the scanner names in `warnings` go under a **Warnings** heading: they never block a commit and need no immediate fix. Everything else goes under **Issues**.
   - **Missing source paths:** with `fix=`, give that path as the replacement; with `candidates=`, list them and ask the owner to pick the right one; with neither, the file is gone — say so, and suggest finding the source again or replacing the path with a description.
   - **End with "Fix first"**: up to five items, ordered by what the fix unblocks:
     1. findings that hide a note from other checks — missing frontmatter, unknown type, schema violation;
     2. single fixes that clear many findings at once — one tag rename used across many notes, one moved file cited by many notes, a batch of source paths that all have a `fix=`;
     3. findings that concern one note.
   - **A clean report** — no issues and no warnings — says that this means the vault is in order (frontmatter, links, indexes, source paths), not that its content is true, and points to `LIMITS.md`.
4. Print to the user the counts per class (warnings apart from issues) and the "Fix first" list. Before telling the user the vault is in good shape, read `LIMITS.md` (repository root) and keep "in order" apart from "true"; if the file is missing, say so.

## Scripts

Run the two canonical scanners from the vault root instead of ad-hoc greps (both emit JSON, UTF-8 safe):

- `python .claude/skills/brain-lint/scripts/lint_scan.py` — classes 1, 4, 6, 9, 10 (frontmatter, stub, TODO, stale, type/schema) + `title_filename_mismatch`, and the warning classes 11 (`missing_source_file`, with `fix=` or `candidates=` for inbox paths that ingest has archived) and 12 (`contradiction`, with the number of callouts per note). Its JSON has `total`, `issues`, `counts` and `warnings` — the list of advisory class names.
- `python .claude/skills/brain-lint/scripts/lint_links.py` — classes 2, 3 (broken wikilinks + orphans). Resolves aliases (`[[Note|alias]]`, table-escaped `[[Note\|alias]]`), anchors (`#…`), path links, `templates/`, and asset embeds (png/pdf/jpg/webm/gif/svg/webp/ATTACHMENTS).

Feed their JSON into the report. Classes 5 (tag near-dupes) and 8 (missing semantic links) still need human judgment. Note: `lint_links.py` reports *raw* broken links — triage into asset-embeds / prose examples / skill-refs / genuinely-missing before quoting a headline number.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
`LIMITS.md` — what a clean lint does not tell you.
