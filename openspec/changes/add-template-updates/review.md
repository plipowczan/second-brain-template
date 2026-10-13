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

## Round 4 — adversarial (Codex, focused) — 2026-10-13 — reviewed 5f8802e

Same focus, run from the coordinating session. Decision on the one finding: partial
accept, as the review coordinator decided.

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R4-1 | critical | .claude/skills/brain-upgrade/scripts/upgrade.py:400-424 | Target validation goes stale before mutation: after the stale check, the git check and resolve_mutations(), transaction() writes to the checked Path objects without checking again; Codex asks for handle-based writes that do not follow reparse points and lock against rename | partially fixed in 59d4c19; rejected: handle-based writes with locks — a process that can plant a link in the base can already write to the base and to everything the user can, so this is not a security boundary; what remains is a window of microseconds after the re-check, and rebuilding the writes on Windows handles would be risky and platform-specific |

How the accepted part was fixed:

- `transaction()` re-checks each target right before its step: `recheck()` refuses a link
  or junction anywhere on its path and a target that now resolves elsewhere;
  `make_parents()` creates missing folders one at a time and checks each for links before
  and after it is made; the target is re-checked once more right before the write.
- The step reads the target, compares its hash with the one the dry run read (carried in
  each mutation; `.kb-onboard.json` and the stamp use the plan's `onboard_before` and
  `stamp_before`), and journals that same read as the rollback preimage. A mismatch stops
  apply with "Nothing was changed: every file was put back as it was."
- Rollback never restores through a link: a journaled path that has become one is
  reported as not put back, and created folders that became links are left alone.

New tests in `test_safety.py` (`RaceTest`): a target's content changed after all checks
(as the transaction starts) and between two writes; a checked parent folder swapped for a
symlink, and for a junction (Windows only), after the checks; a folder created by the
transaction swapped for a link out of the base between two writes. In each, apply stops,
the plan is not marked applied, nothing is written outside the base, and the base holds
only the test's own interference.

Checks: `python tests/run_tests.py` — ALL PASS; brain-upgrade `python -m unittest` —
154 passed (link and junction tests ran, none skipped); brain-onboard, brain-export,
brain-gaps, brain-lint, brain-refactor suites — OK; `python dev/check_manifest.py` — ok

## Round 5 — adversarial (Codex, focused) — 2026-10-13 — reviewed de6a073

Same focus, this time with an explicit threat model, run from the coordinating session.

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R5-1 | critical | .claude/skills/brain-upgrade/scripts/sources.py:268-275 | The downloaded engine is trusted before its code runs: no check of its origin beyond HTTPS from the repository | Paweł's decision, open: R5-1 — przekazane Pawłowi jako decyzja projektowa (D3), bez zmian w kodzie w tej rundzie. Trust today is the repository named in the manifest, on GitHub over HTTPS: the same source as the skills and hooks it installs, which run in every session anyway. Signatures, or showing the origin and asking before running it, are for the maintainer to decide |
| R5-2 | high | .claude/skills/brain-upgrade/scripts/upgrade.py:304-311 | The rollback restores the preimage unconditionally, so a change a sync client or an editor made to a file after apply wrote it is overwritten (or a new file deleted) | fixed in 025c354 |
| R5-3 | high | .claude/skills/brain-upgrade/scripts/upgrade.py:475-483 | A failure saving the plan's applied marker after the transaction leaves an updated base with a plan commit refuses and apply sees as stale | fixed in 025c354 |

How they were fixed:

- R5-2: each journal entry holds the preimage (the read that passed the hash check) and
  the postimage (the bytes apply writes, or None for a deletion). The rollback puts a
  target back only while it still holds the postimage; a target that already holds the
  preimage needs nothing; anything else was changed by someone else after apply wrote it,
  is left as it is, and the error reports an incomplete rollback naming those files and
  pointing to git and the backup folder.
- R5-3: `save_plan()` rewrites the plan file atomically (temp file and rename), and
  recording the plan as applied is the transaction's final step (`finish`). The journal
  lives until it succeeds; when it fails, the base is rolled back under the R5-2 rule and
  the plan stays unapplied.

New tests in `test_safety.py` (`RollbackTest`): a failure recording the plan as applied
leaves the base as before and the plan unapplied; an updated file and an added file that
something else changes after apply wrote them, followed by a failing write, are kept with
the other change and named in an "incomplete rollback" error, while every other file is
put back. The failure-at-every-step test now also covers the plan record, as the last
write.

Test changes:
- `.claude/skills/brain-upgrade/scripts/test_safety.py` — R5-3: `test_stamp_is_written_last` asserted that the stamp is the last write of all; recording the plan as applied is now the transaction's last write, so it asserts the stamp is the last write in the base, followed by the plan file

