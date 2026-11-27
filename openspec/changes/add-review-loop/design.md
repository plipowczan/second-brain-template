# Design

## Context

See `proposal.md` for the why. The ideas come from `undefined-ui/second-brain-os` (MIT).
Their files assume another layout (`raw/`, `wiki/`, `index.md`, `log.md`) and no update
mechanism, so nothing is copied: the text and code here are our own, and `CHANGELOG.md`
names the inspiration, as `0.3.0` did for super-brain.

Facts this design rests on, checked on 2026-11-27:

- `build_indexes.py`, `lint_scan.py` and `lint_links.py` skip `content/_outputs/` and
  every file whose name starts with `_`; a file in either place, with wikilinks and no
  frontmatter, produced no finding and no index entry in a scratch vault. The optional
  pre-commit hook blocks only on `lint_scan.py` findings, so it does not see them either.
- `/b:export --public` excludes `_outputs/` and every underscore-prefixed file.
- The maintainer's own published base (Quartz) ignores `_raw`, `_indexes`, `_outputs`,
  `_graveyard` and `_privacy.local.md`, but not other underscore files: a
  `content/_log.md` would be published there.
- `content/` is seeded once. A file the template adds under `content/` never reaches an
  existing base, so every new file in `content/` is created by the skill that first needs
  it. Rules live in skills, not only in the rendered `AGENTS.md`, because an edited
  `AGENTS.md` is never rewritten (the lesson of `PL-549`).
- `/b:ingest --batch` already exists and means "no person present, skip the plan". Point 5
  needs another name.
- `lint_links.py` counts orphans by file name, counts a self-link as incoming, and
  ignores links in code. A count from `graph.md` differs: on the maintainer's base (487
  notes) 35 orphans by `lint_links.py`, 37 from `graph.md`. Notes with no link at all
  have no line in `graph.md`, only the `nodes:` total.
- Every description of a skill and of a command enters every session. Today the template
  has 21 skills and 20 commands.

Metrics measured on the maintainer's base (487 notes, about six months old), to set the
thresholds (design D6): orphans 7.2 % by `lint_links.py` (7.6 % from `graph.md`),
isolated notes (no link in or out) 3.7 %, 7.25 links out per note (median 6), one island
of 6 notes besides the main component and 18 isolated notes, untouched for 90 days
27 % (last of `date`, `agent-reviewed` and the last git commit) or 52 % (frontmatter
only).

## Goals / Non-Goals

**Goals:**
- After a week of use, the owner can see what the base gained, where it is thin, what to
  do next, and how well they know their own notes, without writing a question first.
- The record of what the agent did survives without git.
- Existing bases get all of it through `/b:upgrade`, with no manual step.
- At most three new skills (decided 2026-11-04); this design uses two.
- The five pilot findings stop surprising the owner of a base that upgrades.

**Non-Goals:**
- Typed links (`supports`, `contradicts`, …), a "changed my mind" history, importing
  chat exports: later, as decided on 2026-11-04.
- Spaced repetition or a schedule for `/b:learn`.
- Metrics in the weekly `kb-maintain` workflow (a snapshot without the owner's review is
  numbers nobody reads; it can come once a base has a history to show).
- A selection pass over a whole backlog before the first batch (see D9).
- Archiving `add-quality-guards` (its own follow-up; it would pull seven capabilities
  into this pull request).

## Decisions

### D1. The log is `content/_outputs/log.md`, written by one script

The comparison suggested `content/_log.md`. `content/_outputs/` is better: Quartz setups
taught in the course ignore it while they publish other underscore files, export and
lint already skip it, and the folder already holds what the agent produces (answers,
reports). The file is a Markdown table so it reads in Obsidian:

```
| When (UTC) | Operation | What | Notes |
|---|---|---|---|
| 2026-11-27 14:03 | ingest | 3 sources; 2 created, 5 updated | `AI/Agents`, `AI/Tools/Foo`, … |
```

