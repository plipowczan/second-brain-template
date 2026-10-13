# Review record — add-template-updates

## Round 1 — 2026-10-13 — reviewed 0c7eb09

No findings. The upgrade workflow is coherently implemented with dry-run planning, stale-state
checks, controlled application, backups, and focused commits.

Checks: `python tests/run_tests.py` — ALL PASS

## Round 2 — adversarial (Codex, focused) — 2026-10-13 — reviewed cc42d67

Focus: data loss, path traversal, running downloaded code, Windows. Run from the
coordinating session; findings checked there against the code before this round.

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R2-1 | critical | .claude/skills/brain-upgrade/scripts/kbtemplate.py:95-102 | Manifest rendered keys and class patterns, stamp `files` keys (and index paths) are not validated; a crafted path can make apply write or delete outside the base, and a manifest can reclassify `content/**` or `README.md` as owned | fixed in 76916e3 |
| R2-2 | high | .claude/skills/brain-upgrade/scripts/sources.py:154-169 | Archive members that differ only in case (or by a trailing dot or space) are one file on Windows; apply writes it twice and the stamp records two paths | fixed in 76916e3 |
| R2-3 | high | .claude/skills/brain-upgrade/scripts/upgrade.py:304-329 | Apply writes and deletes in sequence without a rollback; a locked file, a full disk or a failed stamp write leaves the base half updated | fixed in 76916e3 |

How they were fixed:

- R2-1: `kbtemplate.path_problem` / `check_paths` is the one rule for every path from an
  archive, a manifest (rendered map; patterns get `check_pattern`), the stamp, the history
  index and the plan. `protected()` (notes under `content/`, `README.md`, the stamp,
  `.kb-onboard.json`, the backup folder) is enforced in `Source.owned()`, in the
  planner's `check_invariants()` for every write or delete, and again in apply's
  `target_of()`, which also requires the resolved target to lie inside the base. The
  only exception is `content/WRITING_STYLE.md` on a requested re-render.
- R2-2: `case_collisions()` refuses case-only twins and file/folder twins in every source
  tree, in the stamp and in the plan; trailing dots and spaces fail `path_problem`.
- R2-3: `transaction()` journals the previous bytes (or absence) of every target before
  the first change, replaces files through a temp file and `os.replace`, writes
  `.kb-onboard.json` and then the stamp last, and on any exception restores every touched
  file, deletes the ones it created and removes the folders it made, then reports that
  the base is as it was. Empty folders left by deletions are removed only after success.

New tests: `test_safety.py` (21): unsafe stamp keys (traversal, absolute, drive, UNC,
backslash, dot segments, trailing dot/space, `.git`, `:`), protected and case-twin stamp
keys, manifest rendered outputs outside the base or into notes, a traversal pattern, notes
reclassified as owned or as author leftovers, an index with an unsafe path, case twins
and trailing dots in a zip, tampered plan paths and a symlink out of the base at apply,
and a failure injected at every write step of a full apply (update, add into new folders,
delete, re-render, render values, stamp) with the base byte-for-byte and folder-for-folder
as before and the plan not marked applied.

Checks: `python tests/run_tests.py` — ALL PASS; brain-upgrade `python -m unittest` —
137 passed; brain-onboard, brain-export, brain-gaps, brain-lint, brain-refactor suites —
OK; `python dev/check_manifest.py` — ok

Also fixed after round 2 (background security review of 76916e3, two findings named
"path-validation-differential", in `upgrade.py` and `kbtemplate.py`), in ea6eba5:

- apply checked targets only inside the transaction, after the no-git backup had already
  copied files to `backup/<planned path>`; its stamp/`.kb-onboard.json` exemption applied
  to planned actions too; and the notes guard read the planned string, so a link inside
  the base or a short name could lead into `content/`. Now the plan's paths are checked
  first, every target is resolved and checked by role before the dirty check, the backup
  or any write, and a target that resolves to anything but the planned path is refused.
- the path rule now also refuses Windows short names (`GIT~1`, `CONTEN~1`), device names
  (`NUL`, `AUX`, `COM1`) and characters Windows forbids; collisions and the notes guard
  compare NFC-normalised, case-folded names.

Tests added to `test_safety.py`: short names, device names and forbidden characters in
the stamp; composed and decomposed names colliding; tampered plan paths naming the stamp,
`.kb-onboard.json` or a short name; a link inside the base into `content/`; a no-git
base whose tampered plan leaves no backup folder. Checks: `python tests/run_tests.py` —
ALL PASS; brain-upgrade `python -m unittest` — 140 passed.

## Round 3 — adversarial (Codex, focused) — 2026-10-13 — reviewed 9e6cbee

Same focus as round 2, run from the coordinating session; the round 2 fixes were
accepted. The round ran against 9e6cbee, before the follow-up ea6eba5, which already
refused a target resolving to another path at apply; R3-1 asked for the stop in the dry
run and for an explicit link check.

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R3-1 | critical | .claude/skills/brain-upgrade/scripts/upgrade.py:183-198 | An owned path that is a symlink (or under one) into `content/`, `README.md` or a file outside the manifest is hashed through the link by the planner and written or deleted through it by apply | fixed in f4fbbc2 |
| R3-2 | high | .claude/skills/brain-upgrade/scripts/upgrade.py:356-390 | The uncommitted-work check omits `.kb-template.json` and `.kb-onboard.json`, so a stamp edited or staged before the dry run is overwritten without warning | fixed in f4fbbc2 |

How they were fixed:

- R3-1: `kbtemplate.link_in_path()` finds a symbolic link or a Windows junction at any
  level of a path inside the base. The planner's `check_links()` runs it on every path the
  plan would write or delete, and on the stamp and `.kb-onboard.json`, so the dry run
  stops with "Nothing was changed" before a plan exists. Apply's `target_of()` runs it
  again, and the resolved path must also pass the path rule and the notes guard.
- R3-2: apply builds the full set of mutations first and checks uncommitted work in every
  path it writes or deletes, the stamp and `.kb-onboard.json` included, plus the files
  left for a merge. Only an untracked `.kb-onboard.json` passes: bases from before 0.2.0
  have it that way, apply only adds keys to it, and the commit adds the file. The dry run
  warns about an uncommitted stamp.

New tests in `test_safety.py`: an owned file linked to a note, to `README.md` and to a file
outside the manifest; an owned folder linked into `content/`, and the same through a
junction (Windows only); a link planted between the dry run and apply; a stamp edited, and
edited and staged, before the dry run; `.kb-onboard.json` edited, and edited and staged,
before an apply that writes render values; an untracked `.kb-onboard.json` that still
applies.

Test changes:
- `.claude/skills/brain-upgrade/scripts/test_safety.py` — R3-1: `test_link_out_of_the_base_refused` and `test_link_inside_the_base_into_notes_refused` expected the dry run to plan through a link and apply to refuse; the dry run now refuses first, so they assert that, and keep apply's refusal by planting the link after the dry run

Checks: `python tests/run_tests.py` — ALL PASS; brain-upgrade `python -m unittest` —
149 passed (symlink and junction tests ran, none skipped); brain-onboard, brain-export,
brain-gaps, brain-lint, brain-refactor suites — OK; `python dev/check_manifest.py` — ok
