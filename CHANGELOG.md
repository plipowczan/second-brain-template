# Changelog

All notable changes to the **Knowledge Base Template** are documented here, for people
who have cloned the template and want to pull improvements into their own base.

The format follows [Keep a Changelog](https://keepachangelog.com/). Dates are ISO (UTC).

## [Unreleased]

### Fixed
- **YouTube ingest works on Windows with Smart App Control.** `brain-ingest`'s
  `yt_fetch.py` always ran the `yt-dlp` command and gave up when it was not on PATH. On
  Windows with Smart App Control in enforce mode, the unsigned `yt-dlp.exe` that pip
  installs is blocked (`WinError 4551: An Application Control policy has blocked this
  file`), so every `/b:ingest` of a YouTube URL failed. The signed `python.exe` is
  allowed, so `python -m yt_dlp` still runs. The script now picks the command itself, in
  this order: `$YT_DLP_CMD` if you set it (used as given, for example
  `"C:\Program Files\yt-dlp\yt-dlp.exe"`; double-quote paths with spaces); a `yt-dlp` on
  PATH that actually starts (`yt-dlp --version` succeeds); `python -m yt_dlp` with the
  interpreter the script runs under, when the module is installed. Metadata, captions
  and the Whisper audio download all use that command. When none is found, the script
  exits 3 with `yt-dlp not found` and the install hint (`pip install yt-dlp`, or set
  `YT_DLP_CMD`), and `/b:ingest` stops with that hint; it no longer pre-checks `yt-dlp`
  with `which`. A
  working `yt-dlp` on PATH is still preferred, so nothing changes where ingest already
  worked. The `/b:onboard` prerequisite check also accepts `python -m yt_dlp`, and the
  README and the test notes no longer say yt-dlp has to be on PATH.

  Existing bases: pick it up with `/b:upgrade`, which updates the `brain-ingest` skill
  (`SKILL.md`, `scripts/yt_fetch.py` and its tests). Nothing else is needed, unless you
  relied on a standalone `yt-dlp` executable that is no longer there: then run
  `pip install yt-dlp` with the Python you run the skills with.

## [0.2.0] - 2026-10-13

### Added
- **`/b:upgrade` pulls new template releases into your base.** Until now every update
  meant reading this file and re-copying files by hand. The new `brain-upgrade` skill
  downloads a release from GitHub (or takes a release `.zip` or a local clone, so it
  also works offline and without git), shows a **dry run** (the entries of this file
  since your version, **BREAKING** first, and a plan per file), and changes nothing until
  you approve the plan in one table. Template files you never touched are updated;
  files you edited are kept, and you are asked only when the template changed the same
  file (keep, overwrite, or merge together with the agent). Files the template removed
  are proposed for deletion, checked only when you never edited them. `CLAUDE.md`,
  `AGENTS.md` and `content/WRITING_STYLE.md` are re-rendered from the new templates only
  when you ask and only while you have not edited them by hand. Your notes in `content/`
  and your `README.md` are never written. With git the update is one commit
  (`chore(template): upgrade to …`) holding exactly what the update wrote: if one of
  those files changes before the commit (a sync client, an editor), it stops without
  staging anything and names the file. Without git every replaced file is copied to
  `.kb-upgrade-backup/` first. Before the update tool from a downloaded release (or a
  folder or zip you point to) runs at all, `/b:upgrade` shows you its repository,
  version, tag, commit and where it came from, and asks for your yes; a release from a
  different repository than your base follows is called out, and the tool refuses it
  without your explicit consent. A download is judged by the repository it was fetched
  from, not by what the archive says about itself; a folder, a zip or a local clone you
  point to cannot prove where it comes from, so you confirm it explicitly too. Releases are not signed: the tool comes from the same
  repository as the skills and hooks it installs. Applying is all or nothing: if a write fails halfway (a
  file locked by OneDrive or an antivirus, a full disk), every file is put back as it was
  and the run says so; the same happens when a planned file changes, or a link appears,
  while the update runs. A file that something else (a sync client, an editor) changed
  after the update wrote it is left as it is and named, so you can check it against git
  or the backup. Whatever a downloaded manifest, a history index or your stamp
  claims, it writes nothing outside your base, nothing under `content/` (except
  `content/WRITING_STYLE.md` when you ask for its re-render) and never your `README.md`,
  and it refuses paths that Windows or macOS would treat as one file. It never writes
  through a symbolic link or a junction: when a template file, or a folder above it, is
  one, the dry run stops and names it. Uncommitted edits to `.kb-template.json` or
  `.kb-onboard.json` stop apply just like edits to any planned file. The base records
  its template version and what the template shipped in a new stamp, `.kb-template.json`.
  The scripts (`.claude/skills/brain-upgrade/scripts/`) need only the Python standard
  library.

  Existing bases: your base has neither `/b:upgrade` nor a stamp yet, so the first
  update runs the engine of the `0.2.0` release (or newer) and starts with an adoption
  (next entry). Download the release `.zip` (or use a clone of the template), unpack it
  outside your base, and ask your agent to follow its
  `.claude/skills/brain-upgrade/SKILL.md`, or run it yourself from your base:
  `python <release>/.claude/skills/brain-upgrade/scripts/upgrade.py plan --instance . --adopt --source <release.zip>`.
  Review and apply the adoption and commit it; then run the same `plan` without
  `--adopt` for the upgrade, its own commit. From then on, `/b:upgrade` is enough.
- **Adoption (`/b:upgrade --adopt`) brings bases without a stamp under updates,** of any
  generation, including those older than `0.1.0` that still have the pre-rename skill
  folders. Each release ships an index of every hash the template's files have had
  (`.claude/skills/brain-upgrade/known-hashes.json`), so adoption recognises unmodified
  template files from your generation and finds the nearest release. It moves those
  files forward to that release only (never back), adds the files the release has and
  your base lacks (you can deselect them), and writes the stamp, in its own commit. Your
  edits stay as they are and remain visible as edits at the next upgrade. The upgrade to
  the newest version follows as a second commit, so a large first update comes in two
  reviewable, separately revertible parts.
- **`.kb-manifest.json` holds the template version and sorts every file into a class.**
  The version (`0.1.0` until the next release) now lives only there, and `package.json`
  no longer has a `version` field. The four classes say what an update may touch:
  **owned** files (`.claude/`, hooks, workflows, config, `CHANGELOG.md`, `LICENSE`, …)
  are kept current; **seeded** files (`content/` and `README.md`) are yours once copied
  and are never written; **rendered** files (`CLAUDE.md`, `AGENTS.md`,
  `content/WRITING_STYLE.md`) come from the `*.template.md` files; **author** files
  (`openspec/`, `dev/`, `CONTRIBUTING.md`, `CLAUDE.local.md`) are for developing the
  template and never reach a base. This is the groundwork for `/b:upgrade`.

  Existing bases: nothing to do by hand; your first `/b:upgrade --adopt` brings the file in.
- **Tests run on every push to `main` and on every pull request into it.** The new
  `.github/workflows/tests.yml` runs on Linux and Windows. It runs `python
  tests/run_tests.py`, then the new `python tests/run_skill_tests.py`, which runs every
  skill's own unit tests (`.claude/skills/*/scripts/test_*.py`; `run_tests.py` runs only
  the curate and brain-upgrade suites). Last, it makes real commits to check that `.githooks/pre-commit` lets
  a commit through on the template's own tree, blocks a note without frontmatter, and
  blocks when the lint script is missing. A test that needs a tool the runner doesn't have
  is skipped and listed with its reason in the job summary, never counted as passed. Today
  that is the two `yt-dlp` integration tests in `brain-ingest`, which need the `yt-dlp`
  binary and access to YouTube. A skill suite that finds no tests fails.

  Existing bases: optional. Pull `.github/workflows/tests.yml` and
  `tests/run_skill_tests.py` to run the same checks on your base's pushes; it runs only if
  your default branch is `main`. The clean-tree hook check is skipped there, because its
  result depends on your own notes. `python tests/run_skill_tests.py` also works locally.