`brain-reindex/scripts/oplog.py append --op <name> [--count key=N]... [--note <path>]...`
writes one row. It creates the file with its header when it is missing, builds "What"
from the counts (no free text), lists note paths as code spans (at most 10, then "and N
more"), escapes `|`, and appends with an LF line ending in one write. It never rewrites
or reorders the file. It lives next to `build_indexes.py` because every skill that
writes notes already ends by refreshing the indexes, so the dependency exists.

Alternatives: the agent appends the row itself (rejected: the format drifts between
models and runs, and the review parses it); one row per note (rejected: an ingest of ten
sources would write fifty rows); wikilinks in the Notes column (rejected: the log would
become a hub in Obsidian's graph and backlinks, and `/b:refactor` would rewrite history
when it repairs links on a rename).

### D2. Who writes the log, and what a row may contain

A row is written by every skill that writes or moves notes: `brain-ingest`,
`brain-compile`, `brain-enhance`, `brain-curate` (retire, merge), `brain-refactor`,
`brain-import`, `brain-watch` (apply). The two new skills write one row each
(`review`, `learn`). `brain-qa` and `brain-lint` do not: their dated outputs in
`_outputs/answers/` and `_outputs/reports/` already are the record, and the review reads
them there. `brain-upgrade` does not: its engine never writes under `content/`, and the
commit and the stamp record it.

A row holds only counts, the operation name and paths of notes and archived sources,
that is, names already committed in the base. No quotes from sources, no question text,
no summary in words, so the row cannot carry a private term the base does not already
hold as a file name. The log is committed like the notes; `/b:export --public` leaves it
out.

A skill whose `SKILL.md` the owner edited and kept at upgrade writes no rows, and a base
fresh from an upgrade has an empty log. The review never treats a missing row as "nothing
happened": it also reads the dated outputs and the git history when there is one (D5).

`.gitattributes` gains `content/_outputs/log.md merge=union` and the same for
`content/_outputs/metrics.md`, so two clones or worktrees that both appended rows merge
without a conflict. The union driver is built into git and needs no configuration.

### D3. Two new skills, not three

`brain-review` (`/b:review`) and `brain-learn` (`/b:learn`). The metrics are a script
the review runs, not a skill: numbers without a reading of them tell the owner little,
and a third description in every session is a cost paid daily for a command run weekly.
The comparison planned three (review, metrics, learning); the limit stays three, so a
`/b:metrics` command can come later without breaking it.

Alternative: `/b:metrics` as a third skill. Rejected for now, see above. Paweł decides
(question 1 of the plan).

### D4. Metrics: one definition, shared with lint

`brain-lint/scripts/metrics.py` computes, from the notes themselves:

| Metric | Definition |
|---|---|
| `notes` | notes as `lint_links.py` counts them |
| `orphans` | notes no other note links to, exactly as `lint_links.py` reports them |
| `isolated` | notes with no link in or out |
| `links_per_note` | resolved links out, divided by `notes` |
| `islands` | connected groups of 2 or more notes besides the largest one |
| `untouched_90d` | notes whose last touch is 90 or more days ago |

`lint_links.py` becomes importable (its walk and resolution move into functions; run as a
script it prints exactly what it prints today, which its tests pin), and `metrics.py`
imports it from the same folder. So `/b:lint` and `/b:review` can never report two
different orphan counts. Reading the notes instead of `graph.md` also means the metrics
do not depend on a fresh reindex, and isolated notes are counted by name.

"Last touch" is what `brain-curate` already uses: the latest of `date`, `agent-reviewed`
and, in a git base, the file's last commit (one `git log` call for the whole vault). Each
snapshot records its basis (`git` or `frontmatter`); a comparison across bases says the
two are not comparable instead of showing a jump.

`metrics.py --record` adds one row to `content/_outputs/metrics.md` (a Markdown table,
created on first use) and prints the snapshot, the previous snapshot of an earlier day
and the difference as JSON. A second record on the same day replaces that day's row, so
running the review twice does not skew the trend. Without `--record` it writes nothing.

### D5. The review: inputs, period, output

`brain-review/scripts/review_data.py --since <date>` gathers the data in one JSON, so the
agent reasons over facts instead of searching:

- log rows in the period, grouped by operation, and the folders the touched notes are in;
- files in `_outputs/answers/` and `_outputs/learning/` dated in the period, with their
  `gaps:` counts;
- notes created or changed in the period from git (`git log --since`) when the base has
  git, so a period with no log rows still shows what changed;
- sources waiting in `_raw/inbox/`;
- open contradictions (`lint_scan.py`), weakly connected notes and unanswered questions
  (`gaps.py`), and the metrics with `--record` (`metrics.py`), each run as a subprocess
  with the interpreter that runs the script.

The period starts at the last `review` row of the log, else the date of the newest
`*_review.md` report, else 7 days ago; `--since YYYY-MM-DD` or `--days N` override it.

The report goes to `content/_outputs/reports/YYYY-MM-DD_review.md`, in the vault
language, in a fixed shape: What came in · Where attention went · Open contradictions ·
Thin places · Questions the base could not answer · Metrics (table: now, before,
change) · Three moves. Each move is one command with its target (`/b:enhance
[[Note]]`, "resolve the contradiction in [[Note]]", `/b:ingest --backlog`), chosen in
this order: an open contradiction, an unanswered question, an orphan or thin note in a
folder the owner worked in this period, a waiting inbox, an untouched note. The review
writes no note. Below 10 notes it says the base is too young for a review, as
`/b:lint` does, and stops. It runs without a person present (it asks nothing), so it can
be scheduled.

### D6. No pass or fail thresholds

`second-brain-os` calls a base healthy below 5 % orphans. The maintainer's base, which is
linked by every ingest since `0.3.0`, has 7.2 %; a 5 % line would mark it unhealthy on
every review and teach the owner to skip the line. Absolute targets also depend on the
kind of base: a recipe collection links less than a research base. So the review shows
the value, the previous value and the change, and calls out a metric only when it got
worse since the previous snapshot by at least: orphans +2 percentage points, isolated
+2 points, islands +1, links per note −0.5, untouched +5 points. The steps are about a
third of the maintainer's current levels, enough to ignore the noise of one ingest.
Below 30 notes no metric is called out at all.

Alternative: their 5 % orphan threshold. Rejected, see above. Paweł decides (question 2).

### D7. `/b:learn`: quiz and explain-back in one skill and one command

`/b:learn <topic or [[Note]]>` runs a Feynman session: the agent finds the notes (as
`brain-qa` does: the catalog first), explains the subject in plain words in at most a
short paragraph, asks the owner to explain it back in their own words, then compares the
owner's explanation with the notes. Every gap is one of three kinds: **the base lacks it**
(no note covers it; the agent says what is missing), **its sources lack it** (the note
claims it, but the archived source the note cites does not support it; the agent reads
only the sources that note cites), **you missed it** (the notes have it and the owner did
not say it). `/b:learn --quiz <topic> [N]` asks N questions (5 by default) one at a time,
mixing recall, why and application, grades each answer against the note it came from
with the note named, and ends with the score and the notes to revisit.

Both save the session to `content/_outputs/learning/YYYY-MM-DD_<topic>.md` (topic, mode,
notes used, the owner's explanation or answers, the gaps by kind, the score) and write
one log row. They change no note: filing a gap back is offered as `/b:enhance` or
`/b:ingest`, as `brain-qa` offers it. Without a person present the skill stops: it has no
one to ask.

Alternative: two commands, `/b:quiz` and `/b:explain`. Rejected: one more description in
every session for a split the owner does not need to remember; `--quiz` is enough.
Paweł decides (question 3).

### D8. `/b:ingest --backlog [N]`

`--backlog` takes the N oldest sources in `content/_raw/inbox/` (N is 10 when omitted),
builds the normal plan for those only, writes them after the reply, refreshes the
indexes, writes a log row, and stops with "N ingested, M still in the inbox. Run
`/b:ingest --backlog` again for the next batch." Oldest means, in order: a
`YYYY-MM-DD` date in the file name, the frontmatter `date:`, the file's modification
time; ties go by name. Ingest already moves every processed file to `_raw/processed/`,
so the inbox is the checkpoint: there is no state file, a stopped run loses nothing, and
it works without git. YouTube URLs given as arguments count towards N.

`--backlog` combines with `--batch` (no person present: no plan question, the same N per
run). `--batch` alone keeps its meaning and takes the whole inbox, so scripts that rely
on it are unchanged.

Without either flag, when the inbox holds more than 10 sources, interactive ingest
behaves as `--backlog 10` and says so in its plan message: one plan over dozens of
sources is too long to correct, and reading them all in one context is where the reading
gets shallow. Ingest still asks once per run. Paweł decides (question 4).

### D9. Skips instead of a selection pass

In a backlog the plan may propose to skip a source: empty, unreadable, or the same
content as a file already in `_raw/processed/` (same hash). On the owner's OK a skipped
file moves to `content/_raw/skipped/`, so the next batch does not offer it again; the
owner can move it back. Batch mode skips nothing. A separate pass that lists the whole
backlog for selection before the first batch is left out: on names and first lines it is
shallow, on full reading it is the cost the batches exist to split.

### D10. The skill description pattern

`CONTRIBUTING.md` gets the pattern; new and edited skills follow it:

- The description, single-quoted in YAML: "Use when" with the trigger phrases, one
  sentence on what the skill does and what it writes, and "Do NOT use for …" naming the
  neighbouring skill, only where two skills overlap (review / lint / gaps, learn / qa,
  `--backlog` / `--batch`).
- In the body, a `## Calibration` section: the typical way this skill goes wrong and what
  right looks like, in two to four lines. And a fixed output shape (the report or
  message the skill ends with).

`dev/build_codex_files.py --check` already fails on a description YAML would cut; it also
fails on one over 500 characters (the longest today has 454), so descriptions cannot
grow without notice. The pattern is applied to the two new skills and to every skill this
change edits; the others follow it when they are next edited.

### D11. Upgrade fixes from the pilot (bugs 7–11)

- **Bug 7, `.kb-onboard.json` still ignored.** When the commit is going to track
  `.kb-onboard.json` and `git check-ignore` says the base ignores it, the plan says so and
  names the line. The engine does not edit `.gitignore`: a file the owner edited is never
  written. The skill offers to delete that one line after the upgrade commit, in a commit
  of its own, on the owner's yes.
- **Bug 8, folders left in the temp directory.** The plan records the temporary folders
  the engine created for it (the download, the plan and its payload). `commit` deletes
  them after a successful commit, and `apply` does so in a base without git, where no
  commit follows. `fetch` prints the folders it created; the skill's last step passes
  them to a new `cleanup --path <folder>...`, which deletes a folder only when it is a
  direct child of the temp directory and its name starts with `kb-upgrade-`. Nothing is
  deleted by pattern, so a parallel upgrade in another base keeps its folders. A failed
  step leaves its folders for diagnosis, and `cleanup` names them. The tests create every
  folder under a `TemporaryDirectory` or delete it in `tearDown`.
- **Bug 9, the backup without git.** `apply` without git always creates the backup
  folder and writes `backup.json` in it: the versions, the files replaced and deleted
  (copied there, as today) and the files added, each with the hash apply wrote. A new
  `undo --backup <folder>` puts back every copy, deletes every added file whose content
  still equals what apply wrote, keeps and names any other, and restores the stamp, in
  one transaction like `apply`. Adoption names the backup folder only when it exists, and
  now it always does.
- **Bug 10, a local path in the commit message.** For a zip, a folder or a git clone the
  commit body names the source by its last path component (`Source: zip
  second-brain-template-v0.5.0.zip (<commit>)`). A download keeps its URL. The plan file
  in the temp directory keeps the full path.
- **Bug 11, the owner's note type.** `lint_scan.py` accepts, in addition to the keys of
  `schema.yml`, the types listed in `NOTE_TYPES` of `.kb-onboard.json`, without required
  fields. Writing them into `schema.yml` at onboarding was the alternative; rejected,
  because `schema.yml` is an owned file and an edit there turns every later template
  change to it into a conflict at upgrade. A type the owner wants fields enforced for
  still goes into `schema.yml` by hand, and `/b:lint` says so for a `bad_type` finding.

### D12. Version and delivery

`0.5.0`: new commands are a minor release, as `/b:watch` was in `0.4.0`. It also ships
the `[Unreleased]` entry of PR #25 (`/b:qa` reads less). Nothing is breaking: every new
behaviour starts on first use, and the one changed default (D8, interactive ingest of
more than 10 sources) only splits a run.

Existing bases get the skills, commands, scripts, Codex stubs and `.gitattributes`
through `/b:upgrade`. An untouched `AGENTS.md` is re-rendered with the three new folder
rows (`_outputs/log.md`, `_outputs/metrics.md`, `_outputs/learning/`); an edited one
misses nothing, because every rule is in the skills. A skill the owner edited and kept
does not write log rows; the `CHANGELOG.md` entry says so.

## Risks / Trade-offs

- **Two sessions append at the same moment.** One short write with append mode is not
  interleaved on a local disk; a sync client (OneDrive) may still produce a conflicted
  copy. Accepted: the loss is one row, and the review does not depend on the log alone.
- **The log grows.** About one row per operation, a few thousand rows a year at heavy use:
  under a megabyte. `review_data.py` reads it as a stream. No rotation for now.
- **Interactive ingest of more than 10 sources changes.** An owner used to one big run
  now needs several. Mitigated by saying so in the plan message, by `--backlog N` for
  another size, and by the changelog.
- **`undo` deletes files.** Only files whose content still equals what apply wrote, and
  only those `backup.json` lists as added; everything else is kept and named.
- **Context cost.** Two skills and two commands add about 900 characters to every
  session; the "Do NOT use for" sentences add about 60 each to seven descriptions.
- **Description edits reach owners who edited a skill as a conflict at upgrade.** The
  plan already asks keep, overwrite or merge; the changelog names the edited skills.

## Migration Plan

Nothing to migrate. Each new file is created by the first skill that needs it. The
course (cheat sheet rows for `/b:review`, `/b:learn` and `--backlog`, a paragraph in
lessons 4 and 5) is updated outside this repository from the text in the final report.
Before the tag, the release is tried on a fresh copy of the maintainer's base in a
temporary folder.

## Open Questions

For Paweł, each with a recommendation in the plan: metrics inside the review or as a
third skill (D3); trend only or their 5 % threshold (D6); one `/b:learn` or two commands
(D7); interactive ingest of more than 10 sources switches to batches by itself or only
suggests it (D8).
