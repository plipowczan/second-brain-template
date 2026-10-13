---
name: brain-upgrade
description: Use when the user says "upgrade", "update the template", "pull template updates", "zaktualizuj szablon", "aktualizacja bazy", or asks which template version this base runs. Pulls a newer release of the knowledge-base template into this base — dry run first, one review table, then apply and one commit. A base without a `.kb-template.json` stamp is adopted first (`--adopt`), in its own commit. Never touches notes in `content/`.
---

# UPGRADE

Brings template improvements (skills, hooks, workflows, docs) into this base. The engine
is `scripts/upgrade.py` (Python standard library only, no git required). The scripts
make every decision that can be computed; you drive the order and talk to the owner.

## Rules

- **Consent before code runs.** The engine of a downloaded or named source is code from
  that source. Show the owner where it comes from and get an explicit yes before running
  it (Phase 1, step 5). No yes, nothing runs.
- **Dry run first.** Nothing in the base changes until the owner approves a plan.
- **Run the engine of the version being installed**, not this base's copy: the new
  version knows its own layout. The engine is `<source>/.claude/skills/brain-upgrade/scripts/upgrade.py`.
- **Notes are never touched.** Nothing under `content/` is written, except
  `content/WRITING_STYLE.md` when the owner asks for its re-render.
- **One commit per cycle.** An adoption and the upgrade after it are two commits.
- **One review table per cycle**, the same approve-or-edit form as `/b:import`. Ask
  per file only for merges.
- Plans and decision files go to the temp directory or your scratchpad, never into the
  base.

## Phase 1 — The source, its provenance and the owner's consent

Run `fetch` with **this base's own copy** of the engine: it only reads and unpacks, and
it reports where the source comes from before any code from the source runs.

1. **The owner named a source** (a clone of the template, an unpacked release, or a
   release `.zip`):
   `python .claude/skills/brain-upgrade/scripts/upgrade.py fetch --source <folder or zip>`.
   `SOURCE=<folder or zip>` (a zip carries the release commit).
2. **No source named:** download the latest release (or `--to X.Y.Z`):
   `python .claude/skills/brain-upgrade/scripts/upgrade.py fetch [--to X.Y.Z]`.
   `SOURCE=<source.archive>`. Tell the owner the archive path: passing it as the source
   later works offline.
3. `fetch` stops when there is no network. Say so, and ask for a release `.zip` or a
   local clone. Nothing has changed.
4. If `engine_exists` is false, the source is older than `0.2.0` and cannot upgrade a
   base. Stop. Otherwise `ENGINE=<engine>` from the JSON.
5. **Provenance and consent.** Show the owner the `provenance` block in plain words:
   - repository, version, tag (or "not a tagged release"), commit (or "commit unknown":
     the source cannot prove which commit it is);
   - where it came from (`from`: the download URL or the path they gave), and `verified`:
     what this base's engine itself established. Only one thing counts: an HTTPS
     download of that repository's tag from GitHub;
   - every line of `warnings`, in plain words.

   `fetch` itself stops in two cases, says why, and unpacks nothing:
   - **another repository** than the base's stamp names: tell the owner outright that
     this base follows that repository, the source is another one, and upgrading from it
     replaces the template files with that repository's;
   - **an unverified source** (`verified` is null: a folder, a zip, or a local clone,
     whatever its origin remote says): it only claims its repository
     (`claimed_repository`) and commit, and nothing proves them; say exactly that.

   Only if the owner accepts it, run `fetch` again with `--allow-repository <the
   repository it names>`, and pass the same option to `plan` in Phase 3.

   Ask: *"Run the upgrade tool from this source?"* Only an explicit yes goes on; anything
   else ends here, with nothing run and nothing changed.

A base that does not have this skill yet: see **Bootstrap** below.

## Phase 2 — Adopt or upgrade

- No `.kb-template.json` in the base root → run the cycle below with `--adopt` first.
  Adoption aligns the base with the nearest template release R and writes the stamp.
  Then offer the upgrade from R as a second cycle.
- A stamp exists → one upgrade cycle. Never pass `--adopt`.

## Phase 3 — Plan (the dry run)

```bash
python ENGINE plan --instance . --source SOURCE            # upgrade
python ENGINE plan --instance . --source SOURCE --adopt    # adoption
```

Add `--allow-repository <repository>` only when the owner agreed to switch repository in
Phase 1.

Add `--rerender` when the owner wants `CLAUDE.md`, `AGENTS.md` and
`content/WRITING_STYLE.md` refreshed from the new templates. Add `--diff <path>` or
`--diff all` to see changes; the plan is read-only, so re-running it is safe. An
adoption that is offline and needs an older release stops and names it; ask for that
release's `.zip` and add `--base <zip>`.

Read the summary and the plan file it names (`Plan: …`). If it says **Up to date**,
report that and stop.

## Phase 4 — One review table

Show the owner, in one message:

