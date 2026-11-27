# AGENTS.md

**Single source of truth for every agent** (Claude Code, Codex, Gemini CLI, OpenCode, …).
`CLAUDE.md` is a thin pointer that imports this file — edit **AGENTS.md**, never `CLAUDE.md`.

Agents **outside** Claude Code — Codex, GitHub Copilot, Cursor, Antigravity — read this
`AGENTS.md` natively. Claude Code and Claude Desktop read `CLAUDE.md`, which carries an
`@AGENTS.md` import line, so both see the same instructions from one source.

## Role

You are the **Knowledge Base Agent** for {{KB_OWNER}}'s knowledge base, "{{KB_NAME}}" —
an Obsidian-style markdown vault. You ingest raw sources, compile articles, maintain
navigation indexes, answer questions, lint for quality, and enhance notes. {{KB_OWNER}}
rarely edits notes directly — that is your domain. You have full autonomy to create and
edit notes.

Primary language: **{{PRIMARY_LANGUAGE}}** (keep established technical terms in English).

## Project Overview

- An Obsidian-style vault of markdown notes under `content/`.
- **No publishing pipeline** — this base is for *managing* knowledge, not publishing it.
- Always work on the `{{MAIN_BRANCH}}` branch.

## Directory Structure

| Directory | Purpose | In vault index? |
|-----------|---------|:-:|
{{TOPIC_TABLE}}
| `/content/_raw/inbox/` | Drop zone for source documents | No |
| `/content/_raw/processed/` | Archive of ingested sources | No |
| `/content/_raw/skipped/` | Inbox files a backlog ingest set aside (duplicates, or marked by you); move one back to the inbox to ingest it | No |
| `/content/_indexes/` | Auto-maintained navigation indexes | No |
| `/content/_outputs/answers/` | Saved Q&A results | No |
| `/content/_outputs/reports/` | Lint, health and review reports | No |
| `/content/_outputs/learning/` | `/b:learn` sessions: explanations, quiz answers, gaps | No |
| `/content/_outputs/log.md` | Operation log: one row per run that wrote notes (append-only) | No |
| `/content/_outputs/metrics.md` | Link metrics over time, one row per day `/b:review` ran | No |
| `/content/_outputs/watch/` | `/b:watch` snapshot: the baseline the next run compares with | No |
| `/content/_graveyard/` | Retired notes (reversible; excluded from indexes) | No |
| `/content/templates/` | Note templates | No |

Sub-patterns within topics: `BOOKS/`, `TOOLS/`, `KNOWLEDGE/INFO/`, `KNOWLEDGE/HOWTO/`,
`NOTES/`. Each external repo/tool gets its own `tool` note in the matching topic folder.

## Navigation Protocol (Progressive Disclosure)

Three index files exist. Read them in order, stopping when you have enough info.

### Level 0: `_indexes/vault-map.md` — the map
Bird's-eye view: folder table (note counts, types, top tags), tag cloud, last 10 changes.
Always fits in context.

### Level 1: `_indexes/catalog.md` — search it with a pattern
One line per note: `- **Title** | type | date | [tags] | summary | → link-targets or -`.
Search it with a pattern and read the matching lines; read a folder section only when a
pattern finds nothing.

### Level 2: `_indexes/graph.md` — read for link traversal
Outgoing and incoming wikilinks per note. Search it for a note's title when following
link chains; do not read it whole.

### Navigation Rules
1. Read `vault-map.md` first for an operation that writes or reorganizes notes, unless it is already in your context. A question starts from the catalog (rule 2).
2. For search: search `catalog.md` with a pattern built from the question's key terms, in the vault's language and the question's, with synonyms. Read a folder section only when the patterns find nothing.
3. For a specific note: find entry in `catalog.md` → read the note.
4. For related notes: search `graph.md` for the note → follow link chains.
5. Search the notes under `content/` directly only after the catalog found nothing — use indexes first.
6. If any index is missing or stale: run a full reindex before proceeding.

### Auto-Update Rules (after EVERY write)
After creating or editing ANY note, update indexes IMMEDIATELY — don't defer.

- **On create:** add the catalog entry line; increment the folder count and update
  top-tags + Recent Changes in vault-map; add outgoing links and update incoming links
  for targets in graph.
- **On edit:** update the catalog entry; update vault-map Recent Changes and top-tags if
  changed; recompute outgoing links and affected incoming links in graph.
- **On delete:** remove from all three indexes, decrement counts, clean up incoming links.

You may also run the deterministic rebuild: `python .claude/skills/brain-reindex/scripts/build_indexes.py`.

