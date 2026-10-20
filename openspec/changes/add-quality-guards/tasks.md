# Tasks

Every commit follows `CONTRIBUTING.md`: a `CHANGELOG.md` entry under `## [Unreleased]` in
the same commit (the first commit adds that heading above `## [0.2.1]`), and
`python tests/run_tests.py` ends with `ALL PASS`. A task that changes a skill's scripts
also runs that skill's `python -m unittest`. Commit by path, never `git add -A` or
`git add .`: the untracked `.agents/`, `.codex/` and `.ignore` and the modified
`.gitignore` belong to PL-550. The release (manifest version, history index, tag) is not
part of this change.

## 1. Scanner: source fields and missing source files

- [x] 1.1 In `lint_scan.py`, collect source values from `source` and `sources`, written as
  a scalar, a block list or a flow list, with quotes stripped (design D8). Verify with
  unit tests in `test_lint_scan.py` for each form, and that URLs, wikilinks and free text
  are not treated as paths.
- [x] 1.2 Add the `missing_source_file` class: `_raw/` and `content/_raw/` values resolved
  against the content root; for `_raw/inbox/<name>`, `fix=` when exactly one
  `_raw/processed/*_<name>` exists, `candidates=` when several do, a plain finding when
  none does. Verify with unit tests for one copy, two copies, no copy, an existing path
  (no finding), a `content/_raw/` value, and a missing YouTube archive path (plain
  finding).
- [x] 1.3 Add the top-level `warnings` list to the scanner output. Verify with unit tests
  that `total`, `issues` and `counts` keep their existing keys, and that a note valid
  under `0.2.1` with `source:` pointing at an existing file yields no finding in any class.
- [x] 1.4 Add the `CHANGELOG.md` entry (`Added`: both classes and the warnings list).
  Verify that `python -m unittest` in `.claude/skills/brain-lint/scripts/` passes.

## 2. Scanner: contradiction markers, and warnings downstream

- [x] 2.1 Add the `contradiction` class (design D7): one finding per note with its marker
  count, case-insensitive, markers inside fenced code blocks ignored, and the class
  included in `warnings`. Verify with unit tests for two markers (count 2), an uppercase
  type, a marker that appears only in a code block (no finding), and a note without
  markers.
- [x] 2.2 In `.github/workflows/kb-maintain.yml`, print the classes named in `warnings`
  under a "Warnings" heading, apart from "Issues". Verify by running the summary snippet
  locally on a scanner report that has both kinds. Then run `build_indexes.py` and
  `lint_scan.py` from the repo root and check that `git diff content/_indexes` shows only
  `updated:` lines.
- [x] 2.3 Extend `tests/run_tests.py`: a throwaway-vault note citing a missing
  `_raw/inbox/` file with one archived copy is reported with its `fix=`, `warnings` names
  both new classes, and `missing_frontmatter` and `schema_violation` stay at 0, so the
  unchanged pre-commit hook would let the commit through. Verify `ALL PASS`.
- [x] 2.4 Add the `CHANGELOG.md` entry for 2.1 and 2.2. Verify that
  `python tests/run_skill_tests.py` exits 0.

## 3. Answer gaps in `gaps.py`

- [x] 3.1 Add `--answers` (default `content/_outputs/answers`) and the `answer_gaps` key
  (design D9). Verify with unit tests in `test_gaps.py`: answers with `gaps: 2`, `gaps: 0`
  and no `gaps:` list only the first; ordering is newest first; a missing folder gives
  `[]`; the existing keys are unchanged.
- [x] 3.2 In `brain-gaps/SKILL.md`, add the answers with open gaps to the to-build list.
  Verify that the workflow step names `answer_gaps`, and that the gaps call in
  `tests/run_tests.py` still passes.
- [x] 3.3 Add the `CHANGELOG.md` entry. Verify that `python -m unittest` in
  `.claude/skills/brain-gaps/scripts/` passes.

## 4. Limits file and instruction pointers

- [x] 4.1 Write `LIMITS.md` in our own words (design D2): the five failure modes from the
  `method-limits` spec and the point that a tidy base is not a correct one, each with
  actions for the owner and for the agent. Verify that each failure mode is followed by
  at least one action.
- [x] 4.2 Add `LIMITS.md` to the owned list in `.kb-manifest.json`, and to the owned row
  of the "What ships" table in `CONTRIBUTING.md`. Verify that `python dev/check_manifest.py`
  passes and that the manifest classifies `LIMITS.md` as owned.
- [x] 4.3 Check delivery: in a scratch clone of the `v0.2.1` tag, run `upgrade.py plan`
  with this repository as the source and `--ref` set to the branch head. Verify that the
  plan lists `LIMITS.md` as an addition.
- [x] 4.4 In `AGENTS.template.md`, add the one-line pointer to `LIMITS.md` and change the
  frontmatter example to `sources:` with a `_raw/processed/` path (design D1). Verify by
  rendering the file with `brain-onboard/scripts/render.py` and a temporary values file:
  the output mentions `LIMITS.md` and holds no unresolved `{{`.
- [x] 4.5 Add the `CHANGELOG.md` entry. Verify `ALL PASS`.

## 5. `brain-ingest`

- [x] 5.1 Phase 0: accept `--batch` next to YouTube URLs, and keep aborting on any other
  argument. Update the failure table. Verify by reading the step against the `ingest-plan`
  spec requirement on the flag.
