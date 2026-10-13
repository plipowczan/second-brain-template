# Contributing to the template

These rules are for people who develop **the template itself**. If you cloned it to start
your own knowledge base, you don't need this file: run `/b:onboard` (see the
[README](README.md)), which deletes it from your copy.

## This repository is the source

- Since 2026-10-13 this repository is the source of truth for the template. Make changes
  here, directly. Until then it was a mirror: the template was built inside the
  maintainer's own base and copied here in `sync from brain@…` commits. That sync is gone.
- Every knowledge base created from the template is an **instance**. Changes flow one way,
  template → instances. Don't build a change in an instance and copy it back here.
- Instances pick changes up through an **update**, not by copying files around by hand:
  `/b:upgrade` (the `brain-upgrade` skill, from `0.2.0`) installs a tagged release and
  shows the owner the `CHANGELOG.md` entries since their version. Each entry still says
  what an existing base has to do, because the owner reads it during the upgrade.
- **Never run `/b:onboard` in this repository.** It renders `CLAUDE.md`, `AGENTS.md` and
  `content/WRITING_STYLE.md`, then deletes the `*.template.md` files: it turns the source
  into an instance. To try onboarding, clone to a scratch directory and run it there:
  `git clone . ../kb-onboard-test`.

## Every change gets a CHANGELOG entry

- Every change gets an entry in [`CHANGELOG.md`](CHANGELOG.md) under `## [Unreleased]`, in
  the same commit as the change. No entry, no merge.
