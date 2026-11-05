# Design

## Context

The pilot (2026-11-04, `v0.2.1`) adopted and upgraded `second-brain-demo-recipes` and a
copy of a base built from `v0.1.0`. Notes stayed intact and local tests stayed green. The
defects are in the path around that result. Bug numbers below are those of the report
(`agentic-ai-private: context/plsoft/projects/BRAIN/data/pilot-aktualizacji-0-2-1.md`).

Four facts shape the decisions:

- `fetch` runs with the base's own engine and is the real gate. `plan` runs from the source
  and is the second line of defence (review rounds R5-1, R7-1, R8-1 of
  `add-template-updates`). Round R7 removed origin-based verification so that only an
  HTTPS download this engine made itself counts as verified. That rule stays.
- A base on `0.2.x` follows **its own** `SKILL.md` until the upgrade replaces it, while
  `plan`, `apply` and `commit` come from the release being installed. A fix in `SKILL.md`
  reaches such a base one run late. A fix in the engine or in its messages reaches it at once.
- The published archive carries the executable bit, but only one way. In `v0.2.1`,
  `.githooks/pre-commit` has `external_attr` `0o100755`, and `LICENSE` has `0o0` with
  `create_system` 0, the same as a zip with no mode information at all.
- On Windows the file on disk has no executable bit. There, the only truth is the mode in
  git.

## Goals / Non-Goals

**Goals:** the default path runs from the skill's own commands without a flag; a foreign
zip without consent is still refused; an old base stops showing removed commands; no red
test after the first push; the docs describe what really happens.

**Non-Goals:** bugs 7-11 (`PL-665`, `0.4.0`); release signatures (decided 2026-10-13);
new commands; rewriting the rest of the skill; taking an executable bit away; changing
the base `second-brain-demo-recipes`.

## Decisions

### D1. The default path: `plan` downloads the release itself (bug 1)

**To decide per the brief.** `fetch` verifies a download, then the skill passes the saved
archive to `plan --source`, and `plan` treats every zip as unverified.

**Decision.** The default path no longer hands the archive back.

```bash
python .claude/skills/brain-upgrade/scripts/upgrade.py fetch [--to X.Y.Z]   # the gate
python ENGINE plan --instance . --to VERSION                                # VERSION from fetch
```

- `--to VERSION` pins the plan to the version the owner agreed to, not to whatever is
  latest a minute later. This is the code path `plan` already has
  (`sources.resolve(None, to=…)`, kind `download`, `verified` set), so the gate logic
  does not change at all.
- The skill compares the commit the plan prints with the commit the owner saw in Phase 1
  and stops if they differ. Tags are never moved, so this should never fire. It closes
  the gap between what was approved and what was planned, for the price of one sentence.
- **Bootstrap takes the same road:** `plan --instance . --to X.Y.Z --adopt`. The zip only
  supplies the engine. A zip or clone the owner names, for example offline, stays the
  consent path: the agent adds `--allow-repository` on the owner's yes from step 2.
- The rule stays as R7 left it: only a download this process made counts. The archive
  `fetch` saved is, from then on, a plain zip. It can still be reused offline, as a named
  source with the owner's consent. The skill says so.

**The rejected options:**

