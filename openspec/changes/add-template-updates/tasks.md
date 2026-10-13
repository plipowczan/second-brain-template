# Tasks

Every commit follows `CONTRIBUTING.md`: a `CHANGELOG.md` entry under `[Unreleased]` in
the same commit, and `python tests/run_tests.py` ends with `ALL PASS`. A task that
changes skill scripts also runs that skill's own `python -m unittest`.

## 1. Manifest, file classes and the release check

- [x] 1.1 Merge the duplicated `### Fixed` and `### Changed` sections under
  `[Unreleased]` in `CHANGELOG.md` without losing or rewording any entry (follow-up 5).
  Verify that the merged sections contain the same bullet count as before and that each
  heading appears once.
- [x] 1.2 Add `.kb-manifest.json`:
  - format `1`, version `0.1.0`, repository `plipowczan/second-brain-template`;
  - the author, rendered, owned and seeded classes, and the `exclude` list, as in design
    D1, with `README.md` in the seeded class.

  Remove `version` from `package.json`. Verify that the manifest loads with
  `python -c "import json; json.load(open('.kb-manifest.json'))"` and that
  `npm run format` still starts.
- [x] 1.3 Write `dev/check_manifest.py`. It fails when:
  - a tracked file matches no class;
  - the manifest version differs from the newest `## [X.Y.Z]` heading;
  - `package.json` has a `version`;
  - a section heading repeats within one version block.

  Verify that it passes on the repository and fails, naming the culprit, on a temp copy
  with an unclassified root file and on a temp copy with a duplicated `### Fixed`.
- [x] 1.4 Make `tests/run_tests.py` run `dev/check_manifest.py` when `dev/` exists and
  skip it otherwise. Verify `ALL PASS` here, and that the step is skipped in a temp copy
  without `dev/`.
- [x] 1.5 Mark the author paths `export-ignore` in `.gitattributes`. Verify that
  `git archive --format=zip HEAD` lists no `openspec/`, `dev/` or `CONTRIBUTING.md` entry.
- [x] 1.6 Remove the `.kb-onboard.json` line from `.gitignore`. Verify that
  `git check-ignore .kb-onboard.json .kb-template.json` matches neither file.
- [x] 1.7 Update the "What ships, and in what form" table in `CONTRIBUTING.md` to the four
  classes, with `.kb-manifest.json` as their source of truth. `README.md` moves from
  "shipped as is" to seeded. Add the `CHANGELOG.md` entries for 1.2, 1.5 and 1.6. Verify
  that every path in the table appears in the manifest.

## 2. Engine core: hashing, manifest, sources, stamp

- [x] 2.1 Create `.claude/skills/brain-upgrade/scripts/` with a stdlib-only helper module.
  It covers manifest loading, classification by first match, concrete-path ownership, and
  the hash from design D5. Verify with unit tests for CRLF/LF equality, binary files, the
  class order, `exclude`, and an instance-only skill that is never claimed.
- [x] 2.2 Implement source resolution:
  - a plain directory;
  - a git working copy read through `git archive <ref>`, with the ref defaulting to
    `v<version>`, else HEAD with a warning;
  - a `.zip`, stripping the single top-level folder and taking the commit from the zip
    comment;
  - a download via `releases/latest` or `--to`, into the temp directory, with the path
    printed;
  - an offline stop with guidance.

  Verify with unit tests on local fixtures: a temp git repo with a tag, an archive made by
  `git archive`, a stub URL opener for the download, and a simulated network error. No
  test touches the network.
- [x] 2.3 Implement reading and writing the stamp, and the `upgrade.py stamp`
  subcommand. Verify with unit tests that its output holds every field from the
  instance-stamp spec, that the commit is `null` without proof, and that a tagged HEAD
  yields the tag's commit.

## 3. Planning (the dry run)

- [x] 3.1 Implement the three-way planner for owned files (design D6), including
  additions, collisions, local deletions and deletion proposals that are selected or
  unselected. Verify with one unit test per scenario of the "Owned files follow a
  three-way decision" and "Files removed from the template" requirements.
- [x] 3.2 Implement rendered-file planning with the source's `render.py` (design D7):
  re-render only on request and only when untouched, a diff proposal otherwise, a
  missing placeholder reported as a question, and proposals only when `.kb-onboard.json`
  is missing. Verify with unit tests for each rendered-file scenario.
