# Design

## Context

See `proposal.md` for the reasons. The model itself was approved on 2026-10-13 by the
maintainer, outside this repository. It has three layers: the template, the instances,
and a control project that only reads instance stamps. An update is a pull inside the
instance: a session opened in the instance runs `brain-upgrade` and commits the result.
This document carries that model over and settles the details it leaves open.

Facts checked on 2026-10-13 that shape the approach:

- **History.** 19 commits since 2026-06-16; the first 16 are `sync from brain@…` mirror
  commits. One tag, `v0.1.0` (`c8407e2`), with a GitHub Release. Instances were created
  from several of those states, so adoption has to recognise more than tagged releases.
- **Generations.** Skill directories were renamed (`ingest` → `brain-ingest`) between
  generations. The oldest generation (`brain-test2`, 2026-07-03) still has the old names
  and no `CHANGELOG.md`, `ENVIRONMENTS.md`, `LICENSE`, `.github/` or `.claude/agents/`.
- **Render inputs.** The three instances checked (`second-brain-demo-recipes`,
  `agentic-ai-system-brain`, `brain-test2`) each have `.kb-onboard.json` on disk, but the
  template's `.gitignore` ignores it, so none of them has it in git.
- **Local edits.** `README.md` is unchanged from the template in all three. `schema.yml`
  says in its own header that owners should edit it.
- **Archive commit.** `git archive --format=zip v0.1.0` stores the commit SHA as the
  zip-file comment. GitHub builds its source archives with `git archive`.
- **Rendered files.** `render.py` renders only from the `*.template.md` files, and
  onboarding deletes those. An instance can therefore re-render only with the new
  version's template text, which the update source provides.
- **No git required.** Instances may run without a terminal, without git and offline:
  the README offers "Download ZIP". Python 3 is already required by reindex and lint.

## Goals / Non-Goals

**Goals:**

- Run an upgrade or an adoption without git and without network, given a local source.
- Never overwrite an owner's edit without asking. Ask only when the template and the
  owner both changed the same file.
- Keep the whole result reviewable: a plan before any write, one commit after it.
- Let the instances that exist today come under the mechanism, including pre-`0.1.0`
  generations.

**Non-Goals:**

- Executable migration steps for breaking changes. `0.2.0` shows **BREAKING** entries from
  `CHANGELOG.md`, and the agent walks the owner through them.
- Updating starter `content/`, or merging upstream note changes into notes.
- Downgrades, and upgrades to a version older than the instance's stamp.
- A fleet report, and notices such as "an update is available" at session start.
- Running `brain-upgrade` on any real instance. The pilot is a separate task.

## Decisions

### D1. Four file classes, with the author class kept out at every exit *(brief decision 1)*

`.kb-manifest.json` lists glob patterns per class. Every tracked file is classified by
the first class that matches, in the order **author → rendered → owned → seeded**. Owned
patterns are explicit. Owned is not a catch-all, so stray files in a source directory
(`graft/`, `__pycache__/`, `.claude/settings.local.json`) are never shipped. A manifest
`exclude` list drops such files explicitly, and the dry run lists any other source file
that matches no class.

| Class | Patterns (0.2.0) | Onboarding | Upgrade |
|---|---|---|---|
| author | `openspec/**`, `CONTRIBUTING.md`, `CLAUDE.local.md`, `dev/**` | deleted | never copied; a pristine leftover is proposed for deletion |
| rendered | `CLAUDE.md` ← `CLAUDE.template.md`, `AGENTS.md` ← `AGENTS.template.md`, `content/WRITING_STYLE.md` ← `content/WRITING_STYLE.template.md` | rendered, templates deleted | re-render on request only (D7) |
| owned | `.claude/**`, `.githooks/**`, `.github/**`, `tests/**`, `.kb-manifest.json`, `.editorconfig`, `.gitattributes`, `.gitignore`, `.npmrc`, `.prettierrc`, `package.json`, `requirements.txt`, `schema.yml`, `ENVIRONMENTS.md`, `CHANGELOG.md`, `LICENSE` | kept | three-way update (D6) |
| seeded | `content/**`, `README.md` | kept, `content/` pruned as today | never written; changes listed as information |

