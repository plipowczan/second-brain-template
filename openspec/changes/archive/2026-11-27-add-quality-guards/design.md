# Design

## Context

See `proposal.md` for the reasons. The scope, and decisions D1 to D4 below, come from the
maintainer's brief for PL-549 (2026-10-19). The maintainer accepted this design on
2026-10-20, confirming D4 (`Changed`, not BREAKING), the separate warnings in the
`kb-maintain` summary (D8), the credit in `README.md` and `CHANGELOG.md` (D11), and
clusters as separate notes in batch mode (D5). Facts checked on 2026-10-19 that shape the
approach:

- **How a change reaches a base.** `.kb-manifest.json` sorts files into classes.
  `/b:upgrade` keeps owned files current with a three-way comparison. It re-renders
  `AGENTS.md` only on request and only while the file is unedited. It never writes
  `content/` or `README.md`. The maintainer's base (417 notes) has an edited `AGENTS.md`.
- **Note templates.** `content/templates/*.md` carry no source field at all. The skill
  fills the frontmatter. `AGENTS.template.md` shows `source: "_raw/inbox/filename.md"` in
  its frontmatter example, and that example is where the stale inbox paths come from.
- **Ingest.** Phase 1 asks only about clusters. Phase 2 checks overlap with one note
  (step 7), moves the file (step 11), and checks `source:` against the archive only for
  YouTube.
- **Scanner.** `lint_scan.py` always exits 0 and prints JSON with `total`, `issues`
  (lists of `"<path> (<detail>)"` strings) and `counts`. It has no severity. Its frontmatter
  parser reads scalars and block lists. A flow list (`["a", "b"]`) stays a raw string.
  `content/_outputs/` is excluded, so answer notes are never linted.
- **Scanner consumers.** `.githooks/pre-commit` blocks only on `missing_frontmatter` and
  `schema_violation`. The `kb-maintain` workflow prints every non-zero count under
  "Issues". `tests/run_tests.py` checks two counts.
- **Other readers of `source:`.** `brain-curate` reads the source URL of tool notes. No
  script reads `source:`.
- **`gaps.py`** reads only `graph.md` and has no frontmatter parser.
- **Headless use.** In the maintainer's control repository, a `brain-query` skill runs
  `claude -p` against a base for read-only questions.

## Goals / Non-Goals

**Goals:**

- Every rule takes effect in existing bases after one `/b:upgrade`, without the owner
  editing `AGENTS.md`, `content/templates/` or `schema.yml`.
- No note that passes lint today starts failing.
- What can be checked by a script is checked by a script with unit tests: missing
  sources, contradiction markers, answer gaps. The rest is skill instructions.

**Non-Goals:**

- Fixing the stale paths in any base. The scanner proposes fixes; applying them in the
  maintainer's base is PL-483.
- Behavioural tests of the skills (a later package), a trust field, an operation log,
  answer formats, per-claim citations.
- Executable migrations. Nothing needs migrating.

## Decisions

### D1. Every rule lives in a skill *(brief decision 1)*

What reaches an existing base after `/b:upgrade`:

| Part of this change | Class | Reaches existing bases |
|---|---|---|
| `SKILL.md` files, `lint_scan.py`, `gaps.py`, tests | owned | yes |
| `LIMITS.md`, `.kb-manifest.json`, `kb-maintain.yml`, `CHANGELOG.md` | owned | yes; a file the owner edited is kept, and the owner is asked only when the template changed it too |
| `AGENTS.md` (from `AGENTS.template.md`) | rendered | only when unedited and the owner asks for a re-render; not in the maintainer's base |
| `content/templates/`, `README.md` | seeded | never |

So each rule is written in full in the skill that applies it: the plan, coverage and
final paths in `brain-ingest`; the marker rule in `brain-ingest`, `brain-enhance` and
`brain-compile`; saving in `brain-qa`; the report rules in `brain-lint`. The skills
name `sources:` and the marker format themselves, because an old base has neither in
its `AGENTS.md` or its templates. `AGENTS.template.md` gets two short changes for new
bases. Its frontmatter example shows `sources:` with a `_raw/processed/` path instead of
an inbox path, and one line points to `LIMITS.md`.

*Rejected:*

- **Rules in `AGENTS.template.md`.** They would never reach a base with an edited
  `AGENTS.md`, such as the maintainer's.
- **A `sources:` field in the note templates.** It never reaches existing bases, and
  the templates carry no source field today, so the skill already fills it.

### D2. `LIMITS.md` in the repository root, owned *(brief decision 2)*

`LIMITS.md` goes in the root, next to `ENVIRONMENTS.md`, the existing owned document. It
is added to the owned list in `.kb-manifest.json`. `brain-qa`, `brain-lint` and
`AGENTS.template.md` point to it. It is written in English like the other owned
documents. An owner may edit it: the three-way upgrade keeps local edits.

*Rejected:*

- **`content/`.** Seeded: it would reach new clones only, never existing bases. A note in
  `content/` would also be indexed and linted.