- The format is [Keep a Changelog](https://keepachangelog.com/): sections `Added`,
  `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`. Newest on top: a new entry goes
  first in its section, and releases are listed newest first.
- Write for the people who update their own bases from this file. Say what changed, why it
  matters to them, and what an existing base has to do (`Existing bases: re-pull …, then run
  /b:reindex`). Start a breaking change with **BREAKING** and give the migration steps.

## Before you commit

1. `pip install -r requirements.txt` (PyYAML) once per environment.
2. `python tests/run_tests.py` must end with `ALL PASS` (exit code 0). It builds a
   throwaway vault and exercises reindex, lint, gaps and refactor, adopts and upgrades a
   synthetic old base with `brain-upgrade`, and runs the curate and brain-upgrade unit
   suites. Here (where `dev/` exists) it also runs `dev/check_manifest.py` and the `dev/`
   tests. It takes a few minutes, mostly git in temporary repositories.
3. If you changed a skill's scripts, also run that skill's own unit tests: `python -m
   unittest` from `.claude/skills/<skill>/scripts/`. `tests/run_tests.py` runs only the
   curate and brain-upgrade suites. The two `yt-dlp` integration tests in `brain-ingest`
   need `yt-dlp` and a network connection.
4. If you changed `.github/workflows/kb-maintain.yml`, or a script it calls
   (`build_indexes.py`, `lint_scan.py`), run what the workflow runs, from the repo root:

   ```bash
   python .claude/skills/brain-reindex/scripts/build_indexes.py
   python .claude/skills/brain-lint/scripts/lint_scan.py
   ```

   Then `git diff content/_indexes` may show only `updated:` lines. Any other change means
   the workflow would open an index-refresh pull request.

No CI runs these checks on push or pull request yet, so they are yours to run. Node is
needed only for the optional `npm run format` (Prettier).

## What ships, and in what form

[`.kb-manifest.json`](.kb-manifest.json) is the source of truth for what reaches an
instance. It sorts every tracked file into one of four classes; the first class that
matches wins, in the order author → rendered → owned → seeded. `dev/check_manifest.py`
fails on any tracked file that has no class, so a new top-level file needs a pattern
there.

| Class | Paths | What they are | In an instance |
|-------|-------|---------------|----------------|
| author | `openspec/**`, `CONTRIBUTING.md`, `CLAUDE.local.md`, `dev/**` | Specs, these rules, release tools | Never: `export-ignore` keeps them out of archives, `/b:onboard` deletes them from a clone, `brain-upgrade` never copies them |
| rendered | `CLAUDE.md` ← `CLAUDE.template.md`, `AGENTS.md` ← `AGENTS.template.md`, `content/WRITING_STYLE.md` ← `content/WRITING_STYLE.template.md` | Instruction templates with `{{PLACEHOLDERS}}` | `/b:onboard` renders them and deletes the templates; `brain-upgrade` re-renders a file only on request and only while it is untouched |
| owned | `.claude/**`, `.githooks/**`, `.github/**`, `tests/**`, `.kb-manifest.json`, `.editorconfig`, `.gitattributes`, `.gitignore`, `.npmrc`, `.prettierrc`, `package.json`, `requirements.txt`, `schema.yml`, `ENVIRONMENTS.md`, `CHANGELOG.md`, `LICENSE` | Workflows and their scripts, automation, config, documentation | Kept current by `brain-upgrade`. A file the owner edited is kept, and they are asked only when the template changed it too |
| seeded | `content/**`, `README.md` | Starter content and the product page | Copied once with the clone; from then on it belongs to the owner, and upgrades never write it |

The manifest's `exclude` list names files that never ship, even when they sit in a
source directory: caches, `.claude/settings.local.json`, and an instance's own
`.kb-template.json` and `.kb-onboard.json`.

- **No rendered `CLAUDE.md` or `AGENTS.md` here.** They exist only in an instance.
  `/b:onboard` recognises a fresh clone by `CLAUDE.template.md`, and Claude Code reads an
  `AGENTS.md` on its own, so a rendered file here would either confuse onboarding or load
  instance instructions into your session.
- **Instructions for instances go in the `*.template.md` files.** A new placeholder also
  needs a question in the `/b:onboard` interview and a key in its `.kb-onboard.json`
  mapping: `render.py` fails on any `{{KEY}}` without a value.
- **`content/` is starter content, not anyone's notes.** Keep it small and generic. After
  you change a note there, rebuild the indexes with
  `python .claude/skills/brain-reindex/scripts/build_indexes.py`.
- **No values from your own base in skills or templates:** no fixed language, names,
  topics or file paths that only exist in one vault. Read them from the instance (for
  example the primary language from `content/WRITING_STYLE.md`) or add a placeholder.

## Author tools in `dev/`

`dev/` is author-class: it never reaches an instance.

- `dev/check_manifest.py` — the release check: every tracked file has a class, the
  manifest version equals the newest `## [X.Y.Z]` in `CHANGELOG.md`, `package.json` has
  no `version`, and no section heading repeats within one version. `tests/run_tests.py`
  runs it.
- `dev/build_known_hashes.py` — regenerates `.claude/skills/brain-upgrade/known-hashes.json`,
  the history index adoption uses: every hash each owned- and author-class file has had
  in every commit reachable from HEAD, with the releases each state belongs to.
  `--release` also indexes the staged tree as the release being made; `--check` only
  reports whether the file is current.
- `dev/release_notes.py X.Y.Z` — prints that version's `CHANGELOG.md` section for the
  GitHub Release notes.

## Releasing

A release is one commit on `main` tagged `vX.Y.Z`, published as a GitHub Release whose
notes are its `CHANGELOG.md` section. The version lives only in `.kb-manifest.json`.
Instances install tags, so a tag is never moved: a defect gets a new patch release.

Start on an up-to-date `main` with every change for the release merged, then (with the
version in place of `X.Y.Z` and the UTC date in place of `YYYY-MM-DD`):

1. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`.
2. Set `"version": "X.Y.Z"` in `.kb-manifest.json`.
3. Stage both, then rebuild the history index with the staged tree as the release:

   ```bash
   git add CHANGELOG.md .kb-manifest.json
   python dev/build_known_hashes.py --release
   git add .claude/skills/brain-upgrade/known-hashes.json
   ```

4. Check, then commit:

   ```bash
   python dev/check_manifest.py
   python tests/run_tests.py
   git commit -m "chore(release): X.Y.Z"
   ```

5. Tag and publish:

   ```bash
   git tag -a vX.Y.Z -m "second-brain-template vX.Y.Z"
   git push origin main vX.Y.Z
   python dev/release_notes.py X.Y.Z > release-notes.md
   gh release create vX.Y.Z --title "vX.Y.Z" --notes-file release-notes.md
   ```

6. Verify that the published archive is what instances will get: in a scratch folder,
   `python .claude/skills/brain-upgrade/scripts/upgrade.py fetch --to X.Y.Z` downloads
   `archive/refs/tags/vX.Y.Z.zip`, and the `commit` it prints equals
   `git rev-parse vX.Y.Z^{commit}`. Delete `release-notes.md`.

## Skills shared with the maintainer's base

The maintainer's own base (the `brain` repository) is older than this repository and is
not an instance of it yet. Until it adopts the template, the two share a set of skills.

- A change to a shared skill is made **here** first, then ported by hand into `brain`:
  template → `brain`, never the other way.
- `scripts/check-kb-template-drift.sh` in the `brain` repository lists the shared skills
  and reports any difference between the two copies.
- The port is done in `brain`. This repository gets no extra entry for it.

## How Claude Code loads these rules

Claude Code doesn't read `CONTRIBUTING.md` on its own, and a root `CLAUDE.md` is not an
option: it would ship to every clone, and `/b:onboard` writes its own. So each checkout has
a git-ignored `CLAUDE.local.md` that imports this file. Create it once in the repo root:

```bash
printf '@CONTRIBUTING.md\n' > CLAUDE.local.md
```

`CLAUDE.local.md` is listed in `.gitignore`, so it stays on your machine and never reaches
an instance. It lives only in the checkout where you created it, so a new clone or git
worktree needs it again. To check that it loads, ask a new session what this file requires
before a commit.
