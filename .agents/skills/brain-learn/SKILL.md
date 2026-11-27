---
name: brain-learn
description: 'Use when the user says "learn", "quiz me", "test me on X", "let me explain X back", "przepytaj mnie". Teaches a topic from the vault: explains it plainly, has the owner explain it back and names each gap (the base lacks it, its sources lack it, you missed it); `--quiz` asks graded questions. Saves the session to `_outputs/learning/` and one log row, changes no note. Do NOT use for answering a question (use `/b:qa`).'
---

This skill's instructions are in `.claude/skills/brain-learn/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/brain-learn/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