- **`.claude/skills/<skill>/references/`.** It would reach existing bases, but it belongs
  to two skills and to the owner. Inside one skill's folder the owner would not find it,
  and the "nothing tells the owner" problem would remain.
- **`README.md`.** Seeded, and it is the template's product page.

Trade-off: the root is outside the Obsidian vault (`content/`), so the file does not
show in Obsidian. The lint report's clean-result caveat and the Q&A certainty rule both
name the file, so the owner meets it where it matters.

### D3. Backward compatibility *(brief decision 3)*

- **`schema.yml` does not change.** It declares only required fields. `sources` and
  `gaps` are optional, so nothing needs declaring. A comment-only edit would still make
  every base that edited `schema.yml` answer an upgrade question, and its header invites
  owners to edit it.
- **The scanner only adds.** New classes join `issues` and `counts` like the others. A
  new top-level `warnings` list names the warning classes (D8). No existing key, string
  format or exit code changes.
- **`source:` stays valid** everywhere (spec `source-traceability`). Skills convert to
  `sources:` only when they add a second source to a note.
- **New sections are never required.** Answer notes live in `content/_outputs/`, which
  the scanner excludes. `gaps.py` skips answers without `gaps:`.
- **The pre-commit hook does not change.** It keeps blocking only on
  `missing_frontmatter` and `schema_violation`.

### D4. Version `0.3.0`, nothing BREAKING *(brief decision 4)*

The change adds behaviour and breaks no file format, field or script contract. Two
behaviour changes need calling out under `Changed` in `CHANGELOG.md`, with what to do:

- `/b:ingest` without `--batch` now stops at the plan. An automated or non-interactive
  run therefore writes nothing until someone answers. Add `--batch` to such runs.
- `/b:qa` now writes answer files by default. Non-interactive callers that must stay
  read-only pass `--no-save`.

Neither is marked **BREAKING**. Both affect only runs without a person present, which the
template does not document, and in both cases the old behaviour is one flag away. The
release itself (manifest version, history index, tag) is not part of this change.

### D5. One message per run, and `--batch`

Phase 1 now reads each source in full and builds the coverage map (D6), which today
happens in Phase 2. Overlap checks and contradiction checks move earlier. The run sends
one message: the cluster options, if there are clusters, followed by one block per source
of three or four lines (claim, create, add to, contradicts). Phase 2 writes without
further questions.

`--batch` is the explicit trigger because ingest already parses its arguments: every
non-URL argument aborts today, and the flag gets one exception. The request can also be
made in words ("ingest without review"). A batch run warns first, still builds the map,
resolves clusters as separate notes (option A, the documented default) and ends with a
per-source table.

*Rejected:*

- **One question per source.** It breaks the "ask at most once" property.
- **Asking only when there is a contradiction.** The most common error is the reading
  itself, and only the plan shows it.
- **Automatic batch mode above N files.** Thin notes would arrive by surprise.

### D6. Coverage map with three groups and no quota

The map has one main note, existing notes to add to, and new notes. It comes from the
catalog, the graph and the notes those point to. A mere mention gets a link, not an
addition. There is no minimum number of notes per source. A quota would push the agent
to invent additions. When a source changed one note, the report says why. Each addition
carries the source in the note's source fields, plus a link to the main note and back,
so the extra edits remain traceable.

### D7. The contradiction marker is an Obsidian callout

```markdown
> [!contradiction] Monthly price
> Earlier: 10 USD a month (source: _raw/processed/2026-03-01_pricing.md)
> New: 20 USD a month (source: _raw/processed/2026-10-20_changelog.md)
```

The type token `contradiction` is fixed and English. The title and labels follow the
base's language. Obsidian renders unknown callout types with the default style, so no
CSS or plugin is needed. The scanner matches `^\s*>\s*\[!contradiction\]` without regard
to letter case, outside fenced code blocks. It reports `"<path> (<n> markers)"` in a new
`contradiction` class.

*Rejected:*

- **A frontmatter flag.** It is far from the claim and cannot hold both sides.
- **A plain-text `CONTRADICTION:` line.** It mixes English into notes in other languages
  and does not render.
- **A `#contradiction` tag.** It pollutes the tag cloud and holds no structure.

### D8. Source checks and the warning list

- **Reading.** The scanner collects values from `source` and `sources`, whether written
  as a scalar, a block list or a flow list, on one line or several. A small flow-list
  reader is added: the current parser keeps `["a", "b"]` as a raw string. It strips quotes. Only values that
  start with `_raw/` or `content/_raw/` are checked, against the content root. URLs
  (`scheme://`), wikilinks and free text are skipped.
- **Fix.** For `_raw/inbox/<name>`, it globs `_raw/processed/*_<name>` (top level, where
  ingest archives), and also `*_<stem>-<n>.<ext>`, the name ingest gives an archive whose
  name is taken, so a second copy never leaves the first looking unique. One match gives
  `fix=<path>`. Several give `candidates=<a>|<b>`. None
  gives the plain finding. Class `missing_source_file`, strings such as
  `"content/T/X.md (source=_raw/inbox/talk.md, fix=_raw/processed/2026-07-02_talk.md)"`,
  one string per missing path.
