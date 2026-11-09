# Proposal

## Why

The pilot of `/b:upgrade` on `second-brain-demo-recipes` (2026-11-04, release `v0.2.1`)
kept the owner's notes intact and left the tests green, but the path it walked is not
ready for the mail that sends every owner down it. The command the skill prescribes is
refused, the agent keeps reading command names that no longer exist, and GitHub sends a
red test notification after the first push. These fixes ship before the `v0.3.0` tag, so
that release is the first one owners are pointed at.

## What Changes

Bug numbers are those of the pilot report.

- **The default path works without a flag (bug 1).** After `fetch`, the skill runs `plan`
  with `--to <version>` and no `--source`, so the engine downloads and verifies the
  release itself. A file on disk is still unverified, whoever saved it. A foreign zip
  without the owner's consent stays refused. No record next to the archive is introduced.
- **`AGENTS.md` follows a breaking release (bug 2).** When the update range holds a
  **BREAKING** entry, an untouched `AGENTS.md` is re-rendered by default. An edited one
  stays a proposal. `content/WRITING_STYLE.md` and `CLAUDE.md` still move only on request.
  Phase 7 reminds the owner that their `README.md` keeps the old names.
- **The executable bit reaches the base (bug 12).** A new `executable` list in
  `.kb-manifest.json` names the files a release ships as executable. The plan compares the
  bit as well as the content, `apply` sets it on disk, and `commit` records `100755`, so a
  base that already went through an update heals too.
- **Skill and README tell the truth about undoing (bugs 3 and 4).** The order of reverts,
  and what reverting an adoption does to `.kb-onboard.json`.
- **The plan says when an edit does not follow a rename (bug 5).** An edited file at an
  old path gets its own line that names the new path.
- **Bootstrap stops promising the skill after adoption (bug 6).** It arrives with the
  adoption only for a nearest release of `0.2.0` or newer.
- **`yt_fetch.py`: two confirmed reports are fixed.** yt-dlp gets the canonical URL, and
  `python -m yt_dlp` no longer imports from the current folder.
- **README.** The unconfirmed "~500 sources" figure goes, and the course link comes in.

No new commands. No breaking change: the engine's options stay as they are.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `template-upgrade`: the default path and what counts as verified; the default re-render
  of `AGENTS.md`; executable files; edited files at renamed paths.
- `template-manifest`: the `executable` list and its check.
- `template-adoption`: adoption carries executable bits too.

## Impact

- **Code:** `.claude/skills/brain-upgrade/scripts/` (`upgrade.py`, `planner.py`,
  `kbtemplate.py`, tests), `.claude/skills/brain-ingest/scripts/` (`yt_fetch.py`, tests),
  `dev/check_manifest.py`.
- **Docs:** `.claude/skills/brain-upgrade/SKILL.md`, `README.md`, `CONTRIBUTING.md`,
  `CHANGELOG.md`.
- **Data:** `.kb-manifest.json` gains `executable`. An engine older than this change
  ignores the key.
- **Existing bases:** the fixes arrive with the first upgrade to a release that contains
  them, because the engine of the release being installed does the work. A base on `0.2.0`
  or `0.2.1` follows its own older `SKILL.md` for that one run: see design D1.
- **Other work:** PR #11 touches `.kb-manifest.json`, `CHANGELOG.md`, `README.md`,
  `CONTRIBUTING.md` and `tests/run_tests.py` in other places. New tests go into a new
  file to keep the overlap small. PR #2 becomes redundant.
