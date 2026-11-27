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
- `/b:export --public` excludes `_outputs/` and every underscore-prefixed path.
- The maintainer's own published base (Quartz) ignores `_raw`, `_indexes`, `_outputs`,
  `_graveyard` and `_privacy.local.md`, but not other underscore files: a
  `content/_log.md` would be published there.
- `content/` is seeded once. A file the template adds under `content/` never reaches an
  existing base, so every new file in `content/` is created by the skill that first needs
  it. Rules live in skills, not only in the rendered `AGENTS.md`, because an edited
  `AGENTS.md` is never rewritten (the lesson of `PL-549`). `README.md` is seeded too: its
  command table reaches new bases only.
- `vault-map.md` already has a `## Recent Changes` section: a hand-kept list of recent
  changes that ingest, import, watch and the `AGENTS.md` "On create" / "On edit" rules
  prepend to, that `build_indexes.py` preserves, and that the session-start hook loads
  into every session. It is short and it is rewritten; it is not a history.
- `/b:ingest --batch` already exists and means "no person present, skip the plan". Point 5
  needs another name. `add-quality-guards/specs/ingest-plan` says that any argument other
  than `--batch` or a YouTube URL aborts the call.
- `lint_links.py` is module-level code: it counts orphans by file name, counts a
  self-link as incoming, ignores links in code, and keeps only a set of linked names and
  an out-count per name, not the edges. Its test file has one test. A count from
  `graph.md` differs: on the maintainer's base (486 notes as `lint_links.py` counts
  them) 35 orphans by `lint_links.py`, 37 from `graph.md`. Notes with no link at all have no line in `graph.md`, only the
  `nodes:` total, and `gaps.py` reads `graph.md`.
- On the upgrade to the release that carries this change, the base's old engine runs
  `fetch` and the base's old `brain-upgrade/SKILL.md` drives the steps. Only `plan`,
  `apply` and `commit` run the new engine. Anything new in the skill or in `fetch` starts
  with the upgrade after that.
- Every description of a skill and of a command enters every session. Today the template
  has 21 skills and 20 commands.

Metrics measured on the maintainer's base (486 notes, about six months old), to set the
call-out rules (D6): orphans 7.2 % by `lint_links.py`, isolated notes (no link in or out)
3.7 %, 7.25 links out per note (median 6, counted from `graph.md`), one island of 6 notes
besides the main component and 18 isolated notes, untouched for 90 days 27 % (latest of
`date`, `agent-reviewed` and the last git commit) or 52 % (frontmatter only).

## Goals / Non-Goals

**Goals:**
- After a week of use, the owner can see what the base gained, where it is thin, what to
  do next, and how well they know their own notes, without writing a question first.
- The record of what the agent did survives without git.
- Existing bases get all of it through `/b:upgrade`, with no manual step beyond the one
  the changelog names for the first upgrade (D11).
- At most three new skills (decided 2026-11-04); this design uses two.
- The five pilot findings stop surprising the owner of a base that upgrades.

**Non-Goals:**
- Typed links, a "changed my mind" history, importing chat exports: later, as decided on
  2026-11-04.
- Spaced repetition or a schedule for `/b:learn`.
- Metrics in the weekly `kb-maintain` workflow.
- A selection pass over a whole backlog before the first batch (D9).
- Archiving `add-quality-guards` (a follow-up, see "Archive order").
- Replacing `## Recent Changes` (D2).

## Decisions

### D1. The log is `content/_outputs/log.md`, written by one script

The comparison suggested `content/_log.md`. `content/_outputs/` is better: the Quartz
setup above ignores it while it publishes other underscore files, export and lint already
skip it, and the folder already holds what the agent produces (answers, reports). The
file is a Markdown table so it reads in Obsidian:

```
| When (UTC) | Operation | What | Notes |
|---|---|---|---|
| 2026-11-27 14:03 | ingest | sources=3 created=2 updated=5 | `AI/Agents`, `AI/Tools/Foo`, … |
```

`brain-reindex/scripts/oplog.py append --op <name> [--count key=N]... [--note <path>]...`
writes one row:

- It creates the file with its header when it is missing, and otherwise only appends: it
  adds a final newline first when the file lacks one, then writes the row as bytes with an
  LF ending in one write. It never rewrites or reorders the file.
