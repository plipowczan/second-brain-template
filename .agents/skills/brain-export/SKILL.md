---
name: brain-export
description: 'Use when user says "export [[Note]] ...", "export #tag", "export FOLDER", "export --public ...", "wyeksportuj notatki", "create a bundle/pack of notes". Packs selected wiki notes into a portable zip bundle (manifest + notes) importable into any other brain via /b:import. Two privacy levels - me (default, verbatim) and --public (redaction pipeline for bundles leaving your trust boundary). Read-only for the vault (public level writes one local report).'
---

This skill's instructions are in `.claude/skills/brain-export/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/brain-export/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