- **The template is now developed directly in this repository, and the rules for doing
  that live in `CONTRIBUTING.md`.** Until now this repository was a mirror: the template
  was built inside the maintainer's own base and copied here in `sync from brain@…`
  commits. From now on every change lands here first, comes with an entry in this file,
  and passes `python tests/run_tests.py` before it is committed. `CONTRIBUTING.md` also
  says which files are templates (`*.template.md`, rendered only by `/b:onboard` in your
  base) and which are starter `content/`. Claude Code loads these rules through a
  git-ignored `CLAUDE.local.md` that imports `CONTRIBUTING.md`, so they never become part
  of your base's own instructions. `.gitignore` gained a `CLAUDE.local.md` line for that.

  Existing bases: nothing to do. `CONTRIBUTING.md` is for people who develop the template;
  if your clone has it, you can delete it. The new `.gitignore` line is optional and only
  keeps a personal `CLAUDE.local.md` out of your commits.

### Fixed
- **`.claude/agents/AGENTS.md` no longer sends you to `kb-template/`.** Its rules said to
  mirror every agent change into `kb-template/.claude/agents/` and log it in
  `kb-template/CHANGELOG.md`, a folder that exists only in the maintainer's own base and
  is frozen there. The file also pointed to a note from that base
  (`AI/TOOLS/Deep-Research-skills`) and named the research skills without their `brain-`
  prefix. It now says that agents come from the template, like the skills: in the
  template repository a change to an agent gets an entry in this file, and in a base
  agents arrive with template updates.

  Existing bases: re-pull `.claude/agents/AGENTS.md`. It is documentation; the agents
  themselves are unchanged.