- "What" is built from `key=N` tokens only (keys from `[a-z_]+`, values integers), so
  the review can parse it and no free text gets in.
- Notes are paths as code spans, at most 10, then "and N more"; `|` is escaped.
- Every path and the operation's arguments pass the private-terms check of
  `brain-export/scripts/privacy_sweep.py` (`private_terms`, `mask`), which reads the
  "Always cut" sections of `content/_privacy.md` and `content/_privacy.local.md`: a
  matching path segment is written as `[private]`. When that script is missing (an owner
  deleted `brain-export`), the row is written unmasked and the script says so on stderr.

It lives with `brain-reindex` because that skill is infrastructure every base keeps
(`kb-maintain`, `brain-refactor` and `brain-watch` run its script), not because every
writer calls it.

Alternatives: the agent appends the row itself (rejected: the format drifts between
models and runs, and the review parses it); one row per note (rejected: an ingest of ten
sources would write fifty rows); wikilinks in the Notes column (rejected: the log would
become a hub in Obsidian's graph and backlinks, and `/b:refactor` would rewrite history
when it repairs links on a rename).

### D2. Who writes the log, and how it relates to Recent Changes

A row is written by every skill that writes, moves or retires notes, when it is run by
the owner: `brain-ingest`, `brain-compile`, `brain-enhance`, `brain-curate`,
`brain-refactor`, `brain-import`, `brain-watch` (apply). A skill run by another skill
(`brain-curate` handing a merge to `brain-refactor` or a refresh to `brain-enhance`)
writes no row of its own; the outer skill's row counts what both did. The two new skills
write one row per completed run (`review`, `learn`). `brain-qa`, `brain-lint` and
`brain-output` do not: their dated files in `_outputs/` are the record, and the review
reads them there. `brain-upgrade` does not: its engine never writes under `content/`,
and the commit and the stamp record it.

A row holds counts, the operation name and paths of notes and archived sources, checked
against the private terms (D1). The log is committed like the notes;
`/b:export --public` leaves it out.

`## Recent Changes` stays as it is: a short narrative that the session hook shows at the
start of every session. The log is the full, append-only history behind it. The review
reads both, because the log is empty in a base fresh from the upgrade, and a skill the
owner edited and kept at upgrade writes no rows.

`.gitattributes` gains `content/_outputs/log.md merge=union` and the same for
`content/_outputs/metrics.md`, so two clones or worktrees that both appended rows merge
without a conflict (tested: one header, every row kept). The union driver is built into
git. Rows then follow merge order, not time; readers sort them by time.

### D3. Two new skills, not three

`brain-review` (`/b:review`) and `brain-learn` (`/b:learn`). The metrics are a script
the review runs, not a skill: numbers without a reading of them tell the owner little,
and a third description in every session is a cost paid daily for a command run weekly.
The limit stays three, so a `/b:metrics` command can come later. Paweł agreed on
2026-11-27.

### D4. Metrics: one definition, shared with lint

`lint_links.py` is rewritten as functions that walk the notes and return the resolved
edges between notes (plus links to attachments and templates, and broken links, kept
apart); run as a script it prints exactly what it prints today. Golden-output tests on a
fixture vault come first, before the rewrite, so the output is pinned by the old code.
`brain-lint/scripts/metrics.py` imports it from the same folder and computes:

| Metric | Definition |
|---|---|
| `notes` | notes as `lint_links.py` counts them |
| `orphans` | notes no other note links to, exactly as `lint_links.py` reports them |
| `isolated` | notes with no link to or from another note |
| `weak` | notes with at most one distinct link to or from another note |
| `links_per_note` | distinct links from a note to another note, averaged over `notes` |
| `islands` | connected groups of 2 or more notes besides the largest one |
| `untouched_90d` | notes whose last touch is 90 or more days ago |

So `/b:lint` and `/b:review` cannot report two different orphan counts, the metrics do
not depend on a fresh reindex, and isolated notes are counted by name. With 0 notes every
share and average is `null`. `weak` replaces the `graph.md`-based `weakly_connected` of
`gaps.py` in the review, so the review shows one weakness count; `/b:gaps` itself is
unchanged.

