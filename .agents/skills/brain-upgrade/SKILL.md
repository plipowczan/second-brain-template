---
name: brain-upgrade
description: Use when the user says "upgrade", "update the template", "pull template updates", "zaktualizuj szablon", "aktualizacja bazy", or asks which template version this base runs. Pulls a newer release of the knowledge-base template into this base — dry run first, one review table, then apply and one commit. A base without a `.kb-template.json` stamp is adopted first (`--adopt`), in its own commit. Never touches notes in `content/`.
---

This skill's instructions are in `.claude/skills/brain-upgrade/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/brain-upgrade/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