- **The optional `.githooks/pre-commit` lints commits again, and says so when it can't.**
  It still called `.claude/skills/lint/scripts/lint_scan.py`, the path from before the
  skills were renamed to `brain-*`, and let the commit through whenever that call failed
  (`|| exit 0`). Since the rename it passed every commit without checking anything. It
  was also not marked executable, so on Linux and macOS git skipped it with only a hint.
  The hook now calls `.claude/skills/brain-lint/scripts/lint_scan.py`, lists the notes it
  blocks on, and also blocks, with a message, when it cannot run the lint at all: no
  Python 3 on `PATH`, the script missing, a crash, or output that is not a lint report.
  `git commit --no-verify` skips it once. As before, it checks the whole `content/`
  folder, not only the staged files.

  Existing bases: only if you enabled the hook (`git config core.hooksPath .githooks`).
  Re-pull `.githooks/pre-commit` together with the `brain-lint` fix below: without it the
  hook blocks every commit on `content/_privacy.md`. On Linux or macOS, if your copy is
  not executable, run `chmod +x .githooks/pre-commit`.
- **`brain-lint` no longer reports underscore-prefixed files like `content/_privacy.md`.**
  `lint_scan.py` listed `_privacy.md` under `missing_frontmatter`, and `lint_links.py`
  listed it as an orphan, although the file is configuration, not a note. Both scripts now
  skip any `_*.md` file under `content/`, the rule `build_indexes.py` already applies (see
  the `brain-reindex` entry below). On the template's own content `/b:lint` now reports no
  issues.

  Existing bases: re-pull `.claude/skills/brain-lint/scripts/lint_scan.py` and
  `lint_links.py`. A file of yours whose name starts with `_` is no longer linted, which
  matches how `/b:reindex` already treats it; rename it if it is meant to be a note.
- **The `kb-maintain` workflow runs again.** `.github/workflows/kb-maintain.yml` still
  called `.claude/skills/reindex/…` and `.claude/skills/lint/…` after those skills were
  renamed to `brain-reindex` and `brain-lint`, so every scheduled run failed at the
  rebuild step ("can't open file") and nothing was reindexed. In this repository that was
  every Monday from 2026-07-20 on. The workflow now calls
  `brain-reindex/scripts/build_indexes.py` and `brain-lint/scripts/lint_scan.py`. Its
  comments and pull-request text, and the SessionStart hook's "no vault map yet" message,
  now name the current commands (`/b:reindex`, `/b:lint`, `/b:onboard`).

  Existing bases: re-pull `.github/workflows/kb-maintain.yml`, and
  `.claude/hooks/load_vault_map.py` for the message. The optional `.githooks/pre-commit`
  had the same stale path; it has its own entry above.