"Last touch" is the latest of `date`, `agent-reviewed` and, in a git base, the file's
last commit. It is the definition `brain-curate` uses, but computed in one
`git log -z --name-only --format=...` call for the whole vault (new code: curate asks git
once per note); `-z` keeps non-ASCII paths unquoted. Each snapshot records its basis
(`git` or `frontmatter`); a comparison across bases reports `untouched_90d` as not
comparable.

`metrics.py --record` adds one row to `content/_outputs/metrics.md` (a Markdown table,
created on first use) and prints the snapshot, the comparison snapshots (D6) and the
differences as JSON. When reading the file it takes the last row per UTC date and sorts
by date, so a union merge that left two rows for one day, or rows out of order, changes
nothing. A second record on the same day replaces that day's row. Without `--record` it
writes nothing.

### D5. The review: inputs, period, output

`brain-review/scripts/review_data.py` gathers the data in one JSON, so the agent reasons
over facts instead of searching:

- log rows in the period, grouped by operation, and the folders of the touched notes;
- the `## Recent Changes` entries of `vault-map.md` dated in the period;
- files in `_outputs/answers/` and `_outputs/learning/` dated in the period, with their
  `gaps:` counts (`gaps.py` lists all answers; the script filters by date);
- in a git base, notes created or changed by commits in the period (`git log -z`), and
  notes changed but not committed (`git status --porcelain -z`);
- sources waiting in `_raw/inbox/`;
- open contradictions (`lint_scan.py`) and the metrics with `--record` (`metrics.py`),
  each run as a subprocess with the interpreter that runs `review_data.py`. A script that
  is missing (an owner deleted its skill) or fails is reported in the JSON as unavailable,
  and the rest is still gathered.

The period starts at the last `review` row of the log; that row carries `days=N`, the
length of the period it covered. When the last row is from the same UTC day, the review
covers that row's period again instead of an empty one. Without a row, the period starts
at the date of the newest `*_review.md` report, else 7 days ago. `--since YYYY-MM-DD`
(a UTC date) and `--days N` override it.

The report goes to `content/_outputs/reports/YYYY-MM-DD_review.md` (`-2`, `-3` when the
name is taken; never overwritten), in the vault language, in a fixed shape: What came in
· Where attention went · Open contradictions · Thin places · Questions the base could not
answer · Metrics (table: now, before, change) · Three moves. Empty sections say that
nothing happened. Each move is one command or action with its target (`/b:enhance
[[Note]]`, "decide which claim holds in [[Note]]", `/b:ingest --backlog`), chosen in
this order: an open contradiction, an unanswered question, an orphan or weak note in a
folder the owner worked in this period, a waiting inbox, an untouched note. The review
writes no note. Below 10 notes it says the base is too young for a review, as `/b:lint`
does, and writes nothing. It asks nothing, so it can run unattended.

### D6. No pass or fail thresholds

`second-brain-os` calls a base healthy below 5 % orphans. The maintainer's base, which
is kept up by hand and by these skills every week, has 7.2 %; a 5 % line would mark it
unhealthy on every review and teach the owner to skip the line. Absolute targets also depend on the kind of
base: a recipe collection links less than a research base. So the review shows the
value, the previous value and the change, and calls out a metric only when it got worse
by at least one step:

| Metric | Step |
|---|---|
| `orphans`, `isolated` | +2 percentage points and at least 2 more notes |
| `islands` | +1 |
| `links_per_note` | −0.5 |
| `untouched_90d` | +5 percentage points and at least 2 more notes |

The comparison is made twice: with the previous snapshot (a sudden change) and with the
newest snapshot at least 28 days old (slow decay that no single week shows). The
"at least 2 notes" part keeps a small base from being called out for one new orphan, and
the steps are large enough that one ordinary ingest on the maintainer's base does not
trigger them. Below 30 notes nothing is called out. Paweł agreed on 2026-11-27.

### D7. `/b:learn`: quiz and explain-back in one skill and one command

