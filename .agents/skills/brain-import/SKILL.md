---
name: brain-import
description: Use when user says "import <file.zip>", "zaimportuj paczkę", "import bundle/pack of notes". Imports a brain-pack zip (made by /b:export in another brain) into this vault - validates, triages collisions, places notes into this vault's taxonomy, stamps provenance, updates all 3 indexes, writes a report. At most 2 user prompts per run.
---

This skill's instructions are in `.claude/skills/brain-import/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/brain-import/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