- **`brain-ingest` no longer forces every vault to English.** The "Language enforcement"
  paragraph in Phase 2 declared "the canonical vault language is **English**" and told the
  agent to translate Polish (or any other) sources on ingest — a value leaked from the
  template author's own base. Every vault onboarded from this template sets
  `{{PRIMARY_LANGUAGE}}` in `content/WRITING_STYLE.md`, so a Polish-language base would get
  its own notes silently translated into English against its stated style. The skill now
  reads the primary language from `content/WRITING_STYLE.md` instead of assuming one, and
  translates *into* that language. Its cluster-detection step no longer hardcodes
  "English/Polish stop-words" either.

  The rule now also names **both** writing-style filenames — `content/WRITING_STYLE.md`
  (what `/b:onboard` generates) and `content/WRITING_STYLE_ANALYSIS.md` (what vaults
  predating that template carry). The first pass replaced a hardcoded *language* with a
  hardcoded *filename*, which would have sent the agent to a file that does not exist in
  an older base. Naming both also keeps this skill byte-identical between `.claude/skills/`
  and `kb-template/.claude/skills/`, so `scripts/check-kb-template-drift.sh` stays quiet —
  the scripts already excluded both filenames (`build_indexes.py` `EXCLUDE_FILES`), so this
  just brings the skill in line with the rest of the codebase.

  Known remaining hardcode: `brain-research-deep` still instructs research agents that
  "all field values must be in English". That one is arguably intentional (machine-readable
  JSON), but it flows into `/b:research-report`, so a non-English vault gets an
  English report.
- **`brain-reindex` no longer indexes underscore-prefixed files like `content/_privacy.md`.**
  `_privacy.md` documents that it is "underscore-prefixed, so it is excluded from the site
  build, the indexes, and can never be packed into a bundle itself" — but `build_indexes.py`
  only skipped underscore-prefixed *directories* (`_raw/`, `_indexes/`, `_outputs/`,
  `_graveyard/`) plus three files listed by name. A loose `_*.md` was indexed, so every
  vault built from this template carried a phantom `| (root) | 1 | untyped(1) |` row in
  `vault-map.md` and a matching catalog entry for a config file. The rule now matches the
  documented convention: underscore prefix means infrastructure, not a note. The template's
  own checked-in indexes are regenerated accordingly (3 → 2 notes, which is the real count).

  Existing bases: re-pull `.claude/skills/brain-reindex/scripts/build_indexes.py` and run
  `/b:reindex`. Harmless if your vault has no loose `_*.md` under `content/`.
- **`brain-reindex` no longer destroys the `## Recent Changes` section.**
  `scripts/build_indexes.py` regenerated that section from "the 15 newest notes by
  `date:`" with a 75-character `summary:` snippet. But Recent Changes is a hand-maintained
  *change log* — "what changed and why" — which no frontmatter field records, so every
  rebuild silently replaced curated narrative with a derived listing. The script now
  preserves an existing `## Recent Changes` section verbatim and only falls back to the
  derived listing when the section is absent (fresh vault); the fallback also now emits 10
  entries, matching the "last 10 changes" contract in `AGENTS.md` instead of 15.

  If you run the scheduled `kb-maintain` workflow, this was also making **every** run
  report a substantive index diff and open a no-op PR whose only effect was clobbering
  that section. After this fix a clean vault reproduces all three indexes exactly
  (0 substantive diff), so the workflow opens a PR only on genuine drift.
- **`/research-deep` JSON validator was a silent no-op** —
  `.claude/skills/research/validate_json.py` only read the `field_categories:` /
  `category:` schema, but `/research` Step 4 emits `fields.yaml` with `categories:` /
  `name:`. On that schema the loader parsed **0 fields** and every file "passed"
  trivially (100% of nothing). The loader now accepts **both** schema styles
  (`field_categories`|`categories`, category label `category`|`name`). Second fix:
  `valid` gated only on `required` fields, and nothing was ever marked `required`, so
  even a correctly-parsed schema passed with fields missing — when a schema marks
  nothing required the validator now **treats all defined fields as required and
  enforces full coverage** (a file missing any field FAILs with exit 1). Backward
  compatible: schemas that set explicit `required:` flags keep the original gating.
  Existing bases: re-pull `.claude/skills/research/validate_json.py`.