`/b:learn <topic or [[Note]]>` runs a Feynman session: the agent finds the notes as
`brain-qa` does (the catalog first), explains the subject in plain words in one short
paragraph, asks the owner to explain it back in their own words, then compares that with
the notes. Every gap is one of three kinds: **the base lacks it** (no note covers it),
**its sources lack it** (a note claims it, but the archived source the note cites does
not support it; the agent reads only the sources the notes in use cite), **you missed it**
(the notes have it and the owner did not say it). `/b:learn --quiz <topic> [N]` asks N
questions (5 by default) one at a time, mixing recall, why and application, grades each
answer against the note it came from with the note named, and ends with the score and
the notes to revisit.

Both save the session to `content/_outputs/learning/YYYY-MM-DD_<topic>.md` (never
overwriting; the topic slug passes the private-terms check of D1) with the mode, the
notes used, the owner's explanation or answers, the gaps by kind and the score, and write
one log row. They change no note: a gap of the first kind is offered as `/b:compile` or
an ingest of a source, a gap of the second kind as `/b:enhance` on that note, as
`brain-qa` offers compile and enhance. Without a person present the skill stops before
asking anything. The session files are committed like saved answers; the skill says so
on its first run, and the changelog says it. Paweł agreed to both (committed sessions,
one command) on 2026-11-27.

### D8. `/b:ingest --backlog [N]`

`--backlog` takes N sources (10 when N is omitted): every YouTube URL given as an
argument, then the oldest sources from `content/_raw/inbox/` up to N. It builds the
normal plan for those only, writes them after the reply, writes a log row, and stops with
"N ingested, M still in the inbox. Run `/b:ingest --backlog` again for the next batch."
in place of "Inbox now empty.".

- **Source.** A text source ingest reads (Markdown, text, HTML, PDF and the like). Image
  and media files (`.png`, `.jpg`, `.gif`, `.svg`, `.webm`, …) are attachments, not
  sources: they do not count towards N and move to `ATTACHMENTS/` with the source that
  references them, as step 9 of Phase 2 does today; one no source in the batch references
  stays in the inbox.
- **Oldest.** A `YYYY-MM-DD` date in the file name, else the frontmatter `date:`, else
  the file's modification time; ties go by name. Modification time is the last resort:
  it does not survive every copy, but files dropped into an inbox are rarely tracked by
  git, so git has nothing better.
- **Unusable files.** An empty or unreadable file does not count towards N, so it can
  never stall the backlog. Every run names such files in its report.
- **Checkpoint.** Ingest already moves every processed file to `_raw/processed/`, so the
  inbox is the checkpoint: there is no state file, a stopped run loses nothing, and it
  works without git.
- **Clusters.** Cluster detection runs within the batch. Two related sources that fall
  into different batches become separate notes linked as usual; the owner can merge them
  with `/b:refactor`. This is the price of a bounded run.
- **Script.** `brain-ingest/scripts/inbox_order.py` lists the inbox as JSON: the sources
  in order, the attachments, the unusable files, and for each source whether its content
  equals a file in `_raw/processed/` (SHA-256). The skill takes the first N.
- **Arguments.** `--backlog` and an optional number right after it are valid arguments;
  any other argument that is neither `--batch` nor a YouTube URL still aborts the call.
  The failure table says so.

`--backlog` combines with `--batch` (no person present: no plan question, the same N per
run). `--batch` alone keeps its meaning and takes the whole inbox, so scripts that rely
on it are unchanged.

Without either flag, when the inbox holds more than 10 sources, interactive ingest
behaves as `--backlog 10` and says so in its plan message: one plan over dozens of
sources is too long to correct, and reading them all in one context is where the reading
gets shallow. Ingest still asks once per run. Paweł agreed on 2026-11-27.

### D9. Skips instead of a selection pass