- **Severity.** The output gets `"warnings": ["missing_source_file", "contradiction"]`.
  The `brain-lint` report lists these classes under warnings. The `kb-maintain` summary
  prints them under a separate "Warnings" heading. The pre-commit hook is untouched
  (D3). An exit code was rejected because the scanner always exits 0 and every consumer
  reads the JSON. Making the class an error was rejected: the maintainer's base would
  turn red on 57 notes after one upgrade.
- **Ingest.** Ingest chooses the archive name (`YYYY-MM-DD_<name>`, made unique if taken)
  before it writes notes, writes that path, moves the file, and checks in Phase 3 that
  every `_raw/` path it wrote exists. YouTube keeps its existing check.
- **Other readers.** `brain-curate` reads tool URLs from `source:` or `sources:`.

### D9. Answers are saved by default, with an opt-out *(maintainer, 2026-10-19)*

- Substantive answers are saved without asking. One-line lookups (a single fact or a yes
  or no from one note, in one or two sentences) are not, and the skill says so.
- **Opt-out.** `--no-save`, or the request in words, writes nothing and says so. The
  maintainer chose this on 2026-10-19 over "always save", so the read-only `brain-query`
  calls from the control repository do not pile files into the base. Teaching
  `brain-query` to pass the flag is a follow-up in that repository.
- **Structure.** The section headings (basis, gaps) are in the base's language. The gap
  count goes in `gaps: <int>`, so scripts never depend on the language. A colliding
  filename gets a `-2`, `-3` suffix.
- **`gaps.py`.** It gains `--answers` (default `content/_outputs/answers`). It reads only
  the frontmatter of each answer with a regex for `title`, `date` and `gaps`, and adds
  `answer_gaps: [{path, title, date, gaps}]`, newest first, to its JSON. The existing
  keys are unchanged. A missing folder yields `[]`, which costs about 30 lines plus
  tests. `brain-gaps` adds these answers to its to-build list.

*Rejected:*

- **Gap texts as a frontmatter list.** They would duplicate the body section and drift
  from it.
- **Fixed English headings.** They break the base's language rule.
- **Asking before saving.** That is today's behaviour, under which the answers are lost.

### D10. The honest-lint rules live in the skill, the threshold included

The threshold of 10 notes is applied by `brain-lint`, using the scanner's `total`. The
scanner, the pre-commit hook, CI and the two-note test vault keep working at any size.
The report rules (note and next step, a fix-first list ordered by what a fix unblocks,
and the clean-result caveat that points to `LIMITS.md`) are instructions in the skill's
report template.

### D11. Credit in `README.md` and `CHANGELOG.md`, no `CREDITS.md`

The text is our own: we read super-brain and copied nothing, so MIT imposes no notice.
The credit is a courtesy. A short "Acknowledgements" line in `README.md` (seeded) reaches
the product page and new clones. A mention in the `CHANGELOG.md` entry (owned) reaches
every base that upgrades, during the upgrade itself.

*Rejected:* a `CREDITS.md`. That is one more owned root file, and so one more upgrade
question for every base, for a single line.

## Risks / Trade-offs

- **[The plan adds friction, so owners may reach for `--batch` and get thinner notes]** →
  The plan is three or four lines per source in one message, and batch mode states its
  cost each time.
- **[Non-interactive runs change: ingest waits, Q&A writes]** → `CHANGELOG.md` names both
  under `Changed`, with `--batch` and `--no-save`. A follow-up updates `brain-query`.
- **[Coverage edits more notes per source: bigger diffs, more tokens, an error can spread
  further]** → The plan lists every note before anything is written, each addition names
  its source, and `LIMITS.md` covers cost and compounding.
- **[Markers pile up unresolved]** → Lint lists them every run, and the fix-first list
  includes them.
- **[A single `*_<name>` match can still be a different file with the same name]** → The
  scanner proposes a fix and never applies one. The owner or agent checks it (PL-483 for
  the maintainer's base).
- **[The saved-answer folder grows]** → One-line lookups are not saved, and `--no-save`
  exists. Curating answers is out of scope.
- **[Skill instructions are not covered by unit tests]** → Script behaviour is
  unit-tested. Skill behaviour is walked through by hand in a scratch clone (tasks 8.4,
  8.5). Behavioural tests are a later package.
- **[The maintainer's base shares skills with this template by hand-port until it
  adopts]** → It receives this change through the upgrade pilot (PL-481), or by the
  documented hand-port, template → `brain`, if the pilot slips.

## Migration Plan

Nothing to migrate. After `/b:upgrade` to the release that contains this change, a base
runs `/b:lint`. It gets warnings for stale `_raw/` source paths, with fixes where a
single archived copy exists, and fixes them when convenient. Rollback means reverting the
single upgrade commit, or restoring from `.kb-upgrade-backup/` without git.

## Open Questions

- Should `missing_source_file` become an error in a later release, once bases have
  cleaned their paths? This does not affect this change. It can be decided after the
  pilot.