### Changed
- **`/b:onboard` writes the template stamp and removes template-development files.**
  After rendering your instruction files it records `.kb-template.json` (the template
  version and what the template shipped), so `/b:upgrade` can later tell template files
  from your edits. It also deletes `openspec/`, `dev/` and `CONTRIBUTING.md`, which are
  only for developing the template, and it refuses to run in a checkout that has
  `CLAUDE.local.md` (the template's own source). Commit `.kb-template.json` and
  `.kb-onboard.json` with the rest of your base.

  Existing bases: nothing to do; the adoption above writes your stamp.
- **`README.md` belongs to your base.** Like the starter `content/`, it is copied once
  and then it is yours: upgrades never write it and never ask about it, and they list a
  changed template README as information only. The template's README describes the
  template; yours can describe your knowledge.

  Existing bases: nothing to do.
- **`.kb-onboard.json` is no longer git-ignored.** It holds your onboarding answers, which
  are the input for re-rendering `CLAUDE.md`, `AGENTS.md` and `content/WRITING_STYLE.md`.
  Every base checked kept it only on disk, so any other clone of the base lost it. Its
  contents (name, owner, topics, voice) already appear in your committed `AGENTS.md`.

  Existing bases: delete the `.kb-onboard.json` line from `.gitignore` and commit the
  file. An upgrade does both for you.
- **Template-development files are left out of archives.** `.gitattributes` marks
  `openspec/`, `dev/`, `CONTRIBUTING.md` and `CLAUDE.local.md` `export-ignore`, so
  "Download ZIP" and release archives no longer contain them. The lines reach your base
  with `.gitattributes`: if you ever publish your base with `git archive`, a root
  `openspec/`, `dev/` or `CONTRIBUTING.md` of your own would be left out of it.

  Existing bases: nothing to do.
- **`kb-maintain` uses current versions of its GitHub actions.**
  `.github/workflows/kb-maintain.yml` moves from `actions/checkout@v4`,
  `actions/setup-python@v5` and `actions/upload-artifact@v4`, which run on the Node 20
  runtime GitHub is retiring, to `@v7` of all three, which run on Node 24. The new
  `tests.yml` uses the same versions. What the workflow does is unchanged.

  Existing bases: re-pull `.github/workflows/kb-maintain.yml`. A self-hosted runner needs
  Actions Runner 2.327.1 or newer.
- **BREAKING: all workflow commands and skills are namespaced** — command wrappers moved
  from `.claude/commands/*.md` to `.claude/commands/b/*.md` (subdirectory = native `:`
  namespace, so `/ingest` is now `/b:ingest`), and every vault skill directory gained a
  `brain-` prefix with its frontmatter `name:` updated to match (`ingest` → `brain-ingest`).
  This stops collisions with same-named skills from installed plugins and groups the
  vault's commands in the slash menu. Skill **descriptions are unchanged**, so
  natural-language triggering ("process inbox", "health check") works exactly as before.
  The research suite also gained command wrappers (`/b:research`, `/b:research-deep`,
  `/b:research-report`, `/b:research-add-items`, `/b:research-add-fields`) — previously
  it was invocable only by bare skill name. `excalidraw-diagram` (generic utility) keeps
  its name. All cross-references in skills, scripts, docs, and the test suite's
  path constants (`tests/run_tests.py`) updated.

  | Old command | New command | Old skill | New skill |
  |---|---|---|---|
  | `/onboard` | `/b:onboard` | `onboard` | `brain-onboard` |
  | `/ingest` | `/b:ingest` | `ingest` | `brain-ingest` |
  | `/compile` | `/b:compile` | `compile` | `brain-compile` |
  | `/enhance` | `/b:enhance` | `enhance` | `brain-enhance` |
  | `/reindex` | `/b:reindex` | `reindex` | `brain-reindex` |
  | `/qa` | `/b:qa` | `qa` | `brain-qa` |
  | `/lint` | `/b:lint` | `lint` | `brain-lint` |
  | `/output` | `/b:output` | `output` | `brain-output` |
  | `/refactor` | `/b:refactor` | `refactor` | `brain-refactor` |
  | `/gaps` | `/b:gaps` | `gaps` | `brain-gaps` |
  | `/curate` | `/b:curate` | `curate` | `brain-curate` |
  | `/export` | `/b:export` | `export` | `brain-export` |
  | `/import` | `/b:import` | `import` | `brain-import` |
  | — | `/b:research` | `research` | `brain-research` |
  | — | `/b:research-deep` | `research-deep` | `brain-research-deep` |
  | — | `/b:research-report` | `research-report` | `brain-research-report` |
  | — | `/b:research-add-items` | `research-add-items` | `brain-research-add-items` |
  | — | `/b:research-add-fields` | `research-add-fields` | `brain-research-add-fields` |

  Existing bases: `git mv` your `.claude/commands/*.md` into `.claude/commands/b/`,
  `git mv` each skill dir to its `brain-*` name, update each `SKILL.md` `name:` field
  to match the new directory name, then re-pull the updated docs (README, AGENTS
  template, REFERENCE notes). Muscle-memory note: type `/b:` and tab-complete.
- **`web-search-agent` no longer hard-depends on a Unix `date` call** — step 0 ("Get
  Current Date") ran `date +%Y-%m-%d`, which errors in a PowerShell-only environment
  (`date` is a `Get-Date` alias that rejects `+%Y-%m-%d`). It now takes today's date from
  the harness-injected context (no shell call), and only falls back to a tool call —
  Bash `date +%Y-%m-%d` or PowerShell `Get-Date -Format yyyy-MM-dd` — if the date is
  genuinely unavailable. Shell-agnostic; the failure was cosmetic (date is only used to
  filter "recent" results) but this removes it. Existing bases: re-pull
  `.claude/agents/web-search-agent.md`.

## [0.1.0] - 2026-07-13

First tagged release of the second-brain template.

### Fixed
- **`/lint` link scanner no longer false-flags escaped-pipe aliases** —
  `.claude/skills/lint/scripts/lint_links.py` split link targets on `|` but not on the
  table-escaped `\|`, so `[[Note\|alias]]` resolved to `Note\` and was reported broken.
  Now normalizes `\|`→`|` before splitting. Also treats `.webp` as an asset embed (was
  flagged broken). Cut ~7 false positives on a ~360-note vault. The lint `SKILL.md` now
  points at the two canonical scanners (`lint_scan.py`, `lint_links.py`) so runs use them
  instead of ad-hoc greps, and reminds the operator to triage raw broken-link counts.
  Existing bases: re-pull `.claude/skills/lint/`.
- **Non-Latin vaults** — forced UTF-8 stdout so `/lint`, `/gaps`, and `/refactor` no longer
  crash on non-ASCII content (e.g. Polish); `build_indexes.py` writes UTF-8 too.
- **`/lint` false positives** — `lint_scan` now parses block-style YAML tag lists, so notes
  using multi-line `tags:` no longer report a spurious `missing_tags`.

### Changed
- **`/qa` cites chat answers as percent-encoded markdown links** — instead of
  `[[wikilinks]]`, the Q&A skill now emits `[Title](content/…%20path.md)` links that are
  clickable in Claude Desktop and VS Code markdown preview (saved answer-notes still use
  `[[wikilinks]]` for Obsidian/graph). Existing bases: re-pull `.claude/skills/qa/`.
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

### Added
- **YT ingest supports an alternate yt-dlp `player_client`** — `ingest/scripts/yt_fetch.py`
  now threads an optional `player_client` through metadata + caption fetching
  (`--extractor-args youtube:player_client=…`), a workaround for when the default client is
  throttled or blocked. Existing bases: re-pull `.claude/skills/ingest/scripts/`.
- **Research skill suite now ships its `web-search-agent` dependency** — the `/research`
  → `/research-deep` → `/research-report` pipeline dispatches a `web-search-agent`
  sub-agent that was never bundled, so the deep phase silently fell back to generic web
  search. Added `.claude/agents/web-search-agent.md` + `.claude/agents/web-search-modules/`
  (5 routing modules: general-web, github-debug, stackoverflow, academic-papers,
  chinese-tech), vendored from the upstream **Weizhena/Deep-Research-skills** (MIT) this
  suite was adapted from. Also fixed two hardcoded home-dir paths that assumed a global
  `~/.claude` install: `research-deep` now runs
  `python .claude/skills/research/validate_json.py` (was `~/.claude/skills/…`) and the
  agent loads modules from `.claude/agents/web-search-modules/` (was `~/.claude/agents/…`)
  — both project-relative so a cloned template works without a global install. Removed a
  machine-specific project-root path from `research/SKILL.md` (now "the vault/project
  root"). Existing bases: pull `.claude/agents/` and re-pull `.claude/skills/research-deep/`
  + `.claude/skills/research/`.
- **Export privacy levels: `/export --public` redaction pipeline** — bundles that leave
  your trust boundary (shared with strangers, published openly) can now be scrubbed of
  private data. Default level stays exactly as before (verbatim, 2 prompts, read-only).
  `--public` adds: a category redaction policy (always cut secrets, third-party PII,
  health, finance, rates; genericize personal/commercial context; keep tools/howtos/
  technical opinions) tunable per vault via a new optional `content/_privacy.md`
  (commented example ships with the template); one approvable verdict table
  (include/redact/exclude per note, full diff on demand — 3rd and normally last prompt);
  two post-redaction safety nets (`privacy_sweep.py` deterministic pattern scan for
  emails/phones/IBAN/cards/API-keys/JWT/wallets + a fresh-context adversarial LLM audit);
  wikilink de-personalization (`[[My Crypto Strategy]]` → `[[Crypto Strategy]]`, person-name
  titles genericized) — and writes a local redaction report to `_outputs/reports/`.
  The shipped bundle deliberately carries **no redaction trace** (manifest unchanged,
  format still 1) — the local report is the only record. Also fixes `bundle.py` exclusion:
  underscore-prefixed **files** (e.g. `_privacy.md`) can no longer be packed at any level.
  Existing bases: pull `.claude/skills/export/` (SKILL.md + `bundle.py` +
  `privacy_sweep.py` + tests) and optionally `content/_privacy.md`.
- **Note-bundle transfer: `/export` + `/import` skills** — move sets of notes between
  any two template-based knowledge bases. `/export` (new skill + command) resolves a
  selection (wikilink list, `#tag`, or folder), confirms it, offers depth-1 linked
  neighbors, and packs verbatim note copies into a `brain-pack-*.zip` with a
  `manifest.json` (format `1`, source base name, export date, per-note sha256) — fully
  read-only for the vault. `/import` (new skill + command) validates the bundle before
  any write (format/hash checks), auto-skips byte-identical notes (idempotent re-import),
  triages collisions in a single approve-or-edit table (skip/merge/keep-target/rename),
  maps notes from missing source folders onto the target vault's own taxonomy in a second
  single table (never seeds foreign folder structures unasked), stamps
  `imported-from`/`imported` provenance frontmatter, leaves broken wikilinks intact for
  later re-stitching, batch-updates all 3 indexes, and writes a report to
  `_outputs/reports/` — hard budget of at most 2 user prompts per run, regardless of
  bundle size. Deterministic mechanics live in `export/scripts/bundle.py`
  (`pack`/`unpack`/`same`, stdlib-only Python, tests included). Existing bases: pull
  `.claude/skills/export/`, `.claude/skills/import/`, `.claude/commands/export.md`,
  `.claude/commands/import.md`, and add the two Workflows rows to your `AGENTS.md`.
- **"Works beyond Claude Code" docs** — the template now documents that it runs *outside*
  Claude Code, with **no terminal and no git commands**. Three doc-only additions: a new
  README section listing the supported tools (Claude Desktop Code tab, GitHub Copilot,
  Codex, Cursor, Antigravity) and how to run commands / save changes in each; a note in
  `AGENTS.template.md` explaining which tool reads `AGENTS.md` vs `CLAUDE.md` and why the
  `@AGENTS.md` import keeps one source of truth; and a new **`ENVIRONMENTS.md`** carrying
  the full verified tool-by-tool matrix (file access, native vs conversational commands,
  git-without-commands, which instruction file each tool reads). No skill or
  generation-logic changes. Existing bases: pull `ENVIRONMENTS.md` and add the
  README / `AGENTS.md` paragraphs if you want the same guidance (your rendered `AGENTS.md`
  predates the note — paste it in by hand).
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

---

_Older history predates this changelog. From here on, every change to the template is
recorded above._
