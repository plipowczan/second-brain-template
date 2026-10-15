---
name: brain-onboard
description: Use when starting a fresh knowledge base from this template, or when the user says "onboard", "set up my KB", "initialize", "rozpocznij". Interviews the user, personalizes the brain (CLAUDE.md, WRITING_STYLE.md, AGENTS.md), scaffolds topic folders, and builds the indexes.
---

# ONBOARD

## When to use

A fresh clone of the KB template. Detect by the presence of `CLAUDE.template.md`
in the repo root.

**Stop first if `CLAUDE.local.md` exists in the repo root.** Only the template's own
source checkout has that file, and onboarding would turn the source into a knowledge
base (it deletes the templates and the template-development files). Change nothing, and
tell the user this checkout looks like the template source: to try onboarding, clone it
to a scratch folder first (`git clone . ../kb-onboard-test`) and run `/b:onboard` there. If `CLAUDE.template.md` is absent, the vault is already
initialized — report "already initialized" and offer to **reconfigure** by
re-running the interview from the saved `.kb-onboard.json` (Phase 4), rather than
clobbering existing files.

## Workflow

Four phases. Phase 1 interviews (one question at a time). Phases 2–4 run with the
collected answers.

### Phase 1 — Interview (use AskUserQuestion, ONE question at a time)

Collect, in order:
1. **KB name** and **owner** (free text).
2. **Primary language** (e.g. English / Polish / other).
3. **Topics/domains** — the top-level subject folders (e.g. `AI`, `BUSINESS`,
   `HEALTH`). Capture a short list.
4. **Note types** in use (default: `basic-note`, `knowledge-note`, `tool`,
   `book-note`, `answer-note`; let them add/remove).
5. **Voice**: person (first-person vs neutral) and formality (e.g. "direct and
   practical"); and whether to keep the **emoji-in-headings** convention (yes/no).
6. **Main branch** name (default `main`).

### Phase 2 — Prereq check (non-blocking)

Probe and print a ✅/⚠️ table:
- `python --version` (required for reindex/lint/render).
- `yt-dlp --version`, and when that fails `python -m yt_dlp --version` (optional — only
  for YouTube ingest; either one passing is ✅, because `yt_fetch.py` falls back to the
  module when the executable is missing or blocked).
- `ffmpeg -version` (optional — Whisper fallback).
Warn on missing; do not abort.

### Phase 3 — Scaffold (deterministic)

1. **Build the values file** `.kb-onboard.json` at the repo root from the answers.
   Map answers to the canonical variables:
   - `KB_NAME`, `KB_OWNER`, `PRIMARY_LANGUAGE`, `MAIN_BRANCH`, `VOICE_PERSON`,
     `VOICE_FORMALITY` — direct strings.
   - `NOTE_TYPES` — the chosen types joined as `basic-note | knowledge-note | ...`.
   - `emoji_headings` — boolean from the emoji answer.
   - `TOPIC_TABLE` — pre-render the topic rows as markdown table lines, one per
     topic, in the exact form:
     `| `/content/TOPIC/` | <one-line purpose> | Yes |`
     (newline-separated; this whole block becomes the value of `TOPIC_TABLE`).

2. **Render the three brain files** with `render.py`:
   ```bash
   python .claude/skills/brain-onboard/scripts/render.py --template CLAUDE.template.md \
         --values .kb-onboard.json --out CLAUDE.md
   python .claude/skills/brain-onboard/scripts/render.py --template AGENTS.template.md \
         --values .kb-onboard.json --out AGENTS.md
   python .claude/skills/brain-onboard/scripts/render.py --template content/WRITING_STYLE.template.md \
         --values .kb-onboard.json --out content/WRITING_STYLE.md
   ```
   If any render exits non-zero, STOP and show the error (a missing value means an
   interview answer wasn't captured) — fix the values and re-render. Do not delete
   the templates until all three renders succeed.

3. **Write the template stamp** once all renders succeed, while the templates still
   exist (the stamp records their hashes):
   ```bash
   python .claude/skills/brain-upgrade/scripts/upgrade.py stamp
   ```
   It writes `.kb-template.json`: the template version from `.kb-manifest.json`, the
   hashes of the template files as shipped, and the commit only when this clone sits on
   the release tag. `/b:upgrade` needs it later to tell template files from the
   owner's edits.

4. **Delete the templates and the template-development files:**
   `CLAUDE.template.md`, `AGENTS.template.md`, `content/WRITING_STYLE.template.md`, then
   every author-class file listed in `.kb-manifest.json` (`openspec/`, `dev/`,
   `CONTRIBUTING.md`):
   ```bash
   python .claude/skills/brain-upgrade/scripts/upgrade.py prune-author
   ```

5. **Create the topic folders** from the answers under `content/` (e.g.
   `content/AI/`, `content/BUSINESS/`), each with a `.gitkeep` so it is tracked.

6. **Offer to delete the example** `content/REFERENCE/` folder and the sample
   `content/_raw/inbox/sample-source.md` (ask: keep as a tutorial, or remove). Act
   on the answer.

7. **Prune note templates** in `content/templates/` to the chosen note types
   (e.g. remove `book.md` if `book-note` was dropped).

8. **Rebuild the indexes** so they match the new structure (run from the repo
   root — the script resolves `content/` relative to the current directory):
   `python .claude/skills/brain-reindex/scripts/build_indexes.py`.

### Phase 4 — Handoff

Print a short "what now":
- Drop a file in `content/_raw/inbox/` then run `/b:ingest`.
- Ask a question with `/b:qa`.
- Run `/b:lint` for a health check.
- Run `/b:upgrade` later to pull new template releases (it reads `.kb-template.json`).
Summarize the created topic folders and the personalized files. Commit
`.kb-onboard.json` and `.kb-template.json` with the rest: they travel with the base.

## Idempotence

`.kb-onboard.json` is the saved answer set. On a re-run when `CLAUDE.template.md`
is gone, offer **reconfigure**: re-read `.kb-onboard.json`, let the user adjust
answers, and re-render — but warn before overwriting an existing `CLAUDE.md`,
`AGENTS.md`, or `content/WRITING_STYLE.md`.
