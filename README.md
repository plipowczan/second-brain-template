# Knowledge Base Template

A Claude Code–driven knowledge base: an Obsidian-style markdown vault plus a set
of skills that ingest sources, compile articles, answer questions, lint for
quality, and keep navigation indexes up to date. Publishing (Quartz/GitHub
Pages) is intentionally **not** included — this template is about *managing*
knowledge, not publishing it.

## What you get

- `content/` — your vault. Topic folders hold notes; `_raw/` is the ingest drop
  zone; `_indexes/` holds auto-maintained navigation files; `_outputs/` holds
  generated answers and reports; `templates/` holds note templates.
- `.claude/skills/` + `.claude/commands/` — the management skills below.

## Quickstart

1. Open this folder in Claude Code.
2. Install script prerequisites: `pip install -r requirements.txt`.
3. Run **`/onboard`** — it interviews you (KB name, owner, topics, language,
   voice) and then personalizes the brain (`CLAUDE.md`, `AGENTS.md`,
   `content/WRITING_STYLE.md`), creates your topic folders, and builds the
   navigation indexes.
4. Start using the vault:
   - Drop a file in `content/_raw/inbox/` and run `/ingest`.
   - Ask `/qa what does this vault say about …`.
   - Run `/lint` for a health check.

> Prefer to set things up by hand? You can skip `/onboard`, rename the
> `*.template.md` files yourself, and edit the `{{PLACEHOLDERS}}` directly.

## Skills

| Command | What it does |
|---------|--------------|
| `/onboard` | Interview + scaffold a fresh knowledge base from the template (personalizes the brain, creates topics, builds indexes). |
| `/ingest` | Turn raw sources (files in `_raw/inbox/`, or YouTube URLs) into wiki notes; updates indexes. |
| `/compile` | Synthesize a new article from existing notes on a topic. |
| `/enhance` | Improve a single note: fill gaps, add wikilinks, mark reviewed. |
| `/qa` | Answer a question from the vault, citing notes. |
| `/lint` | Audit vault health: frontmatter, broken links, orphans, stubs, stale notes. |
| `/output` | Generate a report/summary (reading list, topic map, timeline). |
| `/reindex` | Rebuild `vault-map.md`, `catalog.md`, `graph.md` from all notes. |
| `/refactor` | Rename/move/merge/split notes with automatic wikilink repair. |
| `/gaps` | Coverage analysis: weakly-connected notes, missing topics, thin areas. |
| (skill) `excalidraw-diagram` | Generate Excalidraw diagram JSON to embed in notes. |
| (skill) `research`, `research-deep`, … | Structured multi-item web research into the vault (best-effort; depends on your Claude Code web tools). |

## Prerequisites

- **Python 3** with **PyYAML** — required for the reindex and lint scripts
  (`pip install -r requirements.txt`).
- **Node** — optional, only for `npm run format` (Prettier).
- **yt-dlp** (+ **ffmpeg**) on PATH — optional, only for ingesting YouTube URLs.

## Adding publishing later

This template omits the Quartz static-site pipeline and the optional `brain-mcp`
server on purpose. Either can be layered on top of `content/` later without
changing how the skills work.