Checks: `python tests/run_tests.py` — ALL PASS; brain-upgrade `python -m unittest` —
156 passed; brain-onboard, brain-export, brain-gaps, brain-lint, brain-refactor suites —
OK; `python dev/check_manifest.py` — ok

R5-1, decided: decyzja Pawła 2026-10-13: pokazanie pochodzenia i zgoda przed uruchomieniem;
podpisy odrzucone (the upgrade installs skills and hooks from the same repository, which
then run in every session anyway). Done in d15fd75:

- `upgrade.py fetch`, run with the base's own copy of the engine before anything from the
  source runs, prints a `provenance` block: repository, version, tag (only when the source
  proves it is that release), commit or "unknown", where it came from (download URL or
  path), the base's repository from the stamp, and `same_repository`, with a warning when
  they differ.
- `SKILL.md` (Phase 1, step 5 and a new rule) shows that block in plain words, says
  outright when the repository differs from the base's, and asks for an explicit yes;
  without it nothing runs and nothing changes. The bootstrap path (a base without the
  skill) reads the same facts from the release zip with a standard-library one-liner
  before running the release's engine.
- `upgrade.py plan` refuses a source from another repository than the stamp names unless
  `--allow-repository <that repository>` is passed, which the skill does only after the
  owner agreed to the switch.