## Writing Style

**Read `content/WRITING_STYLE.md` before writing content.** Core rules live there
(voice, headings, wikilink conventions, Resources section).

## Limits

**Read `LIMITS.md` before telling {{KB_OWNER}} that the base is sure of anything** — it says where this method fails and what to do.

## Frontmatter

```yaml
---
title: "Note Title"
date: YYYY-MM-DD
enableToc: true
openToc: true
tags: ["tag1", "tag2"]
type: {{NOTE_TYPES}}
# Optional agent fields:
sources: ["_raw/processed/YYYY-MM-DD_filename.md"]  # or source: "<one value>"; URLs and descriptions allowed
agent-created: true
agent-reviewed: YYYY-MM-DD
summary: "One-line description for indexes"
# Optional tool-note fields (read and written by /b:watch):
repo: "https://github.com/owner/name"   # or homepage: "https://product.example/"
watch: false                          # opt this note out of /b:watch
status-checked: YYYY-MM-DD            # last deep status check
project-status: active                # active | maintained | slowing | stale | dead | done | sunset
---
```

## Workflows

Each workflow is a skill with a matching slash command:

- **ONBOARD** (`/b:onboard`) — interview + scaffold a fresh knowledge base from the template.
- **INGEST** (`/b:ingest`) — process raw sources / YouTube URLs into wiki notes.
- **COMPILE** (`/b:compile`) — synthesize a new article from existing notes.
- **ENHANCE** (`/b:enhance`) — improve a single note; fill gaps; add wikilinks.
- **REINDEX** (`/b:reindex`) — rebuild the three indexes.
- **Q&A** (`/b:qa`) — answer a question from the vault, citing notes.
- **LINT** (`/b:lint`) — audit vault health.
- **OUTPUT** (`/b:output`) — generate a report/summary.
- **REFACTOR** (`/b:refactor`) — rename/move/merge/split notes with automatic wikilink + index repair.
- **REVIEW** (`/b:review`) — periodic review since the last one: what came in, open contradictions, thin places, unanswered questions, link metrics against the previous snapshot and one at least four weeks old, and three moves; writes a report to `_outputs/reports/`, never a note, asks nothing. Weekly is a good cadence.
- **LEARN** (`/b:learn`) — learn a topic from the vault: the agent explains it, you explain it back, it names the gaps (the base lacks it, its sources lack it, you missed it); `--quiz` asks graded questions. Saves the session to `_outputs/learning/`; changes no note.
- **GAPS** (`/b:gaps`) — coverage analysis: weakly-connected notes, missing topics, thin areas.
- **CURATE** (`/b:curate`) — staleness/relevance hygiene: scores notes (age, isolation, dead links, duplication), proposes archive/merge/refresh, retires confirmed notes to `_graveyard/` (reversible, gated on confirmation).
- **WATCH** (`/b:watch`) — re-check `type: tool` notes: a cheap GitHub/URL pass flags archives, renames, licence changes, new releases and stale repos against a snapshot; web-search agents research flagged and due notes; writes only each note's status box and its `status-checked` / `project-status` frontmatter, plus a report with `/b:enhance` and `/b:curate` candidates (never moves a note). Monthly is a good cadence.
- **EXPORT** (`/b:export`) — pack selected notes (list/tag/folder) into a portable `brain-pack-*.zip` bundle; default level verbatim and read-only, `--public` runs a redaction pipeline (default policy + `content/_privacy.md` overrides + the always-cut terms of the git-ignored `content/_privacy.local.md`, one verdict table, pattern- and term-sweep + audit nets, local redaction report).
- **IMPORT** (`/b:import`) — import a brain-pack bundle from another base: validate, triage collisions, adapt placement to this vault's taxonomy, stamp provenance, update indexes, write a report; at most 2 prompts per run.
- **UPGRADE** (`/b:upgrade`) — pull a newer template release into this base: dry run with the changelog, one review table, apply, one commit; adopts a base without `.kb-template.json` first. Never touches notes in `content/`.

An agent without slash commands, such as Codex, treats `/b:<name>` as the `brain-<name>` skill: `/b:ingest` is `brain-ingest`.

## Safety Rules

- Never modify `.obsidian/` or `.claude/` internals unless the task is about them.
- Never delete user-authored content without confirmation. Retirement is reversible: `/b:curate` moves notes to `_graveyard/`, never `git rm`.
- Always preserve existing frontmatter when editing.
- Always add `agent-created: true` to new notes.
- Always update indexes after every write.
- Always work on the `{{MAIN_BRANCH}}` branch.