In an interactive backlog run the plan may propose to skip a source whose content equals
a file already in `_raw/processed/`, or one the owner marks in the reply. On the owner's
OK a skipped file moves to `content/_raw/skipped/`, so the next batch does not offer it
again; the owner can move it back. Batch mode moves nothing; it reports duplicates and
unusable files and ingests the rest. A duplicate never counts towards N, like an
unusable file: an interactive batch still holds N sources to ingest besides its proposed
skips, and a queue of unattended runs cannot stall on a duplicate left in the inbox
(found in the trial on a copy of the maintainer's base). A separate pass that lists the whole backlog for
selection before the first batch is left out: on names and first lines it is shallow, on
full reading it is the cost the batches exist to split.

### D10. The skill description pattern

`CONTRIBUTING.md` gets the pattern:

- The description, single-quoted in YAML: "Use when" with the trigger phrases, one
  sentence on what the skill does and what it writes, and "Do NOT use for …" naming the
  neighbouring skill, only where two skills overlap.
- In the body, a `## Calibration` section: the typical way this skill goes wrong and what
  right looks like, in two to four lines. And a fixed output shape (the report or
  message the skill ends with).

It is applied to the two new skills and to `brain-ingest`, the one existing skill whose
behaviour the owner sees change. `brain-review` says "Do NOT use for a health audit (use
`/b:lint`) or coverage analysis (use `/b:gaps`)"; `brain-learn` says "Do NOT use for
answering a question (use `/b:qa`)"; `brain-ingest` names `--backlog` against `--batch`.
The other skills this change edits get only the log step: rewriting their descriptions
or adding sections would change no behaviour and turn every owner-edited copy into a
conflict at upgrade. They follow the pattern when they are next changed for a reason of
their own. This narrows the decision of 2026-11-04 ("in the skills the package touches");
Paweł agreed on 2026-11-27.

New work in `dev/build_codex_files.py --check`: it also fails on a description over 500
characters (the longest today has 454; `brain-ingest` has 405 and must stay under the
limit after its rewrite), so descriptions cannot grow without notice.

### D11. Upgrade fixes from the pilot (bugs 7–11)

For each fix, what the upgrade to `0.5.0` itself gets, given that the base's old skill
and old `fetch` drive that run:

- **Bug 7, `.kb-onboard.json` still ignored.** When the commit is going to track
  `.kb-onboard.json` and `git check-ignore -v` says the base ignores it, the plan warns
  and names the rule. The engine does not edit `.gitignore`: a file the owner edited is
  never written. The skill offers to remove that one line after the upgrade commit, in a
  commit of its own, on the owner's yes. First run: the warning appears (new `plan`); the
  offer comes from the next upgrade, so the changelog names the one-line edit.
- **Bug 8, folders left in the temp directory.** The plan file and its payload share
  one temporary folder. `commit` deletes that folder as its last step, in a git base
  after the commit and without git after reporting the backup. By then the merges of
  Phase 6 are done, and nothing after `commit` reads the plan: the follow-up steps of
  Phase 7 read the changelog, and the upgrade cycle after an adoption makes a plan of its
  own. `commit` keeps the download folder: `plan` tells the owner to reuse that archive
  offline, and the cycle after an adoption may need it. `apply` deletes nothing. A
  failed step deletes nothing, so its folders stay for diagnosis. `plan` and `fetch`
  print the folders they created, and the skill's last phase passes the downloads, the
  `fetch` folders and every superseded plan folder of the run to a new
  `cleanup --path <folder>...`. Every deletion, by `commit` or `cleanup`, checks that the
  folder is a direct child of the system temp directory, that its name starts with
  `kb-upgrade-`, and that no link or junction is on its path (`kt.link_in_path`), because
  the plan file is not trusted (it sits in the temp directory). Nothing is deleted by
  pattern, so a parallel upgrade in another base keeps its folders. The tests set `TMP`,
  `TEMP` and `TMPDIR` to a `TemporaryDirectory`, so a run leaves nothing.
  `shutil.rmtree` is called without `onexc`, which needs Python 3.12. First run: `commit`
  cleans the plan and its payload, the largest folder; the download and `fetch` folders
  stay, and the changelog tells the owner to let the agent delete the folders `plan` and
  `fetch` printed.
- **Bug 9, the backup without git.** `apply` without git always creates the backup
  folder, copies every file it replaces or deletes into it, as today, and writes
  `backup.json`: the versions, and for every path apply wrote or deleted its hash before
  and after (none for an absent file), which covers the added files, the stamp and
  `content/WRITING_STYLE.md` on a requested re-render. A new `undo --backup <folder>`:
  - refuses unless the current stamp equals the stamp the backup recorded after apply,
    so two backups can only be undone newest first;
  - restores a path only while its current content still has the hash apply left, puts
    back the copy (or deletes an added file), and keeps and names every path changed
    since;
  - writes only the paths `backup.json` lists, never under `content/` except
    `content/WRITING_STYLE.md`, never through a link, in one transaction like `apply`.

  Adoption names the backup folder only when it exists, and now it always does. First
  run: `apply` is new code, so the backup and `backup.json` already exist; the skill's
  guidance on `undo` comes from the next upgrade, and the changelog names the command.
