---
name: lint
description: Use when user says "lint", "health check", "audit". Checks vault for missing frontmatter, broken wikilinks, orphans, stub notes, inconsistent tags, TODO markers, stale content; saves report to `_outputs/reports/`.
---

# LINT

## When to use

Trigger phrases: "lint", "health check", "audit". The user wants a health report for the vault.

## Workflow

Check the vault for the following classes of issues:

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

Save the report to `content/_outputs/reports/YYYY-MM-DD_health-report.md`. Print summary counts to the user (issues per class).

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
