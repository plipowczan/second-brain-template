---
name: brain-lint
description: Use when user says "lint", "health check", "audit". Checks vault for missing frontmatter, broken wikilinks, orphans, stub notes, inconsistent tags, TODO markers, stale content, source paths that lead nowhere and open contradictions; names a next step for every finding and ends with what to fix first; saves report to `_outputs/reports/`. Says when the vault is too small to lint.
---

This skill's instructions are in `.claude/skills/brain-lint/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/brain-lint/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