- **Bug 10, a local path in the commit message.** For a zip, a folder or a git clone the
  commit body names the source by its last path component (`Source: zip
  second-brain-template-v0.5.0.zip (<commit>)`). A download keeps its URL. The plan file
  in the temp directory keeps the full path. First run: fixed (new `commit`).
- **Bug 11, the owner's note type.** `lint_scan.py` accepts, in addition to the keys of
  `schema.yml`, the types listed in `NOTE_TYPES` of `.kb-onboard.json`, without required
  fields. Writing them into `schema.yml` at onboarding was the alternative; rejected,
  because `schema.yml` is an owned file and an edit there turns every later template
  change to it into a conflict at upgrade. A type the owner wants fields enforced for
  still goes into `schema.yml` by hand, and `/b:lint` says so for a `bad_type` finding.
  First run: fixed.

### D12. Version and delivery

`0.5.0`: new commands are a minor release, as `/b:watch` was in `0.4.0`. It also ships
the `[Unreleased]` entry of PR #25 (`/b:qa` reads less). Nothing is breaking: every new
behaviour starts on first use, and the one changed default (D8, interactive ingest of
more than 10 sources) only splits a run.

Existing bases get the skills, commands, scripts, Codex stubs and `.gitattributes`
through `/b:upgrade`. An untouched `AGENTS.md` is re-rendered with three new folder rows
(`_outputs/log.md`, `_outputs/metrics.md`, `_outputs/learning/`), a `_raw/skipped/` row
and two Workflows entries (REVIEW, LEARN); an edited one misses nothing, because every
rule is in the skills. A skill the owner edited and kept writes no log rows; the
changelog says so. The `README.md` rows reach new bases only.

## Risks / Trade-offs

- **Two sessions append at the same moment.** One short write in append mode is not
  interleaved on a local disk; a sync client (OneDrive) may still make a conflicted copy.
  Accepted: the loss is one row, and the review does not depend on the log alone.
- **The log grows.** About one row per operation, a few thousand a year at heavy use:
  under a megabyte. No rotation for now.
- **The log keeps old paths.** An append-only history keeps a note's path from before a
  rename. The private-terms check covers the terms known when the row was written; a
  term added later is not removed from old rows, and the changelog says how to edit them
  by hand.
- **Interactive ingest of more than 10 sources changes.** An owner used to one big run
  now needs several. Mitigated by the plan message, `--backlog N` and the changelog.
- **`undo` deletes files.** Only paths `backup.json` lists, only while they hold what
  apply wrote; everything else is kept and named.
- **Context cost.** Two skills and two commands add about 900 characters to every
  session; three "Do NOT use for" sentences add about 60 each.
- **The upgrade to `0.5.0` is driven by the old skill.** Three fixes of D11 reach the
  owner only as changelog steps on that run.

## Migration Plan

Nothing to migrate. Each new file is created by the first skill that needs it. The
course (cheat sheet rows for `/b:review`, `/b:learn` and `--backlog`, a paragraph in
lessons 4 and 5) is updated outside this repository from the text in the final report.
Before the tag, the release is tried on a fresh copy of the maintainer's base in a
temporary folder.

### Archive order

`add-quality-guards` (shipped in `0.3.0`) is still unarchived. It must be archived before
this change. When this change is archived, the argument rule of the `ingest-backlog`
capability is rewritten as a MODIFIED delta of `ingest-plan`, so the two specs never
disagree about which arguments abort an ingest.

## Decisions taken

Paweł accepted the plan on 2026-11-27 with every recommendation: metrics inside the
review (D3), trend only (D6), one `/b:learn` with `--quiz` (D7), interactive ingest of
more than 10 sources switches to batches by itself (D8), learning sessions committed like
answers (D7), the description pattern on the two new skills and `brain-ingest` (D10).
