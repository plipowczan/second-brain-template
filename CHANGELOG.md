# Changelog

All notable changes to the **Knowledge Base Template** are documented here, for people
who have cloned the template and want to pull improvements into their own base.

The format follows [Keep a Changelog](https://keepachangelog.com/). Dates are ISO (UTC).

## [Unreleased]

### Added
- **`LICENSE` (MIT)** — the template now ships an explicit MIT license, so forks have
  real permission to use, modify, and redistribute it. Without a license file a public
  repo defaults to "all rights reserved," which silently contradicted the "git clone and
  it's yours" invitation. Also adds a **License** section to the README. Existing bases:
  pull `LICENSE` if you intend to republish or share your clone.
- **Scheduled maintenance workflow** (`.github/workflows/kb-maintain.yml`) — an optional
  GitHub Action that keeps navigation fresh without anyone remembering to run `/reindex`.
  Weekly (and on-demand via the Actions tab) it rebuilds `content/_indexes/` and runs the
  lint scanner, then opens **one** pull request only if the rebuild changed the indexes in
  substance — a restamped `updated:` timestamp alone never triggers a PR. It never edits
  your notes; the only writes are to `_indexes/`, via a PR you review. Encodes OpenWiki's
  "doc drift is a CI problem, not a discipline problem" idea. Delete the file to opt out.
  - **Enable it:** it runs automatically once the file is on your default branch. Under
    **Settings → Actions → General**, allow workflows to *"Read and write"* and to
    *"create and approve pull requests"* so the bot can open the maintenance PR.
- **`/curate` skill** — vault hygiene: scores notes for staleness, isolation, dead links,
  and duplication; proposes archive/merge/refresh; retires confirmed notes to
  `content/_graveyard/` (reversible — never `git rm`, gated on your confirmation).
- **`content/_graveyard/`** — holding folder for retired notes, excluded from the indexes.
- **This `CHANGELOG.md`** — from now on every template change is recorded here.

### Changed
- **Single source of truth for agent instructions.** `AGENTS.md` is now the canonical
  file that holds all project instructions (role, navigation protocol, writing style,
  frontmatter, workflows, safety). `CLAUDE.md` is reduced to a thin pointer that imports
  `AGENTS.md` via the `@AGENTS.md` line, so Claude Code and any `AGENTS.md`-reading agent
  (Codex, Gemini CLI, OpenCode) all follow **one** file. Previously the content lived in
  `CLAUDE.md` and `AGENTS.md` was a short mirror — the two could drift.
  - **Migration (existing bases):** move your instruction body from `CLAUDE.md` into
    `AGENTS.md`, then replace `CLAUDE.md` with a pointer whose last line is `@AGENTS.md`.
    Fresh clones get this automatically from the updated templates via `/onboard`.
  - `onboard` still renders and personalizes both files; no action needed for new setups.
- **README** — clearer positioning: the base as an LLM Wiki (Karpathy) that is portable
  via the OKF standard, with the index-first "why it scales without embeddings" explainer.

### Fixed
- **Non-Latin vaults** — forced UTF-8 stdout so `/lint`, `/gaps`, and `/refactor` no longer
  crash on non-ASCII content (e.g. Polish); `build_indexes.py` writes UTF-8 too.
- **`/lint` false positives** — `lint_scan` now parses block-style YAML tag lists, so notes
  using multi-line `tags:` no longer report a spurious `missing_tags`.

---

_Older history predates this changelog. From here on, every change to the template is
recorded above._
