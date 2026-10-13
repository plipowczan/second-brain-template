# Proposal

## Why

`CHANGELOG.md` is written "for people who want to pull improvements into their own base",
but nothing can pull them. An instance does not even know which template version it was
created from: `.kb-onboard.json` holds only the onboarding answers, and every update so far
has meant reading the changelog and re-copying files by hand. Since 2026-10-13 this
repository is the single source of the template, so it is now the place to build the
update path. It ships as `0.2.0`. The first instance to receive it is
`second-brain-demo-recipes`.

## What Changes

- **Versioned releases.** The template version (SemVer) lives in a new root manifest,
  `.kb-manifest.json`. A release is one commit tagged `vX.Y.Z` and published as a GitHub
  Release whose notes are its `CHANGELOG.md` section. `package.json` loses its `version`
  field, so the manifest is the only place that holds the number.
- **File-class manifest.** `.kb-manifest.json` sorts every tracked file into one of four
  classes: **owned** (template files that are kept current in instances), **seeded**
  (starter `content/`, which belongs to the instance once it is copied), **rendered**
  (`CLAUDE.md`, `AGENTS.md`, `content/WRITING_STYLE.md` and the `*.template.md` they come
  from) and **author** (`openspec/`, `CONTRIBUTING.md`, `CLAUDE.local.md`, `dev/`), which
  never reach an instance. A check fails on any tracked file that has no class.
- **Instance stamp `.kb-template.json`.** It records the template version, the template
  commit when the source can prove it, and content hashes of the owned and rendered files
  as the template shipped them. With those hashes, an offline upgrade can tell a template
  file the owner never touched from one they edited.
- **New skill `brain-upgrade` (`/b:upgrade`).** It defaults to a dry run that shows the
  `CHANGELOG.md` entries between the two versions and a per-file plan with diffs. Owned
  files are compared three ways (template baseline, new template, local), so the skill asks
  only when both the template and the owner changed a file. It proposes deleting files
  the template has removed, re-renders instruction files only on request and only if they
  were not edited by hand, and never touches `content/`. With git, each upgrade is one
  commit. Without git, the skill backs up every file before replacing or deleting it.
- **Update sources that work without git and offline:** a local template clone, an
  unpacked release, a release `.zip`, or a download of the release archive over HTTPS
  with the Python standard library. The upgrade logic always runs from the new version's
  source. That way it knows the new layout, and an instance that has no `brain-upgrade`
  yet can run it straight from a downloaded release.
- **`brain-upgrade --adopt`** for instances without a stamp, including generations older
  than `0.1.0`. Each release ships an index of every content hash that owned and author
  files have had in the template's history. Adoption uses it to recognise unmodified
  older template files, finds the closest release, and plans the adoption and the upgrade
  as one reviewed commit.
- **Onboarding changes.** `/b:onboard` now writes the stamp, deletes author-class files
  from a fresh clone, and refuses to run in a checkout that has `CLAUDE.local.md` (the
  template source).
- **Author files stay out of archives.** `.gitattributes` marks them `export-ignore`, so
  GitHub "Download ZIP" and release archives never contain them.
- **`.kb-onboard.json` is no longer git-ignored.** Every instance checked on 2026-10-13
  had the file locally but had never committed it, so the render inputs were lost in any
  other clone.
- **`CHANGELOG.md` cleanup.** The duplicated `### Fixed` and `### Changed` sections under
  `[Unreleased]` are merged. A check keeps any section heading from appearing twice within
  one version.

No change is **BREAKING**: existing bases keep working as they are until their owner runs
`--adopt`.

## Scope against the PL-479 follow-ups

Making this repository the source surfaced seven follow-ups. This change takes:

1. **Author files in instances**: the author class, `export-ignore`, removal at onboarding.
5. **Duplicated `[Unreleased]` sections**: merged here, and kept from coming back by the
   release check.

These stay outside the change:

- **Before the `0.2.0` release, as two small separate changes:**
  - **2:** `lint_scan.py` reports `content/_privacy.md`; then fix the path in
    `.githooks/pre-commit`. It is a shared skill with its own port to `brain`.
  - **3:** CI on push and pull request running `tests/run_tests.py` and the per-skill
    suites. Publishing an upgrade engine from a public repository without CI is the
    larger risk.

  The release tasks here are gated on both.
- **4, later:** whether `kb-maintain` should run in the source, and bumping the action
  versions. This change only classifies `.github/workflows/kb-maintain.yml` as owned.
- **6, nothing to do:** `CONTRIBUTING.md` already says that a new clone or worktree needs
  its own `CLAUDE.local.md`.
- **7, belongs to the maintainer's base (PL-483):** the drift check in `brain`.

## Capabilities

### New Capabilities

- `template-manifest`: the four file classes, how each one behaves at onboarding and at
  update time, and the rule that ownership inside an instance is decided by concrete paths.
- `template-releases`: the single version number, the release commit and its tag, the
  release check, and the history index that ships with each release.
- `instance-stamp`: the `.kb-template.json` record, line-ending-independent content
  hashes, and when onboarding and upgrades write it.
- `template-upgrade`: `brain-upgrade` — update sources, dry run, three-way decisions for
  owned files, rendered files, deletions, the one-commit rule and backups without git.
- `template-adoption`: `brain-upgrade --adopt` for unstamped instances of any generation.

### Modified Capabilities

None. `openspec/specs/` is empty: this is the first OpenSpec change in the repository.

## Impact

- **New:** `.kb-manifest.json`; `.claude/skills/brain-upgrade/` (SKILL.md, stdlib-only
  scripts with unit tests, the known-hashes index); `.claude/commands/b/upgrade.md`;
  `dev/` with the author tools (manifest and release check, index builder).
- **Changed:** `.claude/skills/brain-onboard/SKILL.md`, `.gitattributes`, `.gitignore`,
  `package.json`, `tests/run_tests.py`, `CHANGELOG.md`, `CONTRIBUTING.md` (file classes,
  release checklist), `README.md` and `AGENTS.template.md` (how to update).
- **Instances:** none until they upgrade. The first upgrade of an existing base runs
  `--adopt` from the `0.2.0` release, and its owner sees the whole plan before anything is
  written.
- **Dependencies:** none new. The upgrade scripts use only the Python standard library, so
  they run before `pip install -r requirements.txt`.
