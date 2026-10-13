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