Patterns only classify files in a template tree. **Inside an instance, a file counts as
template-owned only by its concrete path:** a path the source version ships, a path in
the stamp, or a path in the history index (D9). The `.claude/**` pattern therefore never
claims an instance's own skills or its `settings.local.json`.

`LICENSE` and `schema.yml` are owned. Three-way comparison leaves a locally edited file
alone until the template also changes it, so an owner may edit them without being asked
at every upgrade.

**`README.md` is seeded** (the maintainer's decision, 2026-10-13). The template's README is
the product page: it describes the template and the course. In an instance, the owner
either describes their own knowledge there or has no use for the file. Template wording
fixes should not reach every base, and they should not raise a question in any of them.
An upgrade lists a changed upstream README as information only.

*Rejected:* README as owned with the three-way rule. Every base that rewrote its README
would get a question whenever the template's text changed. Every base that kept it would
receive product-page edits that say nothing about its own knowledge.

The **author class** is kept out by three independent measures:

1. `.gitattributes` marks the author paths `export-ignore`, so GitHub "Download ZIP" and
   every release archive lack them.
2. `brain-upgrade` never copies author files, even from a full local clone.
3. Onboarding deletes them from a fresh `git clone` or "Use this template" copy.

As a guard, onboarding refuses to start when `CLAUDE.local.md` exists. Only the
template's author checkout has that file, and onboarding there would wipe the source.

*Rejected:*

- **Leaving author files in instances "harmlessly".** They are not harmless.
  `CONTRIBUTING.md` tells any agent that reads it that the repository is the template
  source and forbids `/b:onboard`. `openspec/` would show the template's change history to
  an owner who uses OpenSpec for their own base, and it would go stale because upgrades
  never refresh it.
- **Manifest exclusion without onboarding removal.** Clones would keep `CONTRIBUTING.md`,
  which is the problem follow-up 1 reported.
- **Moving author files to another repository.** This contradicts the 2026-10-13
  decision to keep the specification here.

### D2. The version lives in the manifest, and the tag names the release commit *(brief decision 2)*

- `.kb-manifest.json` holds `"version": "X.Y.Z"` next to the classes, because a class
  list belongs to one version. `package.json` drops its `version` field (npm does not
  need it for a private package).
- A **release** is one commit on `main`. It renames `[Unreleased]` to
  `## [X.Y.Z] - YYYY-MM-DD`, sets the manifest version and regenerates the history index
  (D9). An annotated tag `vX.Y.Z` (the existing `v0.1.0` convention) marks that commit,
  and a GitHub Release is published from the tag with the `CHANGELOG.md` section as its
  notes. Tags are never moved. A defect gets a new patch release.
- The release check (`dev/check_manifest.py`) requires that the manifest version equals
  the newest `## [X.Y.Z]` heading. That holds between releases (`[Unreleased]` on top,
  the last release below it) and on the release commit itself.
- The **stamp** always records `version`, read from the source manifest. It records
  `commit` only when the source proves it:
  - a git source: the resolved ref;
  - a release `.zip`: the zip comment that `git archive` writes;
  - an unpacked directory, or a "Use this template" copy whose history is gone: `null`.

  For a released version, `null` loses nothing, because the tag `vX.Y.Z` names the
  commit. Onboarding records a commit only when HEAD is the commit tagged `v<version>`.
- Between releases, `main` carries the last released version, so a ZIP of `main` is
  "X.Y.Z plus unreleased changes". That is harmless: every decision is made from per-file
  hashes, and the version only selects which `CHANGELOG.md` sections to show.

*Rejected:*

- **A separate `VERSION` file:** a second file that has to change together with the
  manifest.
- **`package.json`:** Node is optional here, and owners may edit that file.
- **Git tags as the only record:** ZIP instances have no git.
- **A `-dev` suffix on `main`:** it needs a bump commit after every release and a guess at
  the next version.
- **An `export-subst` commit placeholder in the manifest:** the manifest's content, and
  so its hash, would then depend on how it was downloaded.

### D3. Update sources, and the engine runs from the source *(brief decision 3)*

`brain-upgrade` resolves one source, in this order:

1. **`--source <path>` to a directory.**
   - If it is a git working copy and git is available, files are read with
     `git archive <ref>` (so `export-ignore` applies, and untracked or ignored files
     never leak in). `--ref` defaults to the tag `v<manifest version>`, else HEAD, with a
     "not a release" warning for HEAD.
   - Otherwise the directory is used as is (an unpacked release), filtered by the manifest.
2. **`--source <file.zip>`:** a release archive. A single top-level folder is stripped,
   and the commit is read from the zip comment.
3. **No `--source`:** download over HTTPS with `urllib`.
   - The repository comes from the stamp, or from the source manifest when adopting
     (`plipowczan/second-brain-template` by default, so instances made with "Use this
     template" follow upstream).
   - The version comes from `--to`, else from `GET /repos/<repo>/releases/latest`.
   - The archive is `https://github.com/<repo>/archive/refs/tags/v<version>.zip`. It is
     saved to the OS temp directory, and its path is printed for offline reuse.
4. **Offline with no `--source`:** stop before any change, and say how to pass a release
   zip or a local clone.

The dry run then needs only local data: the instance, its stamp, and the source tree.

**The engine runs from the source version.** The instance's `brain-upgrade` is a thin
launcher: it gets the source, then runs `<source>/.claude/skills/brain-upgrade/scripts/upgrade.py`.
New logic therefore handles the new layout. This also covers bootstrapping: every instance
that exists today lacks the skill, so its session runs the release's engine directly
(`python <release>/.claude/skills/brain-upgrade/scripts/upgrade.py plan --instance .
--adopt`), or the agent follows the release's `SKILL.md`.

*Rejected:*

- **`git pull` or a merge from a template remote:** it needs git. It also fails on "Use
  this template" histories, which are unrelated to the template's history.
- **A pip or npm package:** a new install step for course participants.
- **An engine fixed in the instance that reads the new source as data:** an old engine
  cannot know the rules of a newer layout.

### D4. Scope against the seven PL-479 follow-ups *(brief decision 4)*

As recommended in the brief, with two refinements recorded in `proposal.md`:

- Follow-up 6 needs no work, because `CONTRIBUTING.md` already documents it.
- Follow-up 4 is touched only by classifying `kb-maintain.yml` as owned.

The release group in `tasks.md` waits until the two pre-release changes (follow-ups 2 and
3) are merged.

### D5. Content hashes that ignore line endings

Each hash is `sha256:` plus the hex digest of the file's bytes. Text files (no NUL byte)
are hashed with CRLF converted to LF first; binary files are hashed raw.

Windows editors and `core.autocrlf` change line endings without changing content.
Without the normalisation, every such file would show up as "locally modified".

### D6. Three-way decision for owned files

For each owned path, compare three hashes:

- **B:** the baseline, the hash in the stamp;
- **S:** the source, the new version;
- **L:** the local file, or absent.

| Case | Outcome |
|---|---|
| `L == S` | up to date, nothing to do |
| `L == B`, `S != B` | update (pristine file) |
| `S == B`, `L != B` | keep the local edit; report it |
| `B`, `S`, `L` all differ | conflict: owner picks keep / overwrite / merge |
| new in S, L absent | add |
| new in S, L present and different | conflict (the instance has its own file at that path) |
| B present, S absent | propose deletion: checked if `L == B`, unchecked with a warning if not |
| B and S present, L absent | the owner deleted it: stays deleted unless they choose to restore it (e.g. an opted-out `kb-maintain.yml`) |

The new stamp records **S**, never L. A file the owner kept edited therefore still shows
as edited at the next upgrade, instead of passing for pristine.

"Merge" means the agent edits the file with the owner after apply, using the diff and the
`CHANGELOG.md` entry. The scripts never auto-merge.

### D7. Rendered files

The stamp records two hashes for each rendered file: the template source it came from
(`template_hash`) and the output as written (`output_hash`).

- **No re-render requested:** the plan reports when the template text changed upstream.
- **Re-render requested** (`--rerender`, or in the review): the engine renders the source
  version's `*.template.md` with `.kb-onboard.json` using that version's `render.py`. It
  writes the result only when `L == output_hash`. Otherwise it shows a diff as a proposal
  and writes nothing.
- **A placeholder has no value:** the skill asks the owner and adds the answer to
  `.kb-onboard.json`.
- **`.kb-onboard.json` is missing:** proposals only.

`content/WRITING_STYLE.md` is the only file under `content/` that brain-upgrade may write,
and only when its re-render was explicitly requested.

`.kb-onboard.json` stops being git-ignored. The stamp is never ignored either. If an
upgrade finds an untracked `.kb-onboard.json`, its commit adds it and the plan says so.

### D8. Plan → apply → commit, driven by the agent

`upgrade.py` has four subcommands. All of them use only the Python standard library.

- **`plan`** writes a JSON plan to the temp directory and prints a summary: source,
  version range, `CHANGELOG.md` entries with **BREAKING** marked, and per-file actions.
  `--diff <path|all>` shows diffs. It writes nothing to the instance.
- **`apply --plan --decisions`** first checks every planned path against the hash in the
  plan and stops before writing anything if one has moved. In a git instance it also
  refuses while a planned path has uncommitted changes. It then writes the adds, updates,
  chosen overwrites, confirmed deletions and requested re-renders. It writes the stamp and
  returns the files waiting for a merge. Without git, it first copies each file it
  replaces or deletes to `.kb-upgrade-backup/<version>-<UTC timestamp>/`.
- **`commit --plan`** stages exactly the planned paths plus the stamp (and
  `.kb-onboard.json` when it becomes tracked). It makes one commit,
  `chore(template): upgrade to <repo> <version>`, and leaves unrelated uncommitted work
  alone. Without git it does nothing and says so.
- **`stamp`** records the current files as the baseline. Onboarding calls it right after
  rendering, when the files are pristine by definition.

`SKILL.md` drives the order: plan, then one review table (the same approve-or-edit form as
`/b:import`), then apply, then any merges, then commit. In an unstamped instance it runs
this cycle twice: first the adoption (D9), then the upgrade.

### D9. Adoption through a history index

`dev/build_known_hashes.py` runs at release time. It walks every commit reachable from the
release commit, hashes (D5) every file that the current patterns classify as owned or
author, and writes `.claude/skills/brain-upgrade/known-hashes.json`. For each path, the
index maps each hash to the template states that shipped it (commit, date, and release if
there is one). Old paths such as `.claude/skills/ingest/SKILL.md` match `.claude/**`, so
they are included.

**Adoption is its own operation, with its own commit** (the maintainer's decision,
2026-10-13). `--adopt` aligns the instance with the nearest template release R and writes
a stamp that names R. The upgrade from R to the new version is a separate, ordinary
stamped upgrade with its own plan and commit. The one-commit-per-upgrade rule stays, and
adoption is simply not an upgrade.

- **Pristine files.** A local file is pristine if its hash appears in the index for its
  path. Any other file that differs from R is a local edit. This also recognises files
  that owners re-pulled one at a time, as the changelog told them to.
- **The nearest release R** is the tagged release, no newer than the source, whose files
  the instance matches best (ties go to the older one). R is always a real release. A
  generation older than `v0.1.0` that still has the pre-rename skill directories gets
  `0.1.0`. The adoption dry run shows R's `CHANGELOG.md` section.
- **Alignment only moves forward.**
  - A pristine file from an older state is updated to R's content.
  - A file R ships that the instance lacks is planned as an addition, which the owner
    can deselect (it may have been deleted on purpose).
  - A pristine file at a path R does not ship is planned as a selected deletion.
  - A pristine file from a state newer than R stays as it is. Its baseline is its own
    hash, so the next upgrade can still update it without a question.
  - A locally edited file stays as it is, is reported, and gets R's hash as its baseline,
    so the next upgrade still sees it as edited.
  - No file is ever moved to an older template state.
- **R's content** comes from the same places as any source. If the source is R's release
  itself (its tag or its archive), the source is used. A source that only carries R's
  version number, such as `main` between releases, does not count. If the source is a git clone, R is read from that clone's
  tag `v<R>`. Otherwise R's archive is downloaded from the repository. Offline, the owner
  passes `--base <zip|dir>`, and without it adoption stops before any change and names
  the release it needs.
- **Rendered files are never written** during adoption. The engine renders R's templates
  with `.kb-onboard.json`. If the local file equals that rendering, the stamp records its
  output hash, and later upgrades may re-render it on request. If not, the stamp records
  `null` and later upgrades only propose. The difference to the new rendering is shown
  either way.
- **When R equals the source version**, the adoption also brings the instance up to date,
  and the following upgrade reports "up to date".

The two commits are `chore(template): adopt <repo> <R>`, then
`chore(template): upgrade to <repo> <version>`.

*Rejected:*

- **Adoption and upgrade in one plan and one commit** (the first draft). For an old
  generation the combined diff is too large to review, and it cannot be reverted in parts.
- **Adoption that writes only the stamp and no files.** It does not split the large diff,
  which is the reason for having two operations. It would also leave the following
  upgrade with a diff that matches no `CHANGELOG.md` range.
- **Comparing only with the newest release:** every file of an older generation would
  become a question.
- **Requiring a git clone of the template to walk its history:** course participants
  without git could not adopt.

### D10. Packaging and tests

- **`.claude/skills/brain-upgrade/`:** `SKILL.md`, `scripts/upgrade.py` with a helper
  module, `unittest` suites next to them, and `known-hashes.json`.
- **`.claude/commands/b/upgrade.md`:** the `/b:upgrade` wrapper.
- **`tests/run_tests.py`** gains the brain-upgrade suite. When `dev/` exists (only in the
  template source), it also runs `dev/check_manifest.py`, because a check of every tracked
  file would fail in an instance.
- **`dev/`** (author class) holds `check_manifest.py` (classification, version against
  `CHANGELOG.md`, no duplicate section headings within a version) and
  `build_known_hashes.py`.
- **`CONTRIBUTING.md`** gains a "Releasing" checklist.

## Risks / Trade-offs

- **The engine is code downloaded from a release, and it runs.**
  → It comes only from the repository recorded in the stamp, over HTTPS. That is the same
  trust as the original clone. A dry run is always first, and nothing is written before
  the owner approves the plan.
- **Generations made from `brain/kb-template` states that were never synced here** are not
  in the index, so adoption treats their files as local edits and asks more questions.
  → The dry run shows them all in one table, and `brain-test2` exercises this case in the
  fleet task.
- **The GitHub archive layout or the API changes,** or the unauthenticated rate limit of
  60 calls an hour is hit.
  → The engine tolerates any single top-level folder and a missing zip comment
  (`commit: null`). It makes one API call per run, and `--to` or `--source` avoids even
  that.
- **A partial write when apply fails mid-way.**
  → Apply checks everything before its first write. Recovery is `git restore` in a git
  instance, and the backup folder otherwise.
- **`export-ignore` lines ship to instances in `.gitattributes`,** so an instance's own
  `git archive` would also drop a root `openspec/`, `dev/` or `CONTRIBUTING.md`.
  → Accepted. Instances do not publish through `git archive`. Recorded in `CHANGELOG.md`.
- **The first adoption of an old generation produces a large diff.**
  → It is split in two: the adoption brings the instance to the nearest release, and the
  upgrade goes from that release to the new one. Each part has one table, deselectable
  additions, and one commit that can be reverted on its own.
- **Adopting an instance older than the source needs a second release's content**, and
  offline that means a second archive.
  → A git clone of the template provides every tag. Without one, adoption names the
  release it needs and stops before any change.
- **`.kb-onboard.json` becomes committed.** Its contents (name, owner, topics, voice)
  already appear in the committed `AGENTS.md`, so nothing new is disclosed.

## Migration Plan

1. Merge this change. The two pre-release changes (follow-ups 2 and 3) land separately.
2. Release `0.2.0`: merged `[Unreleased]` → `[0.2.0]`, manifest version, regenerated
   index, tag, GitHub Release.
3. The pilot `second-brain-demo-recipes` runs the engine from the `0.2.0` release (D3).
   It adopts first, in its own commit, and then upgrades, unless the adoption already
   aligned it to `0.2.0`. Fixes ship as `0.2.1`. The rest of the fleet follows,
   with the maintainer's base last.
4. Rollback:
   - **An instance:** `git revert` of the upgrade commit, the adoption commit, or both,
     or a restore from `.kb-upgrade-backup/` without git.
   - **The template:** a patch release supersedes a bad one. Tags stay.
