---
name: brain-ingest
description: 'Use when user says "ingest", "process inbox", "przetworz nowe pliki", or when files appear in `content/_raw/inbox/`. Turns raw sources into wiki notes across every note they touch: shows one plan before writing, marks contradictions instead of overwriting, records the archive path as the source, updates all 3 indexes and the log. `--backlog [N]` takes the N oldest sources (10 by default) and stops, for a large inbox; `--batch` skips the plan.'
---

This skill's instructions are in `.claude/skills/brain-ingest/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/brain-ingest/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
