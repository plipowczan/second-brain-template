---
name: brain-qa
description: Use when user says "research X", "what do my notes say about X", "co mam w notatkach o X". Synthesizes an answer from the vault citing notes, shows both sides of marked contradictions, and saves substantive answers to `_outputs/answers/` with what they rest on and what the vault could not answer. `--no-save` answers without writing.
---

This skill's instructions are in `.claude/skills/brain-qa/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/brain-qa/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
