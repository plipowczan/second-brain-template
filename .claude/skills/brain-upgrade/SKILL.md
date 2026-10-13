---
name: brain-upgrade
description: Use when the user says "upgrade", "update the template", "pull template updates", "zaktualizuj szablon", "aktualizacja bazy", or asks which template version this base runs. Pulls a newer release of the knowledge-base template into this base — dry run first, one review table, then apply and one commit. A base without a `.kb-template.json` stamp is adopted first (`--adopt`), in its own commit. Never touches notes in `content/`.
---

# UPGRADE

Brings template improvements (skills, hooks, workflows, docs) into this base. The engine
is `scripts/upgrade.py` (Python standard library only, no git required). The scripts
make every decision that can be computed; you drive the order and talk to the owner.

## Rules

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

## Phase 1 — The source and its engine

1. **The owner named a source** (a clone of the template, an unpacked release, or a
   release `.zip`):
   - a folder: `SOURCE=<folder>`, `ENGINE=<folder>/.claude/skills/brain-upgrade/scripts/upgrade.py`;
   - a `.zip`: unpack it with `python .claude/skills/brain-upgrade/scripts/upgrade.py fetch --source <zip>`
     and take `engine` from the JSON it prints. `SOURCE=<zip>` (the zip carries the
     release commit).
2. **No source named:** download the latest release (or `--to X.Y.Z`):
   `python .claude/skills/brain-upgrade/scripts/upgrade.py fetch [--to X.Y.Z]`.
   It prints `engine` and `source.archive`; `SOURCE=<archive>`. Tell the owner the
   archive path: passing it as the source later works offline.
3. `fetch` stops when there is no network. Say so, and ask for a release `.zip` or a
   local clone. Nothing has changed.
4. If `engine_exists` is false, the source is older than `0.2.0` and cannot upgrade a
   base. Stop.

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
2. Unpack it outside the base and follow **that copy** of this file, with
   `ENGINE=<unpacked>/.claude/skills/brain-upgrade/scripts/upgrade.py` and
   `SOURCE=<zip or clone>`, starting at Phase 2 (`--adopt`).
3. The adoption commit brings this skill into the base; later upgrades start at Phase 1.

## Without a terminal

Every step is a command the agent runs for the owner. In tools without native
`/slash` commands, ask: *"follow `.claude/skills/brain-upgrade/SKILL.md`"*. Without git,
the backup folder is the way back; with git, `git revert` of the upgrade commit (or of
the adoption commit) undoes it.
