# AGENTS.md

This file mirrors the project's agent instructions for tools that read `AGENTS.md`
(e.g. Codex, Gemini CLI) instead of `CLAUDE.md`.

**The authoritative instructions live in `CLAUDE.md`. Read it and follow it.**

## Quick summary

- This is "{{KB_NAME}}", a knowledge base owned by {{KB_OWNER}}.
- It is an Obsidian-style markdown vault under `content/`. No publishing pipeline.
- Primary language: {{PRIMARY_LANGUAGE}}. Work on the `{{MAIN_BRANCH}}` branch.
- Before any vault operation, read `content/_indexes/vault-map.md` first
  (progressive disclosure — see `CLAUDE.md` → "Navigation Protocol").
- After every note write, update the three indexes (or run
  `python .claude/skills/reindex/scripts/build_indexes.py`).
- Follow `content/WRITING_STYLE.md` when writing notes.