1. The version range and the `CHANGELOG.md` entries from the summary, **BREAKING**
   entries first, each with its "Existing bases" note.
2. Any warnings (not a release, untracked `.kb-onboard.json`, uncommitted files).
3. One table of the actions: path, action, default (`[x]`/`[ ]`), note. Group them by
   action. Up-to-date files are a count, not rows.
4. The decisions that need an answer, with defaults:
   - each **CONFLICT** (changed in the template and in this base): keep, overwrite or
     merge;
   - **restore?** rows (files the owner deleted): default stays deleted;
   - unchecked **delete** rows (edited files the template removed): default keep;
   - instruction files: re-render untouched ones? (default no);
   - **QUESTION** lines: a value for each new placeholder.
5. Seeded changes (starter content and `README.md` upstream) as information only.

The owner approves, edits defaults, or rejects. A rejection ends the cycle: nothing was
written.

## Phase 5 — Apply

Write the decisions to a JSON file outside the base:

```json
{
  "actions": {"path/of/file": true, "other/file": false, "conflicting/file": "merge"},
  "rerender": ["AGENTS.md"],
  "values": {"NEW_PLACEHOLDER": "the owner's answer"}
}
```

Selectable rows take `true`/`false`; conflicts take `"keep"`, `"overwrite"` or
`"merge"`; rows you leave out keep their default. `rerender` is a list of paths or
`true` for all; `values` are saved to `.kb-onboard.json`.

```bash
python ENGINE apply --plan PLAN --decisions DECISIONS
```

`apply` checks every planned file first and writes nothing if one changed since the
dry run (run the plan again), if a planned file has uncommitted work (ask the owner to
commit or stash it), or if a conflict has no choice. Without git it backs up every file
it replaces or deletes to `.kb-upgrade-backup/<version>-<time>/` and names the folder.

## Phase 6 — Merges

For each file `apply` lists as waiting for a merge: show the diff
(`plan … --diff <path>` from a fresh dry run is fine, or compare with the plan's
`payload/src/<path>`) and the `CHANGELOG.md` entry, then edit the file together with the
owner. The scripts never merge on their own.

## Phase 7 — Commit and follow-up

```bash
python ENGINE commit --plan PLAN
```

It stages only the applied files, the stamp and `.kb-onboard.json` (when it becomes
tracked) and makes one commit: `chore(template): adopt <repo> <R>` or
`chore(template): upgrade to <repo> <version>`. Other uncommitted work stays as it was.
Without git it reports the backup folder instead.

Then:

- walk the owner through each **BREAKING** entry's migration steps;
- run what the entries ask for, typically `/b:reindex`;
- after an adoption, offer the upgrade cycle (Phase 3 without `--adopt`).

## Bootstrap: a base without this skill

Bases created before `0.2.0` have neither this skill nor a stamp. Run the release's
engine directly against the base:

1. Get the release: a local clone of the template, or the release `.zip` from the
   repository's Releases page ("Source code (zip)"). The agent can download it with
   Python if the owner has no browser at hand:
   `python -c "import urllib.request as u; u.urlretrieve('https://github.com/plipowczan/second-brain-template/archive/refs/tags/vX.Y.Z.zip', 'kb-template.zip')"`
   (save it outside the base).
2. **Provenance and consent first.** The base has no engine to run `fetch`, so read the
   facts without running anything from the release: for a zip,
   `python -c "import json,sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); m=[n for n in z.namelist() if n.count('/')==1 and n.endswith('/.kb-manifest.json')][0]; d=json.loads(z.read(m)); print(d['repository'], d['version'], z.comment.decode() or 'commit unknown')" <zip>`
   (for a clone: `git -C <clone> describe --tags` and `git -C <clone> rev-parse HEAD`,
   and the repository from its `.kb-manifest.json`). Show the owner the repository,
   version, tag, commit and where it came from, as in Phase 1 step 5, and ask for an
   explicit yes. No yes, stop.
3. Unpack it outside the base and follow **that copy** of this file, with
   `ENGINE=<unpacked>/.claude/skills/brain-upgrade/scripts/upgrade.py` and
   `SOURCE=<zip or clone>`, starting at Phase 2 (`--adopt`).
4. The adoption commit brings this skill into the base; later upgrades start at Phase 1.

## What you trust

The trust anchor is the template repository on GitHub, reached over HTTPS: the one in the
base's stamp (`plipowczan/second-brain-template` by default). The upgrade tool you run is
code from the same source as the skills and hooks it installs, which run in every
session after the upgrade anyway. Releases are not signed; that is a deliberate decision
(2026-10-13). What protects the owner is seeing the provenance and agreeing before
anything from the source runs, the dry run, and one reviewable commit.

## Without a terminal

Every step is a command the agent runs for the owner. In tools without native
`/slash` commands, ask: *"follow `.claude/skills/brain-upgrade/SKILL.md`"*. Without git,
the backup folder is the way back; with git, `git revert` of the upgrade commit (or of
the adoption commit) undoes it.