- The trust model (the template repository on GitHub over HTTPS; the tool is code from the
  same source as the installed skills and hooks; no release signatures, decided
  2026-10-13) is written in `SKILL.md` ("What you trust"), `README.md` ("Updating your
  base") and `CONTRIBUTING.md` ("What instances trust"); the `CHANGELOG.md` entry for
  `/b:upgrade` says it.

New tests in `test_safety.py` (`ProvenanceTest`): `fetch` reports a tagged git release
(tag, commit, same repository), a download (URL, tag, commit from the zip comment) and an
unproven folder ("commit unknown", no tag); a source from another repository is flagged
with a warning naming both; `plan` refuses it without consent, refuses a consent naming
another repository, and plans it with `--allow-repository`.

Checks: `python tests/run_tests.py` — ALL PASS; brain-upgrade `python -m unittest` —
161 passed; brain-onboard, brain-export, brain-gaps, brain-lint, brain-refactor suites —
OK; `python dev/check_manifest.py` — ok

Also fixed after round 5 (two background security reviews named "authentication-bypass /
trust-boundary" and "provenance spoofing", on 92d5dc3 and 8efe5f8):

- In 8efe5f8: the provenance took the repository from the source's own manifest, so a
  download from another repository whose archive claimed the base's repository raised no
  warning, and a folder's or zip's tag came from its own history index; the
  `--allow-repository` gate lived only in `plan`, inside the source's not-yet-trusted
  engine. Now a download is judged by the repository in the HTTPS URL it was fetched
  from (a differing claim is reported), a folder or zip is marked unverified with no tag,
  and `fetch`, run with the base's own engine, refuses a repository switch before it
  unpacks anything; `plan` keeps its check as a second line.
- In 9b81b24: a clone, zip or folder could still claim the base's repository and pass.
  Now a git clone is verified only through a GitHub origin remote (the repository comes
  from that URL); anything else is unverified (repository and `same_repository`
  unknown), and `fetch` unpacks nothing until the owner accepts the claimed repository
  with `--allow-repository`. `SKILL.md` says both stops in plain words.

Tests in `test_safety.py` (`ProvenanceTest`): a download from a fork whose archive claims
the base's repository; a clone of a fork claiming the base's repository; a clone without
a GitHub origin; a folder and a zip claiming the base's repository (refused until
accepted, then reported with `verified: null` and no tag).

Test changes:
- `.claude/skills/brain-upgrade/scripts/test_safety.py` — the follow-up above: `test_fetch_reports_a_git_release` now gives its clone a GitHub origin and expects that origin as the verification; `test_folder_or_zip_only_claims` (was `test_unproven_source_says_commit_unknown`) and `test_other_repository_needs_consent_before_it_is_unpacked` (was `test_other_repository_is_flagged`) expect `fetch` to refuse an unverified source until the owner accepts it

## Round 6 — adversarial (Codex, focused) — 2026-10-13 — reviewed e41fff1

Same focus, run from the coordinating session.

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R6-1 | high | .claude/skills/brain-upgrade/scripts/upgrade.py:548-569 | commit stages with `git add -A` without checking content: a file changed after apply goes into the update commit unverified, and a file apply deleted but a sync client restored is committed instead of the deletion, while the stamp says it is gone | fixed in 8221a35 |

How it was fixed:

- apply records in the plan's `applied` record the postimage of every path it wrote or
  deleted (hash, or absent), the stamp and `.kb-onboard.json` included; this is the same
  rule as the rollback journal (R5-2).
- commit reads every applied path once and refuses with "changed after apply: …" when a
  non-merge path differs; merge paths are taken as they are (the owner's edits there are
  intended). It builds the commit from exactly those bytes in a temporary index (HEAD plus
  the applied contents), checks the working tree again right before `git commit`, and
  only after the commit brings the owner's index in line for those paths. On a refusal
  nothing is staged and nothing is committed; other staged work stays out of the commit.

New tests in `test_safety.py` (`CommitGuardTest`): an applied write edited before
commit, an applied deletion restored before commit, the stamp edited before commit, and a
change between the check and `git commit` are all refused with HEAD, the index and the
status unchanged; an untouched apply commits exactly what apply left and leaves a clean
status.

Checks: `python tests/run_tests.py` — ALL PASS; brain-upgrade `python -m unittest` —
169 passed; brain-onboard, brain-export, brain-gaps, brain-lint, brain-refactor suites —
OK; `python dev/check_manifest.py` — ok

Also fixed after round 6 (background security review, "trust-bypass / provenance
spoofing"), in 604c2ad: a local git clone still counted as verified through its origin
remote, which is a setting of the clone and proves nothing about its commits. Now only a
download fetched over HTTPS from GitHub is verified; a folder, a zip or a local clone is
unverified, and `fetch` unpacks it only when the owner accepts the repository it claims
(`--allow-repository`). The origin remote is shown as information, marked as the
clone's own setting. Repository names are compared case-insensitively, as GitHub does.

Tests in `test_safety.py` (`ProvenanceTest`): a clone whose origin remote names the
template repository is still refused until accepted and is reported unverified; consent
has to name the repository the source claims; repository names match regardless of case.

Test changes:
- `.claude/skills/brain-upgrade/scripts/test_safety.py` — this follow-up: `test_fetch_reports_a_git_release`, `test_clone_of_a_fork_claiming_ours_is_judged_by_its_origin` and `test_clone_without_a_github_origin_is_unverified` expected a clone with a GitHub origin to be verified; replaced by `test_a_local_clone_only_claims_even_with_our_origin` and `test_consent_must_name_the_claimed_repository`, which expect every clone to be unverified

Checks: `python tests/run_tests.py` — ALL PASS; brain-upgrade `python -m unittest` —
169 passed; brain-onboard, brain-export, brain-gaps, brain-lint, brain-refactor suites —
OK; `python dev/check_manifest.py` — ok

## Round 7 — adversarial (Codex, focused) — 2026-10-13 — reviewed 5764ae6

Same focus, run from the coordinating session. The round ran against 5764ae6, before
1a4f0ef, which had already removed origin-based verification of clones.

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R7-1 | high | .claude/skills/brain-upgrade/scripts/upgrade.py:738-744 | `github_repository()` searched the origin URL with an unanchored regex and no host check, so a mirror URL containing `github.com/<owner>/<repo>` passed as a verified GitHub clone and skipped the consent gate | fixed: the function and origin-based verification were removed in 1a4f0ef (no clone is ever verified, whatever its origin URL); repository names are validated everywhere in 0d24af3 |

How it was fixed:

- There is no URL parsing to harden any more: since 1a4f0ef only a download fetched over
  HTTPS from `https://github.com/<owner>/<name>/archive/refs/tags/...`, a URL this
  engine builds itself, counts as verified. A folder, a zip or a clone is unverified in
  every case, so the supported-forms whitelist the finding proposes would only re-open
  what was closed.
- The rest of the finding, "apply the same rule wherever a repository is judged by
  address, the download URL included", is done with `kbtemplate.repository_problem()`:
  a repository must be a plain GitHub `owner/name` (owner: letters, digits, hyphens, at
  most 39, not starting with a hyphen; name: letters, digits, `.`, `_`, `-`, not `.`
  or `..`). It is checked for the manifest, the stamp, `--repo` and
  `--allow-repository`, and in `sources.download()` / `latest_version()` before the
  URL is built.

New tests in `test_safety.py` (`RepositoryNameTest`): the names a mirror path,
`github.com.evil.example`, `evil-github.com`, a port, user info, a query, a fragment,
an extra segment, dot segments, a leading hyphen and a full URL would give are refused;
plain names pass; a bad `--repo` or `--allow-repository` stops `fetch` before any
download; a bad repository in the stamp or the source's manifest stops `plan`; a clone
whose origin is any of those URLs, or a genuine GitHub URL in https, scp-ssh or ssh://
form, is unverified and refused until the owner accepts it.

Checks: `python tests/run_tests.py` — ALL PASS; brain-upgrade `python -m unittest` —
173 passed; brain-onboard, brain-export, brain-gaps, brain-lint, brain-refactor suites —
OK; `python dev/check_manifest.py` — ok
