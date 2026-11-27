# Changelog

All notable changes to the **Knowledge Base Template** are documented here, for people
who have cloned the template and want to pull improvements into their own base.

The format follows [Keep a Changelog](https://keepachangelog.com/). Dates are ISO (UTC).

## [Unreleased]

### Fixed
- **A short private term saved decomposed in a privacy file now matches.** A privacy file
  edited on a Mac can store a term decomposed (NFD: `ę` as `e` plus a combining ogonek).
  `/b:watch`, the `/b:export --public` sweep and the operation log used each term as
  saved, while the text they check is usually NFC. A term that keeps fewer than four
  letters without its diacritics (`Vęx`, a made-up name) has no form without them, so
  it matched no NFC text. It could reach a status box, the watch report and the committed
  snapshot, pass the export sweep, and be written unmasked into `content/_outputs/log.md`.
  A longer term was still found through its form without diacritics. `watch.py` and
  `privacy_sweep.py` now read every term of the "Always cut" lists in NFC, and
  `privacy_sweep.py --terms` prints it that way.

  Existing bases: `/b:upgrade` brings `brain-watch/scripts/watch.py` and
  `brain-export/scripts/privacy_sweep.py`; the privacy files need no change. To see
  whether yours hold decomposed text, run from the vault root:

  ```bash
  python -c "import pathlib, unicodedata as u; [print(p.name, 'ok' if u.is_normalized('NFC', p.read_text(encoding='utf-8')) else 'decomposed') for p in pathlib.Path('content').glob('_privacy*.md')]"
  ```

  If one says `decomposed`:
  - Search for its short terms in the `/b:export --public` bundles you shared, in the
    status boxes of your tool notes, in `content/_outputs/reports/*_watch.md`, in
    `content/_outputs/watch/snapshot.json` and in `content/_outputs/log.md`. The log is
    only ever appended to, so a row there stays until you edit it. Git history keeps the
    old versions of these files.
  - Expect one `/b:watch` run without a baseline for some entries. The snapshot stores a
    repository or URL whose name holds a private term under a hash keyed with all your
    terms, so once a term reads differently, every such hash changes. At the next run
    those repositories and URLs are compared with nothing: an archived or stale
    repository or a dead link can be flagged again, and a licence or release change since
    the previous run is not seen. The run after compares as before. A repository or URL
    with a short term in it was stored in plain; the next run reads that entry and stores
    it hashed.
- **`/b:review` in a shallow clone no longer reports the whole base as new.** In a clone
  made with `--depth` (for example a CI checkout with `fetch-depth: 1`), history stops
  at the graft. `review_data.py` read "what came in" from `git log`, and when the graft
  fell inside the review period, every note looked created and changed by the graft's
  commit, the old ones too. In a shallow clone the review now leaves git out, as in a
  base without git: no commits, and no list of notes not committed yet. It works from
  the operation log, `## Recent Changes` and the dates of saved answers and learning
  sessions. The report says that git was not used, and why.

  Existing bases: nothing to do. `/b:upgrade` brings
  `brain-review/scripts/review_data.py` and the skill. To have the review read git
  history in a CI checkout, clone the whole history (`fetch-depth: 0`) or run
  `git fetch --unshallow` before `/b:review`.
- **`/b:watch` finds private terms in decomposed text and file names.** `watch.py`
  checked each line, link and note name only as written. Text and file names from a Mac
  often come decomposed (NFD: `ą` stored as `a` plus a combining ogonek), and a term from
  your privacy files did not match them. A name written with diacritics did not match a
  term listed without them either. Such a name could reach a status box in a note, the
  watch report, the outline the research agents get, and the committed snapshot. Every
  check now looks at the text as written, in NFC and without diacritics, as the
  `/b:export --public` sweep and the operation log already do. `[private]` replaces the
  term in whichever form it was found.

  Existing bases: `/b:upgrade` brings `brain-watch/scripts/watch.py`; the change in
  `brain-export/scripts/privacy_sweep.py` is comments only. If your notes come from a Mac
  or your privacy files list a term without its diacritics, search for those terms in the
  status boxes of your tool notes, in `content/_outputs/reports/*_watch.md` and in
  `content/_outputs/watch/snapshot.json`. The next `/b:watch` run stores a repository or
  URL that now matches under a hash and drops the entry written in plain, but git history
  keeps the old version of the snapshot.
- **What `sources:` holds on a book note is now written down.** Nothing said whether a
  book note's `source:` or `sources:` names the book or what the notes were taken from.
  When ingest wrote a new book note from an article that discussed the book, the
  article was its only source, and a reader could take the article for what the note
  describes. Ingest step 3, a comment in `schema.yml` and a commented line in
  `content/templates/book.md` now say the same thing. On every note, these fields hold
  where the content came from: a `_raw/` path, a URL or a description. The book itself
  is the title and the `Author:` line. A new note about a work (a book, a film, a talk)
  written from a text about it, not from the work, says so in the first line under its
  title. No field becomes required.

  Existing bases: `/b:upgrade` brings the skill and `schema.yml`; if you edited
  `schema.yml`, the upgrade asks first. `content/templates/book.md` belongs to your base,
  so no upgrade changes it. To get the hint there, add this line before the closing
  `---` of its frontmatter:
  `# sources: ["_raw/processed/YYYY-MM-DD_file.md"]  # where these notes came from, not the book`.
  Book notes that an earlier ingest wrote from a text about the book don't get the first
  line automatically. Add it by hand if you want it.
- **Metrics in a shallow clone use the `frontmatter` basis.** In a clone made with
  `--depth` (for example a CI checkout with `fetch-depth: 1`), history stops at the
  graft. `metrics.py` then dated every older file from the graft's commit, and
  `Untouched 90d` came out too low. A shallow clone now gets the `frontmatter` basis, as
  a vault without git does, and `/b:review` does not compare its `Untouched 90d` with
  rows on the `git` basis.

  Existing bases: nothing to do. `/b:upgrade` brings `brain-lint/scripts/metrics.py`.
  To use the `git` basis in a shallow clone, run `git fetch --unshallow` first. Rows that
  an earlier run recorded there on the `git` basis stay in
  `content/_outputs/metrics.md`; delete them by hand if you want.
- **The `/b:export --public` sweep finds private terms in decomposed text.**
  `privacy_sweep.py` checked each line and file path only as written. Text and file
  names from a Mac often come decomposed (NFD: `ą` stored as `a` plus a combining
  ogonek), and a term from your privacy files did not match them. A name written with
  diacritics did not match a term listed without them either. The sweep now checks each
  line and path as written, in NFC and without diacritics, as the operation log
  (`oplog.py`) already did. The hit's context masks the term in whichever form it was
  found.

  Existing bases: `/b:upgrade` brings `brain-export/scripts/privacy_sweep.py`. If you
  published a `--public` bundle before, and your notes come from a Mac or your privacy
  files list a term without its diacritics, search that bundle for those terms.
- **The indexes record `updated:` in UTC.** `build_indexes.py` wrote local time followed
  by `Z`, and `Z` means UTC. East of UTC every index claimed to be newer than it was;
  west of UTC, older. `/b:reindex` reads that time to decide whether an index is stale.
  The script now writes UTC. Apart from the `updated:` lines its output is byte for byte
  what it was, so the `kb-maintain` workflow sees no other change.

  Existing bases: nothing to do. `/b:upgrade` brings the script, and the next
  `/b:reindex` writes the correct time.
- **`/b:ingest` no longer writes a backlink into a note the source only mentions.**
  Phase 2 gave two rules: step 6 left such a note alone, and step 8 had every linked note
  link back. Now there is one rule, in step 8. The main note links to every note in the
  plan, and each of those links back to it. A note the source only mentions gets a link
  from the main note and is not changed: it is not in the plan you confirmed, and the
  report lists only the notes the run changed. `graph.md` still lists that link as
  incoming.

  Existing bases: nothing to do. `/b:upgrade` brings the skill. Backlinks that earlier
  runs wrote into mentioned notes stay; remove them by hand if you don't want them.
- **`/b:ingest` rebuilds the indexes with the script.** Step 11 told the agent to edit
  `catalog.md`, `vault-map.md` and `graph.md` by hand, while `AGENTS.md` names
  `build_indexes.py`. A hand edit after a run that touched many notes can miss an entry
  or an incoming link. Now the skill runs
  `python .claude/skills/brain-reindex/scripts/build_indexes.py` once, after the last
  note. The script keeps `## Recent Changes` in `vault-map.md` as it is, so the skill
  then adds one line per created or changed note at the top of that section. If the
  script fails, the report lists it under Failures and the indexes wait for
  `/b:reindex`.

  Existing bases: `/b:upgrade` brings the skill. If you think an earlier ingest left an
  index incomplete, run `/b:reindex` once. It keeps your Recent Changes.
- **The `/b:ingest` report has no emoji.** The `Indexes:` line said
  `✅ vault-map / catalog / graph`. It now says `rebuilt (vault-map, catalog, graph)`,
  plain text like the reports of the other skills.

  Existing bases: nothing to do. `/b:upgrade` brings the skill.

## [0.5.0] - 2026-11-27

The base reports back. `/b:review` reads the period since the last review and ends with
three moves you can run as written, `/b:learn` checks what you know against your notes,
and `/b:ingest --backlog` takes a large inbox in batches; an operation log and dated link
metrics feed the review. `/b:qa` reads less to answer, and `/b:upgrade` cleans up its
temporary folders and, in a base without git, can undo an update.

### Added
- **`/b:review`: a periodic review.** Once a week (or whenever you like) `/b:review`
  writes a short report to `content/_outputs/reports/YYYY-MM-DD_review.md`: what came
  in since the last review, where your attention went, open contradictions, thin places,
  questions your base could not answer, the link metrics against earlier snapshots, and
  three moves for the next period, each one a command you can run as it stands
  (`/b:enhance [[Note]]`, `/b:ingest --backlog`, "decide which claim holds in
  [[Note]]"). It changes no note and asks nothing, so it can run from a schedule. The
  period starts at the last review (`--since YYYY-MM-DD` or `--days N` to choose
  another). Below 10 notes it says the base is too young and writes nothing, as
  `/b:lint` does. The review, the operation log, the metrics over time, `/b:learn` and
  the backlog batches were inspired by `undefined-ui/second-brain-os` (MIT); no code was
  taken from it.

  Existing bases: `/b:upgrade` brings the `brain-review` skill and the `/b:review`
  command. Your first review covers the last 7 days and records the first metrics, so it
  has no trend yet; the operation log starts empty after the upgrade, so the first
  review also reads `## Recent Changes` and your git history. `AGENTS.md` lists REVIEW
  and LEARN and the new folders: an `AGENTS.md` you never edited is re-rendered by the
  upgrade, an edited one gets the change as a proposal. `README.md` belongs to your base
  and is not changed.
- **`/b:learn`: learn from your own notes.** `/b:learn <topic or [[Note]]>` explains the
  topic from your notes in a few plain sentences and asks you to explain it back in your
  own words. Then it names what is missing, in three kinds: the base lacks it (no note
  covers it), its sources lack it (a note claims it, but the source it cites does not
  say so), you missed it (the notes have it, you did not say it). `/b:learn --quiz
  <topic> [N]` asks N questions (5 by default) one at a time and grades each answer
  against the note it came from. Every session is saved to
  `content/_outputs/learning/YYYY-MM-DD_<topic>.md` with the notes used, your answers,
  the gaps and the score; no note changes. A gap comes with the command that would close
  it (`/b:compile`, an ingest, `/b:enhance`). The skill needs a person to answer, so a
  scheduled run stops before the first question. A topic that holds a term from the
  "Always cut" lists of your privacy files gets the file name `private`.

  Existing bases: `/b:upgrade` brings the `brain-learn` skill and the `/b:learn` command.
  Learning sessions are tracked by git like saved answers, so they reach every clone of
  your base (`/b:export --public` leaves them out); the skill tells you so on its first
  run. To keep them local, add `content/_outputs/learning/` to `.gitignore`.
- **`/b:ingest --backlog [N]`: a large inbox in batches.** A backlog of dozens of old
  notes and recordings no longer has to go through one plan. `--backlog` takes N
  sources per run (10 when you give no number): every YouTube URL you pass, then the
  oldest files in `content/_raw/inbox/` (by a `YYYY-MM-DD` date in the file name, else
  the frontmatter `date:`, else the file's modification time). It shows the usual plan
  for those, writes them, and stops with "N ingested, M still in the inbox". Run it again
  for the next batch. The inbox is the checkpoint: a run you stop loses nothing, with or
  without git. Images and media next to a source are attachments: they do not count and
  move with the source that uses them. An empty or unreadable file never counts, stays
  in the inbox and is named in every report, so it cannot stall the queue. A file whose
  content equals a source already in `_raw/processed/` does not count either and is
  proposed as a skip; on your OK it moves to `content/_raw/skipped/`, and you can move it
  back. `--backlog --batch` runs the same batches without the plan question and moves
  nothing; `--batch` alone still takes the whole inbox. Related sources that fall into
  two batches become two linked notes; merge them with `/b:refactor` if you want one.
  The order comes from a new script, `brain-ingest/scripts/inbox_order.py`.

  Existing bases: `/b:upgrade` brings the skill and the script. If you edited
  `brain-ingest` and keep your version, it does not know `--backlog` and stops on it, as
  on any unknown argument.
- **Link metrics over time.** A new script, `brain-lint/scripts/metrics.py`, counts
  notes, orphans, isolated notes (no link to or from another note), weak notes (at most
  one), links per note, islands (groups of linked notes cut off from the largest one)
  and notes untouched for 90 days (by `date`, `agent-reviewed` and, in a git base, the
  last commit). `/b:review` runs it and keeps one row per day in
  `content/_outputs/metrics.md`. Orphans are counted by the same code as `/b:lint`
  (`lint_links.py` can now be imported; what it prints is unchanged), so the two
  commands never give two numbers. There is no healthy or unhealthy line: a base of
  recipes links less than a research base. The review shows each value against the
  previous snapshot and the newest one at least four weeks old, and calls a metric out
  only when it clearly got worse (orphans or isolated notes up 2 percentage points and
  at least 2 notes, an island more, half a link per note less, untouched notes up 5
  points and at least 2 notes), never in a base below 30 notes.

  Existing bases: nothing to do. The first `/b:review` records the first row.
- **An operation log, `content/_outputs/log.md`.** Every run of `/b:ingest`,
  `/b:compile`, `/b:enhance`, `/b:curate`, `/b:refactor`, `/b:import` and `/b:watch`
  that wrote, moved or retired a note adds one row: when (UTC), the operation, counts
  (`sources=3 created=2 updated=5`) and up to ten note paths. `/b:review` and `/b:learn`
  add one row each. Rows are only ever added, never rewritten, and the file is created by
  the first run, so it works without git. A folder or file name that holds a term from
  the "Always cut" sections of `content/_privacy.md` or `content/_privacy.local.md` is
  written as `[private]`. The log is committed like your notes; the indexes, `/b:lint`
  and `/b:export --public` leave it out. `.gitattributes` now merges the log and the
  metrics file with git's union driver, so two clones that both added rows merge without
  a conflict.

  Existing bases: `/b:upgrade` brings `brain-reindex/scripts/oplog.py`, the log step in
  each skill and the `.gitattributes` lines. A skill you edited and keep at your version
  writes no rows until you take the template's version. If you keep an edited
  `.gitattributes`, add the two lines yourself:
  `content/_outputs/log.md merge=union` and `content/_outputs/metrics.md merge=union`.
  Rows keep the paths of their day: after `/b:refactor` renames a note, earlier rows
  still name the old path.

### Changed
- **Three skills describe themselves in one pattern.** `brain-ingest`, `brain-review` and
  `brain-learn` now say when to use them, what they write and, where a neighbouring
  skill overlaps, which one to use instead ("Do NOT use for a health audit (use
  `/b:lint`)"), and each ends with a fixed shape of its report. This helps the agent pick
  the right skill. The other skills follow when they next change for a reason of their
  own. For contributors to the template, `CONTRIBUTING.md` describes the pattern and
  `python dev/build_codex_files.py --check` now fails on a description over 500
  characters.

  Existing bases: nothing to do.
- **`/b:ingest` takes an inbox of more than 10 sources in batches.** Without `--backlog`
  and `--batch`, an inbox of more than 10 sources is now taken as `--backlog 10`: the
  plan covers the 10 oldest, says so in its first line, and the report says how many
  wait. A plan over dozens of sources was too long to correct, and reading them all in
  one go is where the reading got shallow. `--batch` keeps its meaning and takes the
  whole inbox without the plan, so scripts that call it are unchanged.

  Existing bases: nothing to do. `/b:upgrade` brings the skill.
- **`/b:qa` reads less on every question.** Until now every question read
  `vault-map.md` and `LIMITS.md` whole, the skill said to read catalog sections and the
  link graph, and `/b:qa` spent a separate model call only on loading the skill. Now
  brain-qa searches `content/_indexes/catalog.md` with a pattern built from the
  question's key terms, in your vault's language and the question's, with synonyms, and
  reads only the matching lines. The map, the catalog's folder sections and a direct
  search of the notes run only when the patterns find nothing, and only after all three
  does the answer say that your vault does not cover the question. `graph.md` is searched
  for a note's title when the question needs links, never read whole. `LIMITS.md` is read
  only before an answer says the vault is sure, complete or consistent, or when you ask
  how far to trust it; three of its rules (one note citing one source is that source's
  view, two notes that agree may rest on the same source, a note not read is a gap) now
  apply to every answer from the skill itself. `/b:qa` includes the skill text, so the
  agent no longer loads the skill in a call of its own; a question asked without the
  command, Codex, and `/b:qa` in a session started in a subfolder of the base (where the
  text is not included) use the skill as before. The Navigation Protocol in `AGENTS.md`
  says the same: the map comes first only for work that writes or reorganizes notes, and
  a question starts from the catalog.

  Measured on 40 questions against a real base: accuracy unchanged (34 of 34 questions
  the base covers answered with the right notes and facts, 6 of 6 correct "the vault
  does not cover this"), text read from the vault −63 %, input the model processed −18 to
  −23 % from the new protocol and a further −8 to −14 % from the command, and the 40
  questions cost 6.75 instead of 8.91 USD. That base had no session-start hook. In a base
  made from this template the session-start hook already puts the map in context, so
  there the change removes the skill's second read of the map; that case was not
  measured.

  Existing bases: nothing to do. `/b:upgrade` brings the skill and the command; if you
  edited either, it asks what to keep. An `AGENTS.md` you never edited is re-rendered by
  the upgrade, and an edited one gets the change as a proposal.

### Fixed
- **`/b:upgrade` warns when your base still ignores `.kb-onboard.json`.** The upgrade
  commit tracks the file even when a `.gitignore` rule ignores it, but while the rule
  stays, git hides the file again whenever it becomes untracked, and the values
  `/b:onboard` recorded stop travelling with the base. The plan now names the rule
  (file, line, pattern). After the commit, the skill offers to remove that line in a
  commit of its own, or, when the pattern also covers other files (`*.json`), to add
  `!.kb-onboard.json` after it. It changes nothing without your yes.

  Existing bases: the upgrade to 0.5.0 shows the warning; the offer comes from the next
  upgrade on. If you see the warning, run `git check-ignore -v --no-index --
  .kb-onboard.json` and remove or negate the line it names, in a commit of its own.
- **An upgrade no longer leaves folders in your temp directory.** Each run left
  `kb-upgrade-…` folders behind (the download, the unpacked release, the plan and its
  payload). Now the plan and its payload share one folder, and `commit` deletes it as
  its last step. `plan` and `fetch` print every folder they create, and the skill ends
  by passing them to the new `upgrade.py cleanup --path <folder>...`, which deletes only
  `kb-upgrade-…` folders directly in the temp directory and refuses anything else. The
  download is offered for deletion too; keep it if you want to plan again offline.

  Existing bases: the upgrade to 0.5.0 runs your old skill, so only the plan folder is
  deleted. After it, ask the agent to list the `kb-upgrade-…` folders in your temp
  directory and pass the ones you no longer need to `upgrade.py cleanup --path`. From
  the next upgrade on, the skill does this itself.
- **Without git, an update can be undone.** In a base that is not a git repository,
  `apply` now always creates `.kb-upgrade-backup/<version>-<time>/`, also for an adoption
  that only adds files (its report used to name a folder that did not exist). The folder
  holds a copy of every file the update replaced or deleted and `backup.json`, which
  records each path's state before and after. `upgrade.py undo --backup <folder>` puts
  that update back: newest update first, only files that still hold what the update
  wrote, never a note (nothing under `content/` except `WRITING_STYLE.md`). A file you
  changed since the update is kept and named. The apply report prints the undo command.

  Existing bases: nothing to do. The upgrade to 0.5.0 already writes `backup.json`, so
  `undo` works for it; the skill describes `undo` from the next upgrade on. A backup
  from an older upgrade has no `backup.json`: put its copies back by hand.
- **The upgrade commit no longer records the path of a local source.** When you
  upgraded from a zip, a folder or a clone, the commit body named its full path (your
  user name, your Downloads folder) in the base's history. It now names the file or
  folder only: `Source: zip second-brain-template-v0.5.0.zip (<commit>)`. A download
  keeps its URL.

  Existing bases: nothing to do. The upgrade to 0.5.0 already writes the short form.
  Older upgrade commits keep what they say.
- **`/b:lint` accepts the note types you named in `/b:onboard`.** A type of your own
  from the onboarding interview (`recipe-note`, say) was reported as an unknown type in
  every lint, because lint knew only the types in `schema.yml`. Now `lint_scan.py` also
  accepts every type listed in `NOTE_TYPES` of `.kb-onboard.json`. Such a type has no
  required fields; to have lint check fields for it, add it to `schema.yml` with its
  fields. The lint report says so next to an unknown type. A missing or unreadable
  `.kb-onboard.json` changes nothing.

  Existing bases: nothing to do. `/b:upgrade` brings the fix (`brain-lint`:
  `scripts/lint_scan.py` and the skill).

## [0.4.1] - 2026-11-22

A patch release. An untouched `AGENTS.md` now follows every change to its template, and
YouTube transcripts keep lines that a manual subtitle track repeats. On Windows with
Python 3.11 or older, `/b:upgrade` now also refuses to write through a junction.

### Fixed
- **An untouched `AGENTS.md` follows every change to its template.** `/b:upgrade`
  re-rendered `AGENTS.md` by default only when the versions it crossed held an entry
  marked breaking, and neither `0.3.0` nor `0.4.0` has one. So a base that went through
  the `0.2.0` command rename with an older engine still listed `/ingest` instead of
  `/b:ingest`, and no base got the `0.4.0` sentence about `/b:<name>` in Codex unless the
  owner asked for a re-render. Now the plan re-renders an untouched `AGENTS.md` whenever
  its template differs from the one it was rendered from, whatever the versions hold.
  The plan says so, and you can still keep the file (`"rerender": []`); the next upgrade
  asks again. A file you edited is never written: you get the difference as a proposal,
  as before. `CLAUDE.md` and `content/WRITING_STYLE.md` still change only when you ask.
  The plan now also tells the two kinds of proposal apart: `edited by hand`, or `not
  provably untouched` when the base was adopted from an older rendering of `AGENTS.md` and
  the stamp has no output hash for it.

  Existing bases: nothing to do. The upgrade to the release that carries this fix brings
  `AGENTS.md` up to date if you never edited it. If the plan calls your `AGENTS.md` `not
  provably untouched` and you never edited it, or do not need your edits, take the
  proposal whole once: copy `render/AGENTS.md` from the plan's payload folder over
  `AGENTS.md`, commit, and plan again. From then on upgrades keep it current. The
  `brain-upgrade` skill offers this step.
- **YouTube transcripts keep lines that a manual subtitle track repeats.** Since `0.3.0`,
  `yt_fetch.py` dropped any line a caption repeated from the caption before it. That is
  right for auto-captions, which roll and show each line twice, but a manual track that
  opened a caption with the previous caption's last line lost it: `A / B` then `B / C`
  became `A B` and `C`. Now only a track with the word timings that auto-captions carry
  is treated as rolling. Every other track keeps all its lines, and only a caption that
  repeats the previous one whole is merged, as before `0.3.0`.

  Existing bases: `/b:upgrade` brings the fix (`brain-ingest`: `scripts/yt_fetch.py` and
  its tests). Transcripts already in `content/_raw/processed/` stay as they are. For the
  full text of a video with manual subtitles, re-run `yt_fetch.py <url> --out-dir <a temp
  folder>` and replace the transcript below the archive's frontmatter.

### Security
- **`/b:upgrade` sees Windows junctions on Python 3.11 and older too.** The upgrade
  refuses to read or write through a symbolic link or a Windows junction, so that a link
  can never lead it into your notes under `content/`. It recognised a junction only
  through `os.path.isjunction`, which Python has had since 3.12. On Windows with Python
  3.11 or older a junction went unnoticed: with `.claude/hooks` as a junction into
  `content/`, the dry run did not stop, and `apply` could write the template's files
  through it into your notes. Symbolic links were caught on every Python, and Linux and
  macOS have no junctions. The check now reads the junction mark itself, on every Python.
  The template's tests now also run on Windows with Python 3.11, so a function that older
  Pythons lack shows up as a failing test.

  Existing bases: nothing to do before you upgrade. `/b:upgrade` runs the engine of the
  version it installs, so the upgrade to this version already checks junctions. The
  `Tests` workflow it brings runs a third job, Windows with Python 3.11, on each push to
  `main` and each pull request; delete that `include:` entry in
  `.github/workflows/tests.yml` if you don't want it. If you upgraded on Windows with
  Python 3.11 or older and keep junctions in your base, list them from the base's root
  folder in PowerShell with
  `Get-ChildItem -Recurse -Force -Attributes ReparsePoint | Select-Object FullName, LinkType, Target`.
  A junction among the template's own files (under `.claude/`, `.agents/`, `.github/` and
  the like) that points into `content/` may have let an earlier upgrade overwrite the
  notes there: check those notes with `git status` and `git log` and restore any change
  you did not make.

## [0.4.0] - 2026-11-16

Codex gets the template's skills and its session hook, from the same files Claude Code
reads, and `/b:watch` keeps tool notes current. Two skill descriptions are read whole
again, and the public export and the watch report hold back private names more reliably.

### Added
- **Codex gets the skills and the session hook.** Codex reads `AGENTS.md`, but not
  `.claude/skills/` or `.claude/settings.json`, so in Codex a base had its instructions
  and none of its workflows. Now each skill has a stub at
  `.agents/skills/<skill>/SKILL.md`, where Codex looks: the skill's frontmatter, unchanged,
  and one instruction, to read and follow `.claude/skills/<skill>/SKILL.md`. Each skill
  keeps one text, for both agents, and its scripts stay where they are.
  `.codex/hooks.json` runs the same `.claude/hooks/load_vault_map.py` as Claude Code, by a
  relative path, so the vault map loads in the root folder of any clone, and of a base
  downloaded as a ZIP. In Codex, start a skill by name, `$brain-ingest` for `/b:ingest`,
  or pick it from `/skills`. `ENVIRONMENTS.md` has the details, including what was tried
  with the `brain-research*` skills, which Codex runs with its own subagents and question
  form. Claude Code does not read the new files. The template's own tests fail when a stub or the hook file is out of
  date; in a base, `tests/run_tests.py` only names that check in its SKIP line.

  Existing bases: `/b:upgrade` adds one stub per skill and `.codex/hooks.json`, which
  Claude Code does not read. Keep them even if you never use Codex: deleting them brings
  back a `restore?` row at every upgrade. To use Codex, open the base's root folder in it,
  trust the project and approve the hook in `/hooks`, once per clone. After you add a
  skill or edit a skill's description, edit its stub by hand (`ENVIRONMENTS.md` shows the
  file); an edit to a skill's body needs nothing. `AGENTS.template.md` now tells an agent
  without slash commands to read `/b:<name>` as the `brain-<name>` skill; your `AGENTS.md`
  gets that sentence only when you re-render it. If you deleted a template skill, the
  upgrade adds its stub anyway, and the stub tells Codex the skill was removed: delete
  `.agents/skills/<skill>/` after the upgrade and commit.

  If you ran Codex's `/import` in this base, clean up before the upgrade, or it stops on
  conflicts. First copy `.agents/` and `.codex/` to a folder outside the base, and carry
  any edit you made there over to `.claude/skills/<skill>/SKILL.md`,
  `.claude/settings.json` or a skill of your own. Then delete `.agents/skills/<skill>/`
  for each template skill and `.codex/hooks.json` (required), and every
  `.agents/skills/source-command-*`, `.codex/hooks/` and `.codex/agents/` (advised: the
  wrappers double the skill list and the rest is broken). If that output was committed,
  delete it with `git rm -r` and commit the deletion. Keep your own skills under
  `.agents/skills/`: the upgrade leaves them alone.
- **`/b:watch`: a recurring status check for tool notes.** A tool note goes out of date
  without anyone noticing: the project ships a rewrite, gets archived, renamed or
  relicensed. `/b:watch` (the `brain-watch` skill) checks every `type: tool` note in two
  passes. A cheap pass reads GitHub (archived, renamed, licence, latest release, last push)
  or the product URL and compares it with a snapshot in `content/_outputs/watch/`; only a
  change is flagged. Web-search agents then research the flagged notes plus up to
  `--deep-budget` notes that are due (never checked, or checked 90 or more days ago). The
  skill writes only a "Status check YYYY-MM-DD" box under each researched note's H1 and its
  `status-checked` / `project-status` frontmatter, adds `repo:` or `homepage:` once to
  notes that have neither, and writes a report to `content/_outputs/reports/` with the
  notes to refresh (`/b:enhance`) and to retire (`/b:curate`). It never moves a note and
  holds back any line that contains a term from the "Always cut" section of
  `content/_privacy.md` or of the new, git-ignored `content/_privacy.local.md`. Run it by
  hand, or on a schedule (monthly works): an unattended run asks nothing.

  Existing bases: after `/b:upgrade`, run `/b:watch --dry` to see which notes it tracks
  and which need a `repo:` / `homepage:` link (or `watch: false`). Put names that must not
  even appear in the repository in `content/_privacy.local.md`; `.gitignore` now ignores
  it and the watch workspaces (`content/_raw/research-workspaces/watch-*/`).

### Changed
- **`/b:export --public` also cuts the names in `content/_privacy.local.md`.** The export
  took its private terms from `content/_privacy.md` only, so a public bundle kept a client
  name that lives only in the git-ignored local file. Now `privacy_sweep.py --terms` reads
  the "## Always cut" section of both files, as `/b:watch` does: HTML comments are ignored,
  each term also matches joined, hyphenated and underscored (`Acme Labs` → `acmelabs`,
  `acme-labs`, `acme_labs`), and case does not matter. The redaction step cuts that list,
  and the sweep flags any term that survived, in a note's text or its path. Its context
  lines mask each term as `[private]`, and the redaction report (committed with the vault)
  never quotes one. The verdict table shows how many terms came from each file, so a
  checkout without the local file, such as a fresh git worktree, is easy to spot. The
  sweep now runs from the vault root or with `--root <vault>`, and exits 1 when it finds
  no `content/` there.

  Existing bases: nothing to do; `/b:upgrade` brings the new skill. `content/_privacy.md`
  is yours, so its starter text is unchanged in your base: names that must not even be
  committed go in `content/_privacy.local.md`, under a `## Always cut` heading.

### Fixed
- **Two skill descriptions are read whole again.** In `brain-export`, an unquoted ` #`
  started a YAML comment, so the skill list showed 49 of the description's 452
  characters. In `brain-ingest`, a `: ` made the frontmatter invalid YAML, which some
  parsers repair and others reject. Both descriptions are now quoted, with the same text.
  The `brain-export` and `brain-import` descriptions also name the template's commands,
  `/b:import` and `/b:export`, instead of `/import` and `/export`: in Codex, `/import` is
  the command that converts a Claude Code project.

  Existing bases: nothing to do; `/b:upgrade` brings the fix. If you edited one of these
  three `SKILL.md` files, the upgrade asks what to keep.

### Security
- **`/b:watch` writes what web pages say as text, not as markup.** The status box is
  built from what the research agents read on web pages and in release notes, and it is
  published. Quartz renders raw HTML, and its Obsidian plugin turns `==highlight==` and
  `![[embed|alias]]` back into HTML after decoding entities, so a `<script>` or
  `<img onerror=…>` in a result could have run on your site. Now every box line (results,
  `overrides.json` lines, and `digest.json` again when `apply` writes it) has `<`, `>` and
  character references escaped. A link is kept only to a plain http(s) URL, an image
  becomes a link, and `[[wikilinks]]` survive only as a plain link to a tracked note.
  `==`, `%%`, `#tags` and link definitions are broken up. The report escapes GitHub text
  (release tags, licences) the same way and keeps its own `<details>` list.
- **The `/b:watch` snapshot no longer names a private repo or site.** The snapshot in
  `content/_outputs/watch/` is committed. A repo or URL that contains an "Always cut" term
  is now stored under a hash keyed with your private terms, and a value that contains one
  (a renamed repo's name, a release tag) is left out. Changing the terms resets those
  entries once.
- **`/b:watch` checks private terms before it escapes, and again at `apply`.** Escaping
  can split a term (`Team #2` gets a no-break space), so a release tag with one in it could
  reach the report. The report now checks each value as it came in. `apply` checks
  `digest.json` again, since it may have been translated in between, and holds back a note
  whose lines match or whose status is not one it knows.
- **Private terms also match without Polish letters**, in `/b:watch` and in
  `/b:export --public`. Names in folder slugs and URLs are usually written without them,
  so `Łąka Wiśnia` now also matches `laka-wisnia` and `Laka Wisnia` (`ł` → `l`, other
  diacritics dropped). A name that leaves fewer than four letters keeps only its written
  form, so a short term like `Wąs` does not catch the English "was".

  Existing bases: nothing to do; `/b:upgrade` brings the fix. The next `/b:watch` run
  rewrites the snapshot, hashing any private entry an earlier run wrote in clear.

## [0.3.0] - 2026-11-13

A quality package for what the agent writes into your base. Ingest now shows its plan
before writing and updates every note a source touches. Contradictions are marked, not
overwritten. Source paths can be checked, Q&A keeps its answers and their gaps, and a
new `LIMITS.md` says where the method fails. The ideas came from
[super-brain](https://github.com/superhero-tech/super-brain) by AI Product Heroes (MIT);
the text and code are our own.

Existing bases: run `/b:upgrade`. It brings the updated skills (`brain-ingest`,
`brain-qa`, `brain-lint`, `brain-enhance`, `brain-compile`, `brain-gaps`,
`brain-curate`), the scanners and their tests, the `kb-maintain` workflow, and the new
`LIMITS.md`. It re-renders your `AGENTS.md` by default only when it recognises the file
as unedited and your update crosses a **BREAKING** entry, as an update from before
`0.2.0` does. Otherwise it changes that file only if you ask. Every rule also lives in
the skills, so an edited `AGENTS.md` misses nothing. It never touches your note
templates in `content/templates/`, your `README.md` or any note. After the upgrade, run
`/b:lint`. Notes whose `source:` still points at `_raw/inbox/` show up as warnings, most
of them with a ready `fix=` path. Fix them when it suits you; nothing is blocked. If you
run `/b:ingest` or `/b:qa` without a person present, add `--batch` or `--no-save` (see
below).

### Added
- **Lint finds source paths that lead nowhere, and proposes the fix.** Until now nothing
  checked the `source:` a note points to, and ingest left many of them pointing at
  `_raw/inbox/` after it had archived the file. `lint_scan.py` now reads `source:` and
  the new `sources:` list (a single value, a block list or `["a", "b"]`, on one line or
  several, with or without `# comments`) and reports every `_raw/` path that does not
  exist, in the new `missing_source_file` class. When a missing `_raw/inbox/<name>` has
  exactly one archived copy `_raw/processed/<date>_<name>`, the finding carries
  `fix=<that path>`, ready to paste; with several copies (a copy ingest numbered because
  the name was taken, such as `2026-10-20_talk-2.md`, counts) it lists them as
  `candidates=` and proposes none. URLs, wikilinks and free-text sources such as "Call
  with the vendor" are not paths and are skipped.
- **Lint lists notes with open contradictions.** The new `contradiction` class names
  every note that carries a `> [!contradiction]` callout, with the number of callouts.
  Examples of the callout inside a code block do not count, also in a block opened with
  four backticks to show triple-backtick Markdown.
- **Both new classes are warnings.** The scanner's JSON gains a `warnings` list naming
  them. They do not block the optional pre-commit hook, which still blocks only on
  missing frontmatter and schema violations, and the weekly `kb-maintain` summary lists
  them under "Warnings", apart from "Issues". Every existing class and field of the
  scanner's output is unchanged, so scripts that read it keep working.
- **`/b:gaps` lists the questions your vault could not answer.** `gaps.py` gains
  `answer_gaps`: every saved answer in `content/_outputs/answers/` whose `gaps:` count is
  above zero, newest first, with its title, date and count (`--answers DIR` points it
  elsewhere). The `brain-gaps` skill adds them to its to-build list. Answers saved before
  this release have no `gaps:` field and are skipped.
- **`LIMITS.md`: where this method fails, and what to do about it.** A new file in the
  root of your base names five failure modes and, for each, what you and the agent do:
  errors that compound when answers are filed back into notes, citations that look like
  proof, the context ceiling, the cost of every operation, and the whole base being one
  model's reading of your sources. It ends with the reminder that a tidy base is not a
  correct one. `/b:qa` and `/b:lint` read it before they say the base is sure of
  anything. It is a template file: upgrades keep it current and keep your own additions.

### Changed
- **`/b:ingest` shows its plan before it writes, and updates every note a source is
  about.** Ingest used to write first and ask only about clusters. Now it reads every
  source, maps it against your notes and sends one message per run. For each source it
  gives what the source claims in one sentence, the notes it will create, the existing
  notes it will add to and what each gains, and the claims in your base the source
  contradicts. The cluster question comes in the same message, so ingest still asks at
  most once. Reply OK, correct the reading or a note to leave alone, or cancel. A source
  no longer turns into one summary note: it gets a main note, and every existing note it
  adds to gets the new material, the source reference and a link to the main note and
  back. The report lists every note each source touched, and says why when only one
  changed. Contradictions are marked with a `> [!contradiction]` callout next to the
  earlier claim, which is never overwritten: you decide which claim holds.
  `/b:ingest --batch` skips the question, says up front that batch notes come out
  thinner because nobody corrects the reading, and keeps clustered sources as separate
  notes. **If you run ingest without a person present** (a script, `claude -p`), it now
  stops at the plan and writes nothing: add `--batch` to such runs.
- **`/b:qa` saves substantive answers by default, with what they rest on and what your
  vault could not answer.** It used to offer to save, so most answers were lost when the
  session ended, and with them the questions your notes could not answer. Every
  substantive answer is now saved to `content/_outputs/answers/YYYY-MM-DD_<topic>.md`
  (an `answer-note`, never overwriting an earlier one), and the skill tells you the path.
  The note has a section listing the notes the answer rests on and marking what is
  inference, and a section of gaps: each part of the question your vault could not
  answer, including contradictions it could not resolve. The headings follow your
  base's language, and the number of gaps goes in a `gaps:` field, which `/b:gaps`
  reads. A one-line lookup is not saved, and the skill says so. When a note carries a
  `> [!contradiction]` callout, the answer shows both claims. Before it says your vault
  is sure of anything, the skill reads `LIMITS.md` and names the limits that apply.
  Promoting an answer with `/b:compile` or filing it back with `/b:enhance` is still
  only offered. **To answer without writing,** pass `--no-save` or ask not to save. A
  tool that queries your base without a person present should always pass `--no-save`,
  or every question leaves a file behind.
- **`/b:lint` says when it is too early, and every finding comes with a next step.**
  Below 10 notes the skill says a lint would only find noise, gives the count and stops
  without a report. Above that, every finding names the note and what to do: the edit or
  the skill to run, such as the replacement for a stale source path. Warnings are
  listed apart from issues, and the report ends with a "Fix first" list ordered by what
  each fix unblocks. First come notes hidden from the other checks, then single fixes
  that clear many findings, then the rest. A clean report now says that it means the
  vault is in order, not that its content is true, and points to `LIMITS.md`.
- **`/b:enhance` and `/b:compile` mark contradictions instead of smoothing them over.**
  When material conflicts with what a note claims, both skills keep the earlier claim,
  add a `> [!contradiction]` callout with both claims and their sources, and list it in
  their summary. Enhance leaves an existing callout alone until you decide which claim
  holds. Both record raw source files in `source:` or `sources:`, and `/b:curate` reads
  tool URLs from either field.
- **`AGENTS.md` points to `LIMITS.md` and shows `sources:`.** The instruction template
  gets a short "Limits" section, and its frontmatter example now shows
  `sources: ["_raw/processed/YYYY-MM-DD_filename.md"]` instead of an inbox path: the old
  example is where many stale `_raw/inbox/` source paths came from. Only new bases and
  bases that re-render an unedited `AGENTS.md` get this. Every rule it points to also
  lives in the skills, so an edited `AGENTS.md` misses nothing.
- **`README.md`: no source count, and a link to the course.** The line "good for ~500
  sources" is gone, and the setup section links a step-by-step course.

  Existing bases: nothing to do. `README.md` is yours and an upgrade never writes it. If
  you want these lines, copy them by hand.

### Fixed
- **The weekly `kb-maintain` run no longer fails where it may not open a pull request,
  and no longer fails on every run after its first.** GitHub lets a workflow open pull
  requests only when the repository allows it, and that setting is off by default. So
  the workflow pushed the refreshed indexes to `kb-maintenance/reindex`, then failed with
  `GitHub Actions is not permitted to create or approve pull requests`, and GitHub sent a
  failure notice. It now ends without an error: a warning and the run summary name the
  setting (**Settings → Actions → General → Workflow permissions → Allow GitHub Actions to
  create and approve pull requests**) and link the page where you open the pull request
  by hand. Any other error still fails the run. The same step had a second fault: once a
  run had pushed that branch, every later run was refused at the push (`stale info`),
  because the checkout does not fetch the branch, so turning the setting on alone would
  not have brought a pull request. The push now checks what the branch holds on GitHub
  first. `README.md` and the `/b:onboard` handoff name the setting.

  Existing bases: `/b:upgrade` brings the workflow (`.github/workflows/kb-maintain.yml`)
  and the onboarding note. If your base is on GitHub, turn the setting on once; in a
  repository owned by an organization, an owner may have to allow it in the
  organization's settings first. If a refresh already waits on `kb-maintenance/reindex`,
  the next run that finds the indexes out of date replaces it and opens the pull request;
  to get it sooner, run **KB maintenance** from the **Actions** tab. `README.md` is yours and an upgrade never writes
  it: copy the new "Weekly maintenance on GitHub" section by hand if you want it.
- **Lint reads lists written without indentation.** `lint_scan.py` read a YAML list only
  when its items were indented (`tags:` then `  - book`). Items written at the start of
  the line (`tags:` then `- book`) are valid YAML, what PyYAML writes, and how
  `build_indexes.py` already read them, but the scanner saw an empty field: such a note
  was reported for missing tags, or for a schema violation that blocks the optional
  pre-commit hook, and its `sources:` list was never checked. Both forms are now read
  the same way. A note can only lose findings from this.
- **Ingest records where the source file really ends up.** Ingest moved each inbox file
  to `_raw/processed/YYYY-MM-DD_<name>` but left the note's `source:` pointing at
  `_raw/inbox/<name>`. It corrected the path only for YouTube, so for files the reference
  led nowhere. Ingest now chooses the archive name first (with `-2`, `-3` when the name
  is taken) and writes that path into every note the source touches. A note that gains a
  second source gets a `sources:` list, with its earlier `source:` first. Before
  reporting, ingest checks that every path it wrote exists. Paths written by earlier
  versions are not rewritten: `/b:lint` lists them, with the fix where one archived copy
  exists.
- **`/b:upgrade` no longer stops at its own plan step.** The skill passed the archive it
  had just downloaded to `plan --source`. The engine counts every local zip as unverified,
  so the default path ended in a refusal. The skill now runs `plan --to <version>`: the
  engine downloads the release you agreed to over HTTPS, and the skill checks that the
  commit is the one you were shown. A zip from elsewhere is still refused without your
  consent, and a file placed next to it changes nothing.

  Existing bases: a base on `0.2.x` still follows its own older skill for this one
  update, so the first `plan` is refused once. The message names the way out (drop
  `--source`, add `--to <version>`), and your agent can follow it. Updates after that use
  the new skill. Nothing else is needed.
- **Updates carry a file's executable bit.** `.githooks/pre-commit` is executable since
  `0.2.0`, but updates compared content only, so a base from before `0.2.0` kept the old
  mode. Git on Linux and macOS skips a hook that is not executable, and the `Tests`
  workflow, which checks that hook, failed on Ubuntu. The plan now has an **Executable
  bit** section for the files `.kb-manifest.json` lists under `executable`. A new or
  updated file gets the bit as it is written, and adoption does the same. The bit is only
  ever added. On a file you edited, your text stays and only the bit changes; you can
  decline it with `"executable": false`.

  Existing bases: `/b:upgrade` shows the row and sets the bit, also when the content
  already equals the release, so a base that went through `0.2.x` is covered too. If your
  clone uses `.githooks` (`git config core.hooksPath .githooks`), a hook that git skipped
  until now starts to run on Linux and macOS, and blocks a commit with a note the check
  rejects.
- **An untouched `AGENTS.md` follows a breaking release.** The agent reads this file in
  every session, but it was re-rendered only on request, so after a breaking change it
  could keep describing the old setup. When the versions you update across include a
  breaking entry, `/b:upgrade` now re-renders an untouched `AGENTS.md` by default.
  `content/WRITING_STYLE.md` and `CLAUDE.md` stay on request.

  Existing bases: nothing to do. An `AGENTS.md` you edited is never overwritten: the plan
  says so and you compare it by hand. To keep an untouched copy as it is, answer no
  (`"rerender": []`). A base already past that release can ask for it with `--rerender`.
- **The plan names a file the template renamed under your edits.** When the template
  moves a file you edited, your copy stays at the old path, and the plan only said
  "removed from the template". It now also lists `old -> new` under **Renamed by the
  template**. Your edits still don't move on their own, and the skill at the old path
  stays in use until you carry them over. The match is a guess from the two paths and
  only produces this line.

  Existing bases: nothing to do. The section appears when it applies.
- **Undoing an update is documented in the right order.** Undo the newest commit first:
  the upgrade, then the adoption. Reverting the adoption alone runs into conflicts. A
  reverted adoption also removes `.kb-onboard.json` from your disk if it was the commit
  that added it, and `.gitignore` hides that, so `README.md` and the `brain-upgrade` skill
  now give the command that brings the file back.

  Existing bases: `/b:upgrade` brings the note in the skill. Nothing else is needed.
- **`/b:ingest` hands yt-dlp only the video it checked.** `yt_fetch.py` read the video id
  from the URL you pasted, then passed that URL on, so yt-dlp could pick another video
  from `?v=A&v=B`, or go through a whole playlist from `&list=`. It now gets a URL built
  from the checked id. The fallback that runs yt-dlp as a Python module also leaves the
  current folder out of its search, so a stray `yt_dlp.py` in your base no longer runs in
  its place.

  Existing bases: `/b:upgrade` brings the fix (`brain-ingest`: `SKILL.md`,
  `scripts/yt_fetch.py` and its tests). Nothing else is needed.
- **YouTube ingest finds the captions of videos with dubbed audio.** A video with dubbed
  audio tracks has an auto-caption transcript per dub, and yt-dlp lists every one of
  them, machine-translated, under the plain language code. Asking for `en` downloaded the
  last of those: for one video, its Ukrainian dub translated back into English. YouTube
  usually refuses such translations with `HTTP 429`, and every other language failed the
  same way, so `/b:ingest` stopped with `No captions and whisper.cpp not configured`
  although English captions existed. `yt_fetch.py` now picks the languages from the
  video's metadata. For each preferred language (`en`, `en-US`, `en-GB`, `pl`) it takes
  manual subtitles first, then the original-language transcript (`en-orig`), then the
  plain code as before. The video's own original language (`de-orig` for a German video)
  is tried last when none of those matched. Videos with only plain `en` captions are
  fetched as before.

  Existing bases: pick it up with `/b:upgrade`, which updates the `brain-ingest` skill
  (`scripts/yt_fetch.py` and its tests). Nothing else is needed.
- **YouTube transcripts no longer repeat every line.** Auto-captions roll: each caption
  shows the previous line again above the new one. `yt_fetch.py` joined both, so the
  archived transcript of an auto-captioned video had every line two or three times
  (`[0:01] A`, `[0:01] A B`, `[0:03] B`, …). It now keeps each line once, at the time it
  starts. Two smaller faults in the same parser are fixed too: HTML entities are decoded
  (`S&amp;P` is now `S&P`), and a line that opens a caption block, such as the first line
  of the video, gets its own start time instead of the time it ends. Manual subtitles
  come out as before.

  Existing bases: `/b:upgrade` brings the fix (the same files as above). Transcripts
  already in `content/_raw/processed/` keep their repeated lines; the notes written from
  them are not affected. For a clean copy, re-run `yt_fetch.py <url> --out-dir <a temp
  folder>` and replace the transcript below the archive's frontmatter.

## [0.2.1] - 2026-10-15

### Fixed
- **YouTube ingest works on Windows with Smart App Control.** `brain-ingest`'s
  `yt_fetch.py` always ran the `yt-dlp` command and gave up when it was not on PATH. On
  Windows with Smart App Control in enforce mode, the unsigned `yt-dlp.exe` that pip
  installs is blocked (`WinError 4551: An Application Control policy has blocked this
  file`), so every `/b:ingest` of a YouTube URL failed. The signed `python.exe` is
  allowed, so `python -m yt_dlp` still runs. The script now picks the command itself, in
  this order: `$YT_DLP_CMD` if you set it (used as given, for example
  `"C:\Program Files\yt-dlp\yt-dlp.exe"`; double-quote paths with spaces); a `yt-dlp` on
  PATH that actually starts (`yt-dlp --version` succeeds); `python -m yt_dlp` with the
  interpreter the script runs under, when the module is installed. Metadata, captions
  and the Whisper audio download all use that command. When none is found, the script
  exits 3 with `yt-dlp not found` and the install hint (`pip install yt-dlp`, or set
  `YT_DLP_CMD`), and `/b:ingest` stops with that hint; it no longer pre-checks `yt-dlp`
  with `which`. A `$YT_DLP_CMD` that cannot start fails the same way, naming the command,
  instead of with a traceback. A working `yt-dlp` on PATH is still preferred, so nothing
  changes where ingest already worked. The `/b:onboard` prerequisite check also accepts `python -m yt_dlp`, and the
  README and the test notes no longer say yt-dlp has to be on PATH.

  Existing bases: pick it up with `/b:upgrade`, which updates the `brain-ingest` skill
  (`SKILL.md`, `scripts/yt_fetch.py` and its tests). Nothing else is needed, unless you
  relied on a standalone `yt-dlp` executable that is no longer there: then run
  `pip install yt-dlp` with the Python you run the skills with.

## [0.2.0] - 2026-10-13

### Added
- **`/b:upgrade` pulls new template releases into your base.** Until now every update
  meant reading this file and re-copying files by hand. The new `brain-upgrade` skill
  downloads a release from GitHub (or takes a release `.zip` or a local clone, so it
  also works offline and without git), shows a **dry run** (the entries of this file
  since your version, **BREAKING** first, and a plan per file), and changes nothing until
  you approve the plan in one table. Template files you never touched are updated;
  files you edited are kept, and you are asked only when the template changed the same
  file (keep, overwrite, or merge together with the agent). Files the template removed
  are proposed for deletion, checked only when you never edited them. `CLAUDE.md`,
  `AGENTS.md` and `content/WRITING_STYLE.md` are re-rendered from the new templates only
  when you ask and only while you have not edited them by hand. Your notes in `content/`
  and your `README.md` are never written. With git the update is one commit
  (`chore(template): upgrade to …`) holding exactly what the update wrote: if one of
  those files changes before the commit (a sync client, an editor), it stops without
  staging anything and names the file. Without git every replaced file is copied to
  `.kb-upgrade-backup/` first. Before the update tool from a downloaded release (or a
  folder or zip you point to) runs at all, `/b:upgrade` shows you its repository,
  version, tag, commit and where it came from, and asks for your yes; a release from a
  different repository than your base follows is called out, and the tool refuses it
  without your explicit consent. A download is judged by the repository it was fetched
  from, not by what the archive says about itself; a folder, a zip or a local clone you
  point to cannot prove where it comes from, so you confirm it explicitly too. Releases are not signed: the tool comes from the same
  repository as the skills and hooks it installs. Applying is all or nothing: if a write fails halfway (a
  file locked by OneDrive or an antivirus, a full disk), every file is put back as it was
  and the run says so; the same happens when a planned file changes, or a link appears,
  while the update runs. A file that something else (a sync client, an editor) changed
  after the update wrote it is left as it is and named, so you can check it against git
  or the backup. Whatever a downloaded manifest, a history index or your stamp
  claims, it writes nothing outside your base, nothing under `content/` (except
  `content/WRITING_STYLE.md` when you ask for its re-render) and never your `README.md`,
  and it refuses paths that Windows or macOS would treat as one file. It never writes
  through a symbolic link or a junction: when a template file, or a folder above it, is
  one, the dry run stops and names it. Uncommitted edits to `.kb-template.json` or
  `.kb-onboard.json` stop apply just like edits to any planned file. The base records
  its template version and what the template shipped in a new stamp, `.kb-template.json`.
  The scripts (`.claude/skills/brain-upgrade/scripts/`) need only the Python standard
  library.

  Existing bases: your base has neither `/b:upgrade` nor a stamp yet, so the first
  update runs the engine of the `0.2.0` release (or newer) and starts with an adoption
  (next entry). Download the release `.zip` (or use a clone of the template), unpack it
  outside your base, and ask your agent to follow its
  `.claude/skills/brain-upgrade/SKILL.md`, or run it yourself from your base:
  `python <release>/.claude/skills/brain-upgrade/scripts/upgrade.py plan --instance . --adopt --source <release.zip>`.
  Review and apply the adoption and commit it; then run the same `plan` without
  `--adopt` for the upgrade, its own commit. From then on, `/b:upgrade` is enough.
- **Adoption (`/b:upgrade --adopt`) brings bases without a stamp under updates,** of any
  generation, including those older than `0.1.0` that still have the pre-rename skill
  folders. Each release ships an index of every hash the template's files have had
  (`.claude/skills/brain-upgrade/known-hashes.json`), so adoption recognises unmodified
  template files from your generation and finds the nearest release. It moves those
  files forward to that release only (never back), adds the files the release has and
  your base lacks (you can deselect them), and writes the stamp, in its own commit. Your
  edits stay as they are and remain visible as edits at the next upgrade. The upgrade to
  the newest version follows as a second commit, so a large first update comes in two
  reviewable, separately revertible parts.
- **`.kb-manifest.json` holds the template version and sorts every file into a class.**
  The version (`0.1.0` until the next release) now lives only there, and `package.json`
  no longer has a `version` field. The four classes say what an update may touch:
  **owned** files (`.claude/`, hooks, workflows, config, `CHANGELOG.md`, `LICENSE`, …)
  are kept current; **seeded** files (`content/` and `README.md`) are yours once copied
  and are never written; **rendered** files (`CLAUDE.md`, `AGENTS.md`,
  `content/WRITING_STYLE.md`) come from the `*.template.md` files; **author** files
  (`openspec/`, `dev/`, `CONTRIBUTING.md`, `CLAUDE.local.md`) are for developing the
  template and never reach a base. This is the groundwork for `/b:upgrade`.

  Existing bases: nothing to do by hand; your first `/b:upgrade --adopt` brings the file in.
- **Tests run on every push to `main` and on every pull request into it.** The new
  `.github/workflows/tests.yml` runs on Linux and Windows. It runs `python
  tests/run_tests.py`, then the new `python tests/run_skill_tests.py`, which runs every
  skill's own unit tests (`.claude/skills/*/scripts/test_*.py`; `run_tests.py` runs only
  the curate and brain-upgrade suites). Last, it makes real commits to check that `.githooks/pre-commit` lets
  a commit through on the template's own tree, blocks a note without frontmatter, and
  blocks when the lint script is missing. A test that needs a tool the runner doesn't have
  is skipped and listed with its reason in the job summary, never counted as passed. Today
  that is the two `yt-dlp` integration tests in `brain-ingest`, which need the `yt-dlp`
  binary and access to YouTube. A skill suite that finds no tests fails.

  Existing bases: optional. Pull `.github/workflows/tests.yml` and
  `tests/run_skill_tests.py` to run the same checks on your base's pushes; it runs only if
  your default branch is `main`. The clean-tree hook check is skipped there, because its
  result depends on your own notes. `python tests/run_skill_tests.py` also works locally.
- **The template is now developed directly in this repository, and the rules for doing
  that live in `CONTRIBUTING.md`.** Until now this repository was a mirror: the template
  was built inside the maintainer's own base and copied here in `sync from brain@…`
  commits. From now on every change lands here first, comes with an entry in this file,
  and passes `python tests/run_tests.py` before it is committed. `CONTRIBUTING.md` also
  says which files are templates (`*.template.md`, rendered only by `/b:onboard` in your
  base) and which are starter `content/`. Claude Code loads these rules through a
  git-ignored `CLAUDE.local.md` that imports `CONTRIBUTING.md`, so they never become part
  of your base's own instructions. `.gitignore` gained a `CLAUDE.local.md` line for that.

  Existing bases: nothing to do. `CONTRIBUTING.md` is for people who develop the template;
  if your clone has it, you can delete it. The new `.gitignore` line is optional and only
  keeps a personal `CLAUDE.local.md` out of your commits.

### Fixed
- **`.claude/agents/AGENTS.md` no longer sends you to `kb-template/`.** Its rules said to
  mirror every agent change into `kb-template/.claude/agents/` and log it in
  `kb-template/CHANGELOG.md`, a folder that exists only in the maintainer's own base and
  is frozen there. The file also pointed to a note from that base
  (`AI/TOOLS/Deep-Research-skills`) and named the research skills without their `brain-`
  prefix. It now says that agents come from the template, like the skills: in the
  template repository a change to an agent gets an entry in this file, and in a base
  agents arrive with template updates.

  Existing bases: re-pull `.claude/agents/AGENTS.md`. It is documentation; the agents
  themselves are unchanged.
- **The optional `.githooks/pre-commit` lints commits again, and says so when it can't.**
  It still called `.claude/skills/lint/scripts/lint_scan.py`, the path from before the
  skills were renamed to `brain-*`, and let the commit through whenever that call failed
  (`|| exit 0`). Since the rename it passed every commit without checking anything. It
  was also not marked executable, so on Linux and macOS git skipped it with only a hint.
  The hook now calls `.claude/skills/brain-lint/scripts/lint_scan.py`, lists the notes it
  blocks on, and also blocks, with a message, when it cannot run the lint at all: no
  Python 3 on `PATH`, the script missing, a crash, or output that is not a lint report.
  `git commit --no-verify` skips it once. As before, it checks the whole `content/`
  folder, not only the staged files.

  Existing bases: only if you enabled the hook (`git config core.hooksPath .githooks`).
  Re-pull `.githooks/pre-commit` together with the `brain-lint` fix below: without it the
  hook blocks every commit on `content/_privacy.md`. On Linux or macOS, if your copy is
  not executable, run `chmod +x .githooks/pre-commit`.
- **`brain-lint` no longer reports underscore-prefixed files like `content/_privacy.md`.**
  `lint_scan.py` listed `_privacy.md` under `missing_frontmatter`, and `lint_links.py`
  listed it as an orphan, although the file is configuration, not a note. Both scripts now
  skip any `_*.md` file under `content/`, the rule `build_indexes.py` already applies (see
  the `brain-reindex` entry below). On the template's own content `/b:lint` now reports no
  issues.

  Existing bases: re-pull `.claude/skills/brain-lint/scripts/lint_scan.py` and
  `lint_links.py`. A file of yours whose name starts with `_` is no longer linted, which
  matches how `/b:reindex` already treats it; rename it if it is meant to be a note.
- **The `kb-maintain` workflow runs again.** `.github/workflows/kb-maintain.yml` still
  called `.claude/skills/reindex/…` and `.claude/skills/lint/…` after those skills were
  renamed to `brain-reindex` and `brain-lint`, so every scheduled run failed at the
  rebuild step ("can't open file") and nothing was reindexed. In this repository that was
  every Monday from 2026-07-20 on. The workflow now calls
  `brain-reindex/scripts/build_indexes.py` and `brain-lint/scripts/lint_scan.py`. Its
  comments and pull-request text, and the SessionStart hook's "no vault map yet" message,
  now name the current commands (`/b:reindex`, `/b:lint`, `/b:onboard`).

  Existing bases: re-pull `.github/workflows/kb-maintain.yml`, and
  `.claude/hooks/load_vault_map.py` for the message. The optional `.githooks/pre-commit`
  had the same stale path; it has its own entry above.
- **`brain-ingest` no longer forces every vault to English.** The "Language enforcement"
  paragraph in Phase 2 declared "the canonical vault language is **English**" and told the
  agent to translate Polish (or any other) sources on ingest — a value leaked from the
  template author's own base. Every vault onboarded from this template sets
  `{{PRIMARY_LANGUAGE}}` in `content/WRITING_STYLE.md`, so a Polish-language base would get
  its own notes silently translated into English against its stated style. The skill now
  reads the primary language from `content/WRITING_STYLE.md` instead of assuming one, and
  translates *into* that language. Its cluster-detection step no longer hardcodes
  "English/Polish stop-words" either.

  The rule now also names **both** writing-style filenames — `content/WRITING_STYLE.md`
  (what `/b:onboard` generates) and `content/WRITING_STYLE_ANALYSIS.md` (what vaults
  predating that template carry). The first pass replaced a hardcoded *language* with a
  hardcoded *filename*, which would have sent the agent to a file that does not exist in
  an older base. Naming both also keeps this skill byte-identical between `.claude/skills/`
  and `kb-template/.claude/skills/`, so `scripts/check-kb-template-drift.sh` stays quiet —
  the scripts already excluded both filenames (`build_indexes.py` `EXCLUDE_FILES`), so this
  just brings the skill in line with the rest of the codebase.

  Known remaining hardcode: `brain-research-deep` still instructs research agents that
  "all field values must be in English". That one is arguably intentional (machine-readable
  JSON), but it flows into `/b:research-report`, so a non-English vault gets an
  English report.
- **`brain-reindex` no longer indexes underscore-prefixed files like `content/_privacy.md`.**
  `_privacy.md` documents that it is "underscore-prefixed, so it is excluded from the site
  build, the indexes, and can never be packed into a bundle itself" — but `build_indexes.py`
  only skipped underscore-prefixed *directories* (`_raw/`, `_indexes/`, `_outputs/`,
  `_graveyard/`) plus three files listed by name. A loose `_*.md` was indexed, so every
  vault built from this template carried a phantom `| (root) | 1 | untyped(1) |` row in
  `vault-map.md` and a matching catalog entry for a config file. The rule now matches the
  documented convention: underscore prefix means infrastructure, not a note. The template's
  own checked-in indexes are regenerated accordingly (3 → 2 notes, which is the real count).

  Existing bases: re-pull `.claude/skills/brain-reindex/scripts/build_indexes.py` and run
  `/b:reindex`. Harmless if your vault has no loose `_*.md` under `content/`.
- **`brain-reindex` no longer destroys the `## Recent Changes` section.**
  `scripts/build_indexes.py` regenerated that section from "the 15 newest notes by
  `date:`" with a 75-character `summary:` snippet. But Recent Changes is a hand-maintained
  *change log* — "what changed and why" — which no frontmatter field records, so every
  rebuild silently replaced curated narrative with a derived listing. The script now
  preserves an existing `## Recent Changes` section verbatim and only falls back to the
  derived listing when the section is absent (fresh vault); the fallback also now emits 10
  entries, matching the "last 10 changes" contract in `AGENTS.md` instead of 15.

  If you run the scheduled `kb-maintain` workflow, this was also making **every** run
  report a substantive index diff and open a no-op PR whose only effect was clobbering
  that section. After this fix a clean vault reproduces all three indexes exactly
  (0 substantive diff), so the workflow opens a PR only on genuine drift.
- **`/research-deep` JSON validator was a silent no-op** —
  `.claude/skills/research/validate_json.py` only read the `field_categories:` /
  `category:` schema, but `/research` Step 4 emits `fields.yaml` with `categories:` /
  `name:`. On that schema the loader parsed **0 fields** and every file "passed"
  trivially (100% of nothing). The loader now accepts **both** schema styles
  (`field_categories`|`categories`, category label `category`|`name`). Second fix:
  `valid` gated only on `required` fields, and nothing was ever marked `required`, so
  even a correctly-parsed schema passed with fields missing — when a schema marks
  nothing required the validator now **treats all defined fields as required and
  enforces full coverage** (a file missing any field FAILs with exit 1). Backward
  compatible: schemas that set explicit `required:` flags keep the original gating.
  Existing bases: re-pull `.claude/skills/research/validate_json.py`.

### Changed
- **`/b:onboard` writes the template stamp and removes template-development files.**
  After rendering your instruction files it records `.kb-template.json` (the template
  version and what the template shipped), so `/b:upgrade` can later tell template files
  from your edits. It also deletes `openspec/`, `dev/` and `CONTRIBUTING.md`, which are
  only for developing the template, and it refuses to run in a checkout that has
  `CLAUDE.local.md` (the template's own source). Commit `.kb-template.json` and
  `.kb-onboard.json` with the rest of your base.

  Existing bases: nothing to do; the adoption above writes your stamp.
- **`README.md` belongs to your base.** Like the starter `content/`, it is copied once
  and then it is yours: upgrades never write it and never ask about it, and they list a
  changed template README as information only. The template's README describes the
  template; yours can describe your knowledge.

  Existing bases: nothing to do.
- **`.kb-onboard.json` is no longer git-ignored.** It holds your onboarding answers, which
  are the input for re-rendering `CLAUDE.md`, `AGENTS.md` and `content/WRITING_STYLE.md`.
  Every base checked kept it only on disk, so any other clone of the base lost it. Its
  contents (name, owner, topics, voice) already appear in your committed `AGENTS.md`.

  Existing bases: delete the `.kb-onboard.json` line from `.gitignore` and commit the
  file. An upgrade does both for you.
- **Template-development files are left out of archives.** `.gitattributes` marks
  `openspec/`, `dev/`, `CONTRIBUTING.md` and `CLAUDE.local.md` `export-ignore`, so
  "Download ZIP" and release archives no longer contain them. The lines reach your base
  with `.gitattributes`: if you ever publish your base with `git archive`, a root
  `openspec/`, `dev/` or `CONTRIBUTING.md` of your own would be left out of it.

  Existing bases: nothing to do.
- **`kb-maintain` uses current versions of its GitHub actions.**
  `.github/workflows/kb-maintain.yml` moves from `actions/checkout@v4`,
  `actions/setup-python@v5` and `actions/upload-artifact@v4`, which run on the Node 20
  runtime GitHub is retiring, to `@v7` of all three, which run on Node 24. The new
  `tests.yml` uses the same versions. What the workflow does is unchanged.

  Existing bases: re-pull `.github/workflows/kb-maintain.yml`. A self-hosted runner needs
  Actions Runner 2.327.1 or newer.
- **BREAKING: all workflow commands and skills are namespaced** — command wrappers moved
  from `.claude/commands/*.md` to `.claude/commands/b/*.md` (subdirectory = native `:`
  namespace, so `/ingest` is now `/b:ingest`), and every vault skill directory gained a
  `brain-` prefix with its frontmatter `name:` updated to match (`ingest` → `brain-ingest`).
  This stops collisions with same-named skills from installed plugins and groups the
  vault's commands in the slash menu. Skill **descriptions are unchanged**, so
  natural-language triggering ("process inbox", "health check") works exactly as before.
  The research suite also gained command wrappers (`/b:research`, `/b:research-deep`,
  `/b:research-report`, `/b:research-add-items`, `/b:research-add-fields`) — previously
  it was invocable only by bare skill name. `excalidraw-diagram` (generic utility) keeps
  its name. All cross-references in skills, scripts, docs, and the test suite's
  path constants (`tests/run_tests.py`) updated.

  | Old command | New command | Old skill | New skill |
  |---|---|---|---|
  | `/onboard` | `/b:onboard` | `onboard` | `brain-onboard` |
  | `/ingest` | `/b:ingest` | `ingest` | `brain-ingest` |
  | `/compile` | `/b:compile` | `compile` | `brain-compile` |
  | `/enhance` | `/b:enhance` | `enhance` | `brain-enhance` |
  | `/reindex` | `/b:reindex` | `reindex` | `brain-reindex` |
  | `/qa` | `/b:qa` | `qa` | `brain-qa` |
  | `/lint` | `/b:lint` | `lint` | `brain-lint` |
  | `/output` | `/b:output` | `output` | `brain-output` |
  | `/refactor` | `/b:refactor` | `refactor` | `brain-refactor` |
  | `/gaps` | `/b:gaps` | `gaps` | `brain-gaps` |
  | `/curate` | `/b:curate` | `curate` | `brain-curate` |
  | `/export` | `/b:export` | `export` | `brain-export` |
  | `/import` | `/b:import` | `import` | `brain-import` |
  | — | `/b:research` | `research` | `brain-research` |
  | — | `/b:research-deep` | `research-deep` | `brain-research-deep` |
  | — | `/b:research-report` | `research-report` | `brain-research-report` |
  | — | `/b:research-add-items` | `research-add-items` | `brain-research-add-items` |
  | — | `/b:research-add-fields` | `research-add-fields` | `brain-research-add-fields` |

  Existing bases: `git mv` your `.claude/commands/*.md` into `.claude/commands/b/`,
  `git mv` each skill dir to its `brain-*` name, update each `SKILL.md` `name:` field
  to match the new directory name, then re-pull the updated docs (README, AGENTS
  template, REFERENCE notes). Muscle-memory note: type `/b:` and tab-complete.
- **`web-search-agent` no longer hard-depends on a Unix `date` call** — step 0 ("Get
  Current Date") ran `date +%Y-%m-%d`, which errors in a PowerShell-only environment
  (`date` is a `Get-Date` alias that rejects `+%Y-%m-%d`). It now takes today's date from
  the harness-injected context (no shell call), and only falls back to a tool call —
  Bash `date +%Y-%m-%d` or PowerShell `Get-Date -Format yyyy-MM-dd` — if the date is
  genuinely unavailable. Shell-agnostic; the failure was cosmetic (date is only used to
  filter "recent" results) but this removes it. Existing bases: re-pull
  `.claude/agents/web-search-agent.md`.

## [0.1.0] - 2026-07-13

First tagged release of the second-brain template.

### Fixed
- **`/lint` link scanner no longer false-flags escaped-pipe aliases** —
  `.claude/skills/lint/scripts/lint_links.py` split link targets on `|` but not on the
  table-escaped `\|`, so `[[Note\|alias]]` resolved to `Note\` and was reported broken.
  Now normalizes `\|`→`|` before splitting. Also treats `.webp` as an asset embed (was
  flagged broken). Cut ~7 false positives on a ~360-note vault. The lint `SKILL.md` now
  points at the two canonical scanners (`lint_scan.py`, `lint_links.py`) so runs use them
  instead of ad-hoc greps, and reminds the operator to triage raw broken-link counts.
  Existing bases: re-pull `.claude/skills/lint/`.
- **Non-Latin vaults** — forced UTF-8 stdout so `/lint`, `/gaps`, and `/refactor` no longer
  crash on non-ASCII content (e.g. Polish); `build_indexes.py` writes UTF-8 too.
- **`/lint` false positives** — `lint_scan` now parses block-style YAML tag lists, so notes
  using multi-line `tags:` no longer report a spurious `missing_tags`.

### Changed
- **`/qa` cites chat answers as percent-encoded markdown links** — instead of
  `[[wikilinks]]`, the Q&A skill now emits `[Title](content/…%20path.md)` links that are
  clickable in Claude Desktop and VS Code markdown preview (saved answer-notes still use
  `[[wikilinks]]` for Obsidian/graph). Existing bases: re-pull `.claude/skills/qa/`.
- **Single source of truth for agent instructions.** `AGENTS.md` is now the canonical
  file that holds all project instructions (role, navigation protocol, writing style,
  frontmatter, workflows, safety). `CLAUDE.md` is reduced to a thin pointer that imports
  `AGENTS.md` via the `@AGENTS.md` line, so Claude Code and any `AGENTS.md`-reading agent
  (Codex, Gemini CLI, OpenCode) all follow **one** file. Previously the content lived in
  `CLAUDE.md` and `AGENTS.md` was a short mirror — the two could drift.
  - **Migration (existing bases):** move your instruction body from `CLAUDE.md` into
    `AGENTS.md`, then replace `CLAUDE.md` with a pointer whose last line is `@AGENTS.md`.
    Fresh clones get this automatically from the updated templates via `/onboard`.
  - `onboard` still renders and personalizes both files; no action needed for new setups.
- **README** — clearer positioning: the base as an LLM Wiki (Karpathy) that is portable
  via the OKF standard, with the index-first "why it scales without embeddings" explainer.

### Added
- **YT ingest supports an alternate yt-dlp `player_client`** — `ingest/scripts/yt_fetch.py`
  now threads an optional `player_client` through metadata + caption fetching
  (`--extractor-args youtube:player_client=…`), a workaround for when the default client is
  throttled or blocked. Existing bases: re-pull `.claude/skills/ingest/scripts/`.
- **Research skill suite now ships its `web-search-agent` dependency** — the `/research`
  → `/research-deep` → `/research-report` pipeline dispatches a `web-search-agent`
  sub-agent that was never bundled, so the deep phase silently fell back to generic web
  search. Added `.claude/agents/web-search-agent.md` + `.claude/agents/web-search-modules/`
  (5 routing modules: general-web, github-debug, stackoverflow, academic-papers,
  chinese-tech), vendored from the upstream **Weizhena/Deep-Research-skills** (MIT) this
  suite was adapted from. Also fixed two hardcoded home-dir paths that assumed a global
  `~/.claude` install: `research-deep` now runs
  `python .claude/skills/research/validate_json.py` (was `~/.claude/skills/…`) and the
  agent loads modules from `.claude/agents/web-search-modules/` (was `~/.claude/agents/…`)
  — both project-relative so a cloned template works without a global install. Removed a
  machine-specific project-root path from `research/SKILL.md` (now "the vault/project
  root"). Existing bases: pull `.claude/agents/` and re-pull `.claude/skills/research-deep/`
  + `.claude/skills/research/`.
- **Export privacy levels: `/export --public` redaction pipeline** — bundles that leave
  your trust boundary (shared with strangers, published openly) can now be scrubbed of
  private data. Default level stays exactly as before (verbatim, 2 prompts, read-only).
  `--public` adds: a category redaction policy (always cut secrets, third-party PII,
  health, finance, rates; genericize personal/commercial context; keep tools/howtos/
  technical opinions) tunable per vault via a new optional `content/_privacy.md`
  (commented example ships with the template); one approvable verdict table
  (include/redact/exclude per note, full diff on demand — 3rd and normally last prompt);
  two post-redaction safety nets (`privacy_sweep.py` deterministic pattern scan for
  emails/phones/IBAN/cards/API-keys/JWT/wallets + a fresh-context adversarial LLM audit);
  wikilink de-personalization (`[[My Crypto Strategy]]` → `[[Crypto Strategy]]`, person-name
  titles genericized) — and writes a local redaction report to `_outputs/reports/`.
  The shipped bundle deliberately carries **no redaction trace** (manifest unchanged,
  format still 1) — the local report is the only record. Also fixes `bundle.py` exclusion:
  underscore-prefixed **files** (e.g. `_privacy.md`) can no longer be packed at any level.
  Existing bases: pull `.claude/skills/export/` (SKILL.md + `bundle.py` +
  `privacy_sweep.py` + tests) and optionally `content/_privacy.md`.
- **Note-bundle transfer: `/export` + `/import` skills** — move sets of notes between
  any two template-based knowledge bases. `/export` (new skill + command) resolves a
  selection (wikilink list, `#tag`, or folder), confirms it, offers depth-1 linked
  neighbors, and packs verbatim note copies into a `brain-pack-*.zip` with a
  `manifest.json` (format `1`, source base name, export date, per-note sha256) — fully
  read-only for the vault. `/import` (new skill + command) validates the bundle before
  any write (format/hash checks), auto-skips byte-identical notes (idempotent re-import),
  triages collisions in a single approve-or-edit table (skip/merge/keep-target/rename),
  maps notes from missing source folders onto the target vault's own taxonomy in a second
  single table (never seeds foreign folder structures unasked), stamps
  `imported-from`/`imported` provenance frontmatter, leaves broken wikilinks intact for
  later re-stitching, batch-updates all 3 indexes, and writes a report to
  `_outputs/reports/` — hard budget of at most 2 user prompts per run, regardless of
  bundle size. Deterministic mechanics live in `export/scripts/bundle.py`
  (`pack`/`unpack`/`same`, stdlib-only Python, tests included). Existing bases: pull
  `.claude/skills/export/`, `.claude/skills/import/`, `.claude/commands/export.md`,
  `.claude/commands/import.md`, and add the two Workflows rows to your `AGENTS.md`.
- **"Works beyond Claude Code" docs** — the template now documents that it runs *outside*
  Claude Code, with **no terminal and no git commands**. Three doc-only additions: a new
  README section listing the supported tools (Claude Desktop Code tab, GitHub Copilot,
  Codex, Cursor, Antigravity) and how to run commands / save changes in each; a note in
  `AGENTS.template.md` explaining which tool reads `AGENTS.md` vs `CLAUDE.md` and why the
  `@AGENTS.md` import keeps one source of truth; and a new **`ENVIRONMENTS.md`** carrying
  the full verified tool-by-tool matrix (file access, native vs conversational commands,
  git-without-commands, which instruction file each tool reads). No skill or
  generation-logic changes. Existing bases: pull `ENVIRONMENTS.md` and add the
  README / `AGENTS.md` paragraphs if you want the same guidance (your rendered `AGENTS.md`
  predates the note — paste it in by hand).
- **`LICENSE` (MIT)** — the template now ships an explicit MIT license, so forks have
  real permission to use, modify, and redistribute it. Without a license file a public
  repo defaults to "all rights reserved," which silently contradicted the "git clone and
  it's yours" invitation. Also adds a **License** section to the README. Existing bases:
  pull `LICENSE` if you intend to republish or share your clone.
- **Scheduled maintenance workflow** (`.github/workflows/kb-maintain.yml`) — an optional
  GitHub Action that keeps navigation fresh without anyone remembering to run `/reindex`.
  Weekly (and on-demand via the Actions tab) it rebuilds `content/_indexes/` and runs the
  lint scanner, then opens **one** pull request only if the rebuild changed the indexes in
  substance — a restamped `updated:` timestamp alone never triggers a PR. It never edits
  your notes; the only writes are to `_indexes/`, via a PR you review. Encodes OpenWiki's
  "doc drift is a CI problem, not a discipline problem" idea. Delete the file to opt out.
  - **Enable it:** it runs automatically once the file is on your default branch. Under
    **Settings → Actions → General**, allow workflows to *"Read and write"* and to
    *"create and approve pull requests"* so the bot can open the maintenance PR.
- **`/curate` skill** — vault hygiene: scores notes for staleness, isolation, dead links,
  and duplication; proposes archive/merge/refresh; retires confirmed notes to
  `content/_graveyard/` (reversible — never `git rm`, gated on your confirmation).
- **`content/_graveyard/`** — holding folder for retired notes, excluded from the indexes.
- **This `CHANGELOG.md`** — from now on every template change is recorded here.

---

_Older history predates this changelog. From here on, every change to the template is
recorded above._
