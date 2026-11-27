---
name: brain-review
description: 'Use when the user says "review", "weekly review", "what changed in my vault", "przegląd", or a schedule runs `/b:review`. Reports what came in since the last review, open contradictions, thin places, unanswered questions and the metrics with their trend, and ends with three moves; writes one report to `_outputs/reports/` and one log row, never a note. Do NOT use for a health audit (use `/b:lint`) or coverage analysis (use `/b:gaps`).'
---

This skill's instructions are in `.claude/skills/brain-review/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/brain-review/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