- [x] 5.2 Phase 1: read each source in full, build the coverage map (design D6), check it
  for contradictions, and send one message that holds the cluster options and one plan
  block per source; then wait. Cover cancellation and batch mode (the warning first,
  clusters as separate notes, no question). Verify by reading against every requirement
  of the `ingest-plan` spec.
- [x] 5.3 Phase 2: write the main note and the additions to existing notes, each with its
  source and a link in both directions; mark contradictions without overwriting; convert
  `source:` to `sources:` on a second source; choose the unique archive name before
  writing, and write the final `_raw/processed/` path for file sources. Verify by reading
  against the `ingest-coverage` and `source-traceability` specs and the writing rule of
  `contradiction-markers`.
- [x] 5.4 Phase 3: check that every `_raw/` path written exists, and report per source
  the main note, every changed note, the markers added and, when only one note changed,
  why; batch runs end with the table. Verify by reading against the report requirements.
- [x] 5.5 Add the `CHANGELOG.md` entries (`Changed`: the plan before writing and
  `--batch`; `Fixed`: the final source path for file sources). Verify `ALL PASS`.

## 6. `brain-qa`

- [x] 6.1 Rewrite steps 5 and 6: save substantive answers by default with the path stated;
  do not save one-line lookups, and say so; `--no-save` or a request in words writes
  nothing and says so; on a name collision, a new name; a basis section and a gaps
  section in the base's language, and `gaps:` in the frontmatter; both sides of a
  contradiction, each unresolved one listed as a gap; `LIMITS.md` before any claim of
  certainty; the compile and enhance offers unchanged. Update the skill `description` and
  `.claude/commands/b/qa.md` (mention `--no-save`). Verify by reading against the
  `answer-capture` spec, the Q&A requirement of `contradiction-markers`, and the
  certainty requirement of `method-limits`.
- [x] 6.2 Add the `CHANGELOG.md` entry (`Changed`: answers saved by default, with the
  `--no-save` note for non-interactive callers). Verify `ALL PASS`.

## 7. Other skills and the product page

- [x] 7.1 `brain-lint/SKILL.md`: stop below 10 notes using the scanner's `total`; one note
  and one next step per finding; a warnings section for `missing_source_file` (with the
  fix) and `contradiction`; the fix-first list in the order of the `lint-report` spec;
  the clean-report caveat and the `LIMITS.md` rule; the scripts section names the new
  classes. Update the `description`. Verify by reading against the `lint-report` spec.
- [x] 7.2 `brain-enhance` and `brain-compile`: mark contradictions and never overwrite;
  list markers in the report; enhance keeps a marker until the owner decides; raw-source
  citations go in `source:` or `sources:`. Verify by reading against the
  `contradiction-markers` spec.
- [x] 7.3 `brain-curate/SKILL.md`: read tool URLs from `source:` or `sources:`. Verify that
  the Phase 2 text names both fields.
- [x] 7.4 `README.md`: an "Acknowledgements" line crediting super-brain (MIT, link), and
  updated `/b:ingest`, `/b:qa` and `/b:lint` rows in the skills table. Verify that the
  links resolve.
- [x] 7.5 Add the `CHANGELOG.md` entries for 7.1 to 7.3. Verify `ALL PASS`.

## 8. Integration checks and review

- [x] 8.1 Finish the `[Unreleased]` entry: an "Existing bases" paragraph covering what
  `/b:upgrade` brings (skills, scripts, `LIMITS.md`, the workflow summary); what it does
  not bring (a rendered `AGENTS.md` unless unedited and re-rendered, `content/templates/`,
  `README.md`); the lint warnings for stale source paths, with fixes; `--batch` and
  `--no-save` for non-interactive runs; the credit to super-brain. Verify that
  `python dev/check_manifest.py` passes (no repeated section heading).
- [ ] 8.2 Run `python tests/run_tests.py` and `python tests/run_skill_tests.py`. Verify
  `ALL PASS` and exit 0, with every skip listed and explained.
- [ ] 8.3 Run the two workflow commands from the repo root (CONTRIBUTING step 4). Verify
  that `git diff content/_indexes` shows only `updated:` lines, then restore the indexes.
- [ ] 8.4 Walk through ingest in a scratch base: `git clone . ../kb-quality-test`,
  `/b:onboard` there with test answers, two inbox files (one contradicting the example
  note), then `/b:ingest`. Verify one message with the plan, notes with `sources:`
  pointing at existing `_raw/processed/` files, a `> [!contradiction]` marker, and a
  report that lists every changed note. Then run `/b:ingest --batch` on one file: the
  warning comes first and no question is asked.
- [ ] 8.5 In the same scratch base, verify the following. A substantive `/b:qa` is saved
  with a basis section, a gaps section and a matching `gaps:`. A one-line lookup is not
  saved, and the skill says so. `/b:qa --no-save` writes nothing. `/b:lint` below 10
  notes says it is too early. After notes are added to reach 10, the report has a
  warnings section, a fix-first list, and the caveat when it is clean. Delete the
  scratch base afterwards.
- [ ] 8.6 Push, mark the PR ready, run `/ss:review-loop <PR> add-quality-guards`, and get
  CI green on Linux and Windows. The merge is the maintainer's.
