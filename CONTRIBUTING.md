# Contributing to the template

These rules are for people who develop **the template itself**. If you cloned it to start
your own knowledge base, you don't need this file: run `/b:onboard` (see the
[README](README.md)), and you can delete `CONTRIBUTING.md` from your copy.

## This repository is the source

- Since 2026-10-13 this repository is the source of truth for the template. Make changes
  here, directly. Until then it was a mirror: the template was built inside the
  maintainer's own base and copied here in `sync from brain@…` commits. That sync is gone.
- Every knowledge base created from the template is an **instance**. Changes flow one way,
  template → instances. Don't build a change in an instance and copy it back here.
- Instances pick changes up through an **update**, not by copying files around by hand. A
  versioned update mechanism is planned for `0.2.0`. Until it ships, each `CHANGELOG.md`
  entry tells the owner of an existing base what to re-pull.
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
   throwaway vault and exercises reindex, lint, gaps and refactor, plus the curate unit
   tests.
3. If you changed a skill's scripts, also run that skill's own unit tests: `python -m
   unittest` from `.claude/skills/<skill>/scripts/`. `tests/run_tests.py` runs only the
   curate suite. The two `yt-dlp` integration tests in `brain-ingest` need `yt-dlp` and a
   network connection.
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

| Path | What it is | In an instance |
|------|------------|----------------|
| `CLAUDE.template.md`, `AGENTS.template.md`, `content/WRITING_STYLE.template.md` | Instruction templates with `{{PLACEHOLDERS}}` | `/b:onboard` renders them to `CLAUDE.md`, `AGENTS.md`, `content/WRITING_STYLE.md` and deletes the templates |
| everything else in `content/` | Starter content: example notes in `REFERENCE/`, note templates in `templates/`, a sample in `_raw/inbox/`, `_privacy.md`, prebuilt indexes | Copied once with the clone; from then on it belongs to the owner |
| `.claude/` (skills, `commands/b/`, agents, hooks, `settings.json`) | The workflows and their scripts | Shipped as is and kept current by updates |
| `.github/workflows/kb-maintain.yml`, `.githooks/` | Index and lint automation | Runs in the instance (the workflow also runs here) |
| `README.md`, `ENVIRONMENTS.md`, `CHANGELOG.md`, `LICENSE` | Documentation | Shipped as is |
| `CONTRIBUTING.md` | These rules | Ships with a clone today; meant to stay out of instances |

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
