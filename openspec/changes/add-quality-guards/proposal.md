# Proposal

## Why

The template is strong at scale (three indexes, a rebuild script), in its tested scripts
and in its update path. It is weak at the quality of what the agent writes into a base.
A comparison with `superhero-tech/super-brain` (MIT, read on 2026-10-19 at commit
`0922a1a`) made the gaps concrete:

- `brain-ingest` writes before it shows what it understood. The user is asked only about
  clusters.
- One source creates or merges one note, instead of adding to every note it is about.
- No rule says what to do when a new source contradicts what the base already says.
- Nothing checks that the source a note points to exists. In the maintainer's base, 58
  notes have a `source:` under `_raw/inbox/`, and 57 of those files are gone. Ingest moves
  the file to `_raw/processed/` in step 11 but corrects `source:` only for YouTube.
- `brain-qa` only offers to save, so good answers, and what the base could not answer,
  are lost.
- Nothing tells the agent or the owner where this method fails.

A mistake written once comes back in every later answer, and in a base of hundreds of
notes nobody finds it by reading. This change adds guards at the points where mistakes
enter: the ingest plan, the source path, the saved answer and the lint report.

## What Changes

- **Ingest shows a plan before it writes.** For each source: its claim in one sentence,
  the notes it will create, the notes it will add to, and what it contradicts. The plan
  and the cluster question form one message per run, so ingest still asks at most once.
  `--batch` skips the question, and says at the start that batch notes come out thinner
  because nobody corrects the reading.
- **One source updates every note it is about.** Ingest maps the source against the
  catalog and graph into a main note, existing notes to add to, and new notes. Each
  existing note gets what the source adds, the source reference and a two-way link to
  the main note. The final report lists every changed note, and says why when only one
  note changed.
- **Contradictions are marked, never overwritten.** A fixed Obsidian callout,
  `> [!contradiction]`, holds the old claim, the new claim and both sources. The rule
  lives in `brain-ingest`, `brain-enhance` and `brain-compile`. `brain-qa` presents both
  sides, and `lint_scan.py` lists the notes that carry a marker.
- **Sources can be checked.** Notes may list several sources in `sources:`, and a single
  `source:` stays valid. Ingest writes the final `_raw/processed/` path into the note for
  file sources, not only for YouTube. `lint_scan.py` reports `_raw/` paths that do not
  exist. When a copy of a missing `_raw/inbox/<name>` sits at `_raw/processed/*_<name>`,
  it gives the ready fix. In this release that report is a **warning**, not an error.
- **Q&A saves substantive answers by default.** `brain-qa` saves them to
  `content/_outputs/answers/` as an `answer-note` without asking, with a section on what
  the answer rests on and a section on gaps: what the base could not answer. The gap
  count goes in a `gaps:` frontmatter field. A one-line lookup is not saved, and the
  skill says so. `--no-save` (or asking not to save) turns saving off, and the skill
  confirms that too. `gaps.py` lists saved answers that have gaps.
- **A limits file and an honest lint.** A new root file, `LIMITS.md`, says where the
  method fails and what to do about each failure. `brain-qa` and `brain-lint` read it
  before claiming that the base is sure of anything. `brain-lint` stops below 10 notes,
  names the note and the next step for every finding, ends with a "fix first" list, and
  says that a clean report means tidy, not true.

Nothing here is **BREAKING**. Old notes with `source:` and without the new sections pass
lint as before. The release, `0.3.0`, is a separate step after the update pilot.

## Capabilities

### New Capabilities

- `ingest-plan`: the pre-write plan, how it merges with the cluster question, and batch
  mode.
- `ingest-coverage`: mapping one source to a main note, existing notes and new notes;
  adding to every affected note; the report of all changed notes.
- `contradiction-markers`: the callout format, which skills write it, how Q&A treats it
  and how lint lists it.
- `source-traceability`: `source:` and `sources:`, final archive paths written by
  ingest, and the lint warning for missing `_raw/` paths, with a suggested fix.
- `answer-capture`: saving answers by default, the basis and gap sections, the `gaps:`
  count, the opt-out, the unsaved one-line lookup and the gap listing in `gaps.py`.
- `method-limits`: the `LIMITS.md` file, its place in the manifest, and the skills that
  must read it.
- `lint-report`: the minimum vault size, findings that name a note and a next step, the
  "fix first" list, the clean-report caveat, and advisory classes that never block.

### Modified Capabilities

None. The existing specs cover releases, the manifest, the stamp, upgrade and adoption.
`LIMITS.md` joins the owned class through a manifest pattern, which no existing
requirement enumerates.

## Impact

- **Skills (owned, reach instances through `/b:upgrade`):** `brain-ingest`, `brain-qa`,
  `brain-lint`, `brain-enhance`, `brain-compile`, `brain-gaps` and `brain-curate`
  (`SKILL.md`). Scripts: `lint_scan.py` and `gaps.py`, with their unit tests.
- **New owned file:** `LIMITS.md`, added to the owned list in `.kb-manifest.json`.
- **Also owned:** `.github/workflows/kb-maintain.yml` (the summary lists warnings apart
  from issues), `tests/run_tests.py` and `CHANGELOG.md`.
- **Rendered:** `AGENTS.template.md` gets short pointers and `sources:` in its
  frontmatter example. It reaches only instances whose `AGENTS.md` is unedited.
- **Seeded:** `README.md` credits super-brain. Note templates in `content/templates/`
  are not changed.
- **Unchanged:** `schema.yml`, `.githooks/pre-commit` and `build_indexes.py`.
- **Dependencies:** none new.
- **Instances:** nothing until their owner upgrades. After the upgrade, lint warns about
  old `_raw/inbox/` source paths and proposes a fix. Fixing them in the maintainer's base
  is PL-483.