| Option | Foreign zip with a planted record | Cost | Verdict |
|---|---|---|---|
| Record next to the archive: hash and "verified" (pilot's proposal) | **Passes.** Whoever hands over the zip hands over the record, and the hash matches because it is computed from that zip | A new file format and new trust code | Rejected: it fails the brief's own condition |
| The same record keyed with a per-user secret | Refused | Key storage on every machine | Rejected: far too much for one line in a skill |
| `plan --source <zip>` downloads the tag again and compares the trees | Refused | The same second download, plus a second route through the gate | Rejected: its only gain is D1a below, and a gate should have one route |
| `plan --to VERSION` | Refused: nothing on disk is consulted | One more download (about 260 kB) and one changed line in Phase 3 | **Chosen** |

The brief asks for no change to the skill's syntax. `/b:upgrade` and every engine option
stay as they are. What changes is the default line in Phase 3 and the Bootstrap step.

**D1a. Bases on `0.2.x` read the old line.** Their `SKILL.md` still says
`plan --source <archive>`, and the new engine refuses that. So the refusal itself carries
the way out: to have the release verified, drop `--source` and add `--to <version>`. It
names the repository it will download from, and it appears only when the zip claims the
base's own repository. The agent reads it and retries, so such a base sees one refused
command on its first run and none after that. Bases from before `0.2.0` go through
Bootstrap, which follows the new release's text, so they never see it. `CHANGELOG.md` says this.

### D2. `AGENTS.md` after a breaking release (bug 2)

**Decision.** `plan_upgrade` looks for an entry marked breaking in the changelog range. If
there is one, the `AGENTS.md` entry starts as requested. The test of "untouched" stays:
the local file must match the stamp's output hash.

- `requested` becomes per file. `--rerender` still requests all three.
- `content/WRITING_STYLE.md` is never requested by default, which keeps the mail's promise
  about notes. `CLAUDE.md` holds only the import of `AGENTS.md`, so it stays on request too.
- An edited file stays a proposal, as it does today.
- The owner can say no: `"rerender": []` in the decisions. The plan says why the file is
  being rewritten, and the Phase 4 table shows it with a default of yes.
- A new placeholder without a value now stops `apply` until it is answered, because the
  re-render is requested. The QUESTION line already asks for it, and "nothing was written"
  holds.
- Adoption never writes rendered files. That rule is unchanged.

Phase 7 of the skill reminds the owner that `README.md` is theirs, so it keeps the old
names and the engine never touches it.

**Known limit.** This reaches only a base whose `AGENTS.md` is provably untouched. A base
adopted at `0.2.0` from an older rendering has `output_hash: null`, so it gets a proposal.
A base already past the breaking entry with a stale file (today only the demo base) has
no such entry in its range, so it needs `--rerender`. Comparing against older templates
would need rendered files in the history index, which is too much for this change.

### D3. Executable files: one list in the manifest (bug 12)

**To decide per the brief:** where the mode comes from, and what happens to an owner's file.

**Decision: where it comes from.** `.kb-manifest.json` gets a top-level list:

```json
"executable": [".githooks/pre-commit"]
```

The engine reads the bit from this list for every kind of source, and from nowhere else.

| Option | Clone or folder on Windows | Verdict |
|---|---|---|
| `external_attr` in the zip, tar mode from a clone, `stat` on a folder | Folder has nothing; needs a fallback anyway | Rejected: three readers and two truths. A zip rebuilt by another tool shows `0o0`, which reads the same as "not executable" |
| The `executable` list | Same answer everywhere | **Chosen** |

- `dev/check_manifest.py` compares the list with the `100755` entries in the git index, in
  both directions, so a forgotten file fails the tests.
- The list is checked like every other path in the manifest. A protected path (`content/`,
  `README.md`, the stamp) stops the source. Only files the source ships as owned count.
- An engine older than this change ignores the key.

**What the plan compares.** Hashes stay as they are, because the bit is not content. For
each listed file that exists locally, the engine reads its current state: the mode in
`HEAD` when git tracks it, otherwise `stat` on Linux and macOS. On Windows without git
there is no bit to read, so nothing is planned.

- A missing bit gets a row in a new plan section, `Executable bit`. It is not an action
  row, so `keep (yours)`, `update` and `conflict` mean what they meant.
- Rows count as pending. A base already past an update, with equal content, is not "up to
  date" until the bit is set. A row also goes through the stale and uncommitted-work checks.
- The decisions file takes `"executable": true`, `false` or a list of paths, the same shape
  as `rerender`.

**Decision: the owner's file.** The text stays and the bit moves. The row is selected by
default, and the owner can deselect it. The content row stays `keep (yours)`.

- The bit is not the owner's edit. Without it git on Linux and macOS skips the hook, edited
  or not, and `tests.yml` goes red on every push, which is the defect being fixed.
- The stamp has no baseline for the bit, so a deliberate `chmod -x` looks the same as a
  base that never had it. That is why the row is a question with a default and not a silent
  write. A declined row comes back on the next run.

**Only one direction.** The engine adds the bit to listed files and never removes one. An
owner's `chmod +x` on another file is harmless, and nothing in the template needs the
opposite move.

**Writing it.**

- `_write` keeps the bits of the file it replaces. Today it writes a temp file and renames
  it, so on Linux and macOS an update drops a bit the file already had, and `git status`
  shows a mode change. This is a second bug behind the same symptom.
- A listed file gets the bit on any write (`add`, `update`, `restore`, a conflict
  overwritten), unless the owner declined it. A bit-only row rewrites the same bytes through
  the same journaled step.
- The rollback journal records the bit and puts it back. Today's early exit for "content
  unchanged" would otherwise leave it set.
- `build_commit_index` takes the modes `apply` recorded, on top of the modes from `HEAD`,
  and a new listed file gets `100755` instead of `100644`.

**Adoption** does the same, using the list from the source. It must: adoption can bring in
`tests.yml`, which checks the hook. For R = `0.1.0` the hook gets a bit that release did not
have, which is harmless and forward only. Such an adoption commit may now hold one mode
change instead of no files.

### D4. A line for edits that do not follow a rename (bug 5)

**Decision.** For a `delete` row left unselected because the file was edited, the planner
looks for the file's new name among the paths the source ships and the stamp does not.
Two paths match when they have the same file name and differ in one way: one folder gained
a prefix (`skills/lint/` to `skills/brain-lint/`), or one folder was inserted
(`commands/lint.md` to `commands/b/lint.md`). Those are the shapes of the `0.2.0` rename.

The summary gets its own section, and the skill walks the owner through it:

```text
Renamed by the template (your edits stay at the old name and do not move):
  .claude/skills/lint/SKILL.md -> .claude/skills/brain-lint/SKILL.md
```

The match only produces a message and never changes what is written, so a wrong guess costs
one misleading line. That is why a rule of a few lines is enough. A `renamed` map in the
manifest would be more exact, but it is 30-odd entries to maintain for a message.

### D5. Undoing (bugs 3 and 4) and Bootstrap (bug 6)

Documentation only, in `SKILL.md` and `README.md`:

- Undo the newest commit first: the upgrade, then the adoption. Reverting the adoption
  alone conflicts.
- Reverting an adoption that added `.kb-onboard.json` removes the file from disk, and the
  `.gitignore` entry stays. The way back: `git restore --source=<adoption> -- .kb-onboard.json`.
  The brief names `git show <adoption>:.kb-onboard.json`. `git restore` is the same recovery
  without redirecting output, which in Windows PowerShell 5.1 would rewrite the file's
  encoding.
- Bootstrap step 4 becomes conditional: at R of `0.2.0` or newer the adoption commit brings
  the skill. Below that it arrives with the upgrade commit, so run that cycle with the same
  engine.

### D6. `yt_fetch.py`: both reports confirmed, both small

- **The original URL goes to yt-dlp. Confirmed.** `normalize_url` keeps out other hosts and
  anything starting with `-`, so there is no option injection, and `subprocess` uses a list.
  But the check and the fetch can disagree: `?v=A&v=B` is checked as A, `&list=…` is passed on
  with no `--no-playlist`, and `/redirect?q=…&v=…` passes. **Fix:** `process_url` builds
  `https://www.youtube.com/watch?v=<id>` from the validated id and uses it everywhere.
- **`python -m yt_dlp` imports from the current folder. Confirmed by running it:** a
  `yt_dlp.py` in the working directory ran instead of the module, and `python -P -m yt_dlp`
  ignored it. The agent runs from the base root, so a file planted in a base or a cloned
  folder runs. **Fix:** start yt-dlp with the current folder off `sys.path`. `-P` needs
  Python 3.11, and the template names no minimum, so the fallback command becomes a short
  `python -c` that drops `sys.path[0]` and runs the module with `runpy`. It behaves the same
  on every version, so one test covers it. Signed `python.exe` stays the executable, so the
  Smart App Control fix holds.

### D7. README

`README.md` is seeded, so this reaches only new clones. The "~500 sources" figure goes. The
course link goes where PR #2 put it, with the address `https://lipowczan.pl/llm-wiki/kurs`.

### D8. Tests

New suite `.claude/skills/brain-upgrade/scripts/test_skill_path.py`, which keeps away from
the parts of `tests/run_tests.py` that PR #11 changes. `tests/run_tests.py` runs it with
the rest of the unit suites, on Linux and Windows.

- **The skill's own commands.** The test reads the fenced lines of Phase 3 from `SKILL.md`
  and runs them with a stub opener: `fetch`, `plan`, `apply`, `commit`. A flag added to the
  skill later fails the test, which is the gap `tests/run_tests.py:72` left open.
- **Refusals.** A foreign zip at `fetch` and at `plan`; the same zip with a plausible record
  next to it; the archive `fetch` saved, passed back without consent.
- **Rendering.** The default re-render with a breaking entry, none without one, an edited
  file as a proposal, `WRITING_STYLE.md` untouched, `"rerender": []` honoured.
- **Modes.** Both checks read `git ls-tree`, so they run on Windows too: a `100644` base gets
  `100755` with equal content; an added file gets the bit; an edited file stays
  `keep (yours)`, gets the bit, and can decline it; `git status` stays clean; rollback puts
  the bit back. Disk modes run on Linux only, under `skipUnless`, so CI is what covers them.

## Risks / Trade-offs

- **A second download.** `plan` needs the network right after `fetch` did. If it fails, the
  message says how to pass the zip, with consent. Accepted.
- **One refused command on `0.2.x` bases** (D1a). Accepted: the alternative is a second route
  through the gate.
- **A hook that was silently skipped starts to run** on Linux and macOS, for an owner who
  enabled `core.hooksPath`. That is the point of the fix, and the plan shows the row. The
  `CHANGELOG.md` entry says so.
- **The word `BREAKING` in a first line now rewrites a file.** It used to change only the
  display. Our own entries must not use the capitalised word unless they mean it, and this
  change's entry avoids it.
- **The rename line can be wrong.** It only informs (D4).

## Migration Plan

Nothing to migrate by hand for the engine. The `CHANGELOG.md` entry's "Existing bases"
paragraph says what a base gets alone (the bit, an untouched `AGENTS.md`, the new plan
lines) and what stays with the owner (`README.md`, an edited `AGENTS.md`, the one refused
command on `0.2.x`). Rollback of this change: revert the PR. The manifest key is ignored by
older engines.

## Open Questions

For Paweł, before code:

1. **D1:** one line in Phase 3 and the Bootstrap step change, and the engine's options do
   not. Is that within "no change to the skill's syntax"?
2. **D3:** on an edited file the bit moves by default and the owner can decline. The
   alternative is to leave it, and accept a red test for those owners.
3. **D5:** `git restore` in place of the brief's `git show`.