- [x] 3.3 Implement seeded and author handling. Seeded changes are information only. An
  author-class leftover is proposed for deletion only when it is pristine. Verify with
  unit tests that no seeded path, `README.md` included, ever appears among the write
  actions or the questions.
- [x] 3.4 Implement the `CHANGELOG.md` extraction, with **BREAKING** entries marked: the
  range between two versions for an upgrade, and a single version's section for an
  adoption. Verify with unit tests that the range starts after the stamp version and
  that a single-version request returns only that section.
- [x] 3.5 Implement `upgrade.py plan`, covering:
  - the JSON plan written to the temp directory;
  - the summary, and `--diff <path|all>`;
  - warnings for a non-release source, an untracked `.kb-onboard.json` and uncommitted
    planned paths;
  - an up-to-date report, and a refusal of an older source.

  Verify with a unit test that hashes the whole instance tree before and after `plan` and
  finds it unchanged.

## 4. Apply and commit

- [x] 4.1 Implement `upgrade.py apply --plan --decisions` (design D8):
  - check every planned path before the first write;
  - refuse when a planned path is dirty in git;
  - write the selected actions and requested re-renders;
  - make the backup folder when there is no git;
  - write the stamp with the source hashes;
  - list the files waiting for a merge.

  Verify with unit tests for a stale plan (nothing written), a dirty path (refused),
  the no-git backup contents, a stamp that records S for a kept local file, and
  `content/` byte-identical after apply.
- [x] 4.2 Implement `upgrade.py commit --plan`: stage only the planned paths, the stamp
  and a newly tracked `.kb-onboard.json`, then make one commit, `chore(template): adopt
  <repo> <R>` for an adoption plan and `chore(template): upgrade to <repo> <version>`
  otherwise. Without git, it reports and exits 0. Verify in a temp git repo that has an unrelated dirty note: exactly one new
  commit, and the note still dirty afterwards.

## 5. Adoption

- [x] 5.1 Write `dev/build_known_hashes.py` to generate
  `.claude/skills/brain-upgrade/known-hashes.json` from every commit reachable from HEAD
  (design D9), and commit the first generated index. Verify that the index contains the
  `v0.1.0` hash of `.claude/skills/ingest/SKILL.md` and of `.claude/hooks/load_vault_map.py`,
  and that a second run produces a byte-identical file.
- [x] 5.2 Implement `--adopt` planning (design D9):
  - a plain upgrade without a stamp stops and suggests `--adopt`; `--adopt` with a stamp
    is refused;
  - pristine detection by the index;
  - the nearest release R, always a tagged release no newer than the source;
  - forward-only alignment to R: older pristine files updated, missing files added as
    deselectable, pristine paths R does not ship deleted, newer pristine files and local
    edits left alone with the baselines from D9;
  - proposals only for rendered files, with the output hash recorded only when the file
    equals R's rendering.

  Verify with unit tests on a fixture index that simulates a pre-`0.1.0` instance, an
  instance between releases, and an instance with one file re-pulled from a newer state
  that must not be rewound.
- [x] 5.3 Obtain R's content: the source itself only when it is R's release, the tag
  `v<R>` of a git-clone source, a download, or `--base <zip|dir>`. Offline without any of
  these, stop and name the release. Verify with unit tests on a temp git repo with two
  tags, a stub download, and the offline stop (nothing written).
- [x] 5.4 Add an adoption case to `tests/run_tests.py`. It builds, in temp directories, a
  synthetic old generation (pre-rename skill paths, no `CHANGELOG.md`), a synthetic
  older release R and a newer source. It runs adoption (`plan --adopt`, `apply`,
  `commit`) and then an upgrade (`plan`, `apply`, `commit`), and asserts:
  - two commits;
  - an adoption stamp naming R, and an upgrade stamp naming the source version;
  - no file rewound;
  - an untouched `content/` and `README.md`.

  Verify `ALL PASS`.

## 6. Skill, command, onboarding and docs

