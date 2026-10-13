# Knowledge Base Template

> A second brain for agents *and* humans — built on Karpathy's **LLM Wiki**
> idea, portable via the **OKF** standard.

RAG searches raw documents on every query. An LLM Wiki flips it: a Claude
Code agent **incrementally builds and maintains** a living markdown vault —
cross-linked, indexed, synthesized. Knowledge **compounds** instead of piling
up. Because it's plain markdown with `type` frontmatter (the OKF minimum), the
base stays portable — `git clone` and it's yours — and readable by agent and
human alike.

The trick that makes it scale without embeddings or a vector DB: **index-first
reads**. The agent starts from a navigation map and opens only the relevant
notes, keeping context up to ~28× smaller per query — good for ~500 sources on
plain markdown alone.

Live instance: **[brain.lipowczan.pl](https://brain.lipowczan.pl)**.

This template is about *managing* knowledge, not publishing it — the Quartz /
GitHub Pages pipeline is intentionally **not** included (see
[Adding publishing later](#adding-publishing-later)). What you get is an
Obsidian-style vault plus the skills that ingest sources, compile articles,
answer questions, lint for quality, and keep navigation indexes current.

## What you get

- `content/` — your vault. Topic folders hold notes; `_raw/` is the ingest drop
  zone; `_indexes/` holds auto-maintained navigation files; `_outputs/` holds
  generated answers and reports; `templates/` holds note templates.
- `.claude/skills/` + `.claude/commands/` — the management skills below.

## Quickstart

1. Open this folder in Claude Code.
2. Install script prerequisites: `pip install -r requirements.txt`.
3. Run **`/b:onboard`** — it interviews you (KB name, owner, topics, language,
   voice) and then personalizes the brain (`CLAUDE.md`, `AGENTS.md`,
   `content/WRITING_STYLE.md`), creates your topic folders, and builds the
   navigation indexes.
4. Start using the vault:
   - Drop a file in `content/_raw/inbox/` and run `/b:ingest`.
   - Ask `/b:qa what does this vault say about …`.
   - Run `/b:lint` for a health check.

> Prefer to set things up by hand? You can skip `/b:onboard`, rename the
> `*.template.md` files yourself, and edit the `{{PLACEHOLDERS}}` directly.

## Works beyond Claude Code

The template is plain markdown files plus instructions for an agent. Drive it in
any tool where an AI assistant can reach your files: Claude Code, Claude Desktop
(the **Code** tab), GitHub Copilot (VS Code), Codex, Cursor, or Antigravity.

- **Commands go in the agent's chat.** In Claude Code / Claude Desktop (Code)
  they run directly as `/b:onboard`, `/b:ingest`. In other tools, ask in a sentence:
  *"follow the instructions in `.claude/commands/b/ingest.md`."*
- **No terminal needed.** Git without commands: tell the agent "save my changes,"
  use the panel buttons (VS Code–based tools), or use a cloud mode where the agent
  opens the pull request itself.
- **Don't want git at all?** Download a ZIP: the **Code** button → **Download
  ZIP** → unzip, and open the folder in your tool.

See [`ENVIRONMENTS.md`](ENVIRONMENTS.md) for the full tool-by-tool matrix.

## Updating your base

The template keeps improving: new skills, fixes, better hooks. Each release is listed in
[`CHANGELOG.md`](CHANGELOG.md), and **`/b:upgrade`** pulls it into your base:

1. It downloads the latest release from GitHub (or uses a release `.zip` or a local
   clone you point it to) and runs a **dry run**: the changelog entries since your
   version and a plan per file. Nothing changes yet.
2. You approve the plan in one table. Files you edited are kept; you are asked only
   when the template changed the same file. Your notes in `content/` and your
   `README.md` are never touched.
3. It applies the plan and records the new version in `.kb-template.json`.

- **With git**, the update is one commit (`chore(template): upgrade to …`); undo it
  with `git revert`.
- **Without git**, every file it replaces or deletes is copied to
  `.kb-upgrade-backup/` first.
- **Offline**, pass a release `.zip` you downloaded earlier, or a local clone of the
  template: `/b:upgrade` with the path. The download step prints where it saved the
  archive, so the same file works next time.

**What you trust.** Updates come from the template repository on GitHub over HTTPS (the
one recorded in your base's `.kb-template.json`). Before the update tool from a release
runs, `/b:upgrade` shows you its repository, version, tag, commit and where it was
downloaded from, and waits for your yes; a release from a different repository than your
base follows gets an explicit warning. Releases are not signed: the tool is code from the
same source as the skills and hooks it installs, which run in every session anyway.

**The first update of an older base** (created before `0.2.0`, so without
`.kb-template.json` and without `/b:upgrade`) starts with an **adoption**: it recognises
which files are unmodified template files from your generation, brings them to the
nearest release, and writes the stamp, in its own commit. The upgrade follows as a
second commit. Such a base has no `/b:upgrade` yet, so ask your agent to *"download the
latest release of the template and follow its
`.claude/skills/brain-upgrade/SKILL.md` to adopt this base"*.

## Skills

| Command | What it does |
|---------|--------------|
| `/b:onboard` | Interview + scaffold a fresh knowledge base from the template (personalizes the brain, creates topics, builds indexes). |
| `/b:ingest` | Turn raw sources (files in `_raw/inbox/`, or YouTube URLs) into wiki notes; updates indexes. |
| `/b:compile` | Synthesize a new article from existing notes on a topic. |
| `/b:enhance` | Improve a single note: fill gaps, add wikilinks, mark reviewed. |
| `/b:qa` | Answer a question from the vault, citing notes. |
| `/b:lint` | Audit vault health: frontmatter, broken links, orphans, stubs, stale notes. |
| `/b:output` | Generate a report/summary (reading list, topic map, timeline). |
| `/b:reindex` | Rebuild `vault-map.md`, `catalog.md`, `graph.md` from all notes. |
| `/b:refactor` | Rename/move/merge/split notes with automatic wikilink repair. |
| `/b:gaps` | Coverage analysis: weakly-connected notes, missing topics, thin areas. |
| `/b:curate` | Staleness hygiene: score notes (age, isolation, dead links, duplication), propose archive/merge/refresh, retire confirmed notes to `_graveyard/` (reversible). |
| `/b:upgrade` | Pull a newer template release into this base: dry run, one review table, one commit; adopts a base without a `.kb-template.json` stamp first. Never touches your notes. |
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

## License

[MIT](LICENSE) — use it, fork it, make it yours. The example notes under
`content/` are scaffolding meant to be replaced; they carry the same license.