- [x] 6.1 Write `.claude/skills/brain-upgrade/SKILL.md` as the thin launcher from design
  D3 and D8: resolve the source, run the source's engine, then plan, one review table,
  apply, merges with the owner, and commit. For an unstamped base, run that cycle for the
  adoption first, then offer the upgrade as a second cycle. Include the bootstrap path
  for bases without the skill. Add `.claude/commands/b/upgrade.md`. Verify that the frontmatter `name`
  matches the directory, and that following the skill in a scratch instance produces a
  dry run without writes.
- [x] 6.2 Change `.claude/skills/brain-onboard/SKILL.md`:
  - refuse when `CLAUDE.local.md` exists;
  - after the renders succeed, delete the `*.template.md` files and every author-class
    file listed in the manifest;
  - write the stamp with `upgrade.py stamp`.

  Verify in a scratch clone (`git clone . ../kb-onboard-test`) that onboarding leaves no
  `openspec/`, `dev/` or `CONTRIBUTING.md`, and writes a stamp holding version `0.1.0`.
  Verify also that it refuses in a copy that has `CLAUDE.local.md`.
- [x] 6.3 Add the brain-upgrade unit suite to `tests/run_tests.py`, next to the curate
  suite. Verify `ALL PASS`.
- [x] 6.4 Document updating:
  - an "Updating your base" section in `README.md`, covering git, no git and offline, and
    the first `--adopt`;
  - a `/b:upgrade` row in the README skills table;
  - an **UPGRADE** line in the Workflows list of `AGENTS.template.md`;
  - one paragraph in `ENVIRONMENTS.md` on upgrading without a terminal.

  Verify that `render.py` still renders `AGENTS.template.md` with a sample values file,
  and that `brain-onboard`'s `test_render.py` passes.
- [x] 6.5 Add the `CHANGELOG.md` entries for brain-upgrade, `--adopt`, the onboarding
  changes and `README.md` becoming seeded. Include "Existing bases" bootstrap steps: run
  the `0.2.0` release's engine with `--adopt`, commit, then upgrade. Verify that `dev/check_manifest.py` passes.
- [x] 6.6 Add a "Releasing" checklist and the `dev/` tools to `CONTRIBUTING.md`. Verify
  that each command in the checklist runs as written on a scratch branch, stopping before
  the tag.

## 7. End-to-end checks

- [x] 7.1 Git round trip in scratch directories:
  - onboard a clone;
  - edit `schema.yml` and one skill file;
  - build a "next version" source with a changed hook, a removed file and a changed
    `AGENTS.template.md`;
  - run `/b:upgrade` as the skill describes.

  Verify one commit, the edited `schema.yml` kept (it was unchanged upstream), the
  conflict asked about only for the skill file, and `content/` untouched.
- [x] 7.2 No-git, offline round trip: unpack `git archive` output as an instance, then
  upgrade with `--source <zip>` and no network. Verify that the backup folder holds every
  replaced file and that the stamp's commit equals the zip comment.
- [x] 7.3 Adopt, with this clone as the source, a `git archive` copy of a pre-`0.1.0`
  commit (for example `4d38b2b`) that carries rendered files and a `.kb-onboard.json`
  fixture. Verify:
  - R is reported as `0.1.0`;
  - unmodified files raise no conflicts and are moved forward to `0.1.0`, and none is
    rewound;
  - the adoption is one commit.

  Then upgrade it. Verify a second commit, and that the pre-rename skill directories are
  proposed for deletion in that upgrade.

## 8. Release 0.2.0 (after this change is merged)

- [ ] 8.1 Gate: confirm that the separate changes for follow-up 2 (`lint_scan.py` and
  `content/_privacy.md`, then the `.githooks/pre-commit` path) and follow-up 3 (CI on push
  and pull request) are merged, or record the maintainer's decision to release without
  them.
- [ ] 8.2 Release commit on `main`:
  - rename `[Unreleased]` to `## [0.2.0] - <date>`;
  - set the manifest version to `0.2.0`;
  - regenerate `known-hashes.json`.

  Verify that `dev/check_manifest.py` and `python tests/run_tests.py` pass.
- [ ] 8.3 Create the annotated tag `v0.2.0`, push it, and publish a GitHub Release with
  the `[0.2.0]` section as notes. Verify that
  `upgrade.py plan --instance <scratch> --adopt --to 0.2.0` downloads
  `archive/refs/tags/v0.2.0.zip` and records a commit equal to `git rev-parse v0.2.0^{commit}`.
