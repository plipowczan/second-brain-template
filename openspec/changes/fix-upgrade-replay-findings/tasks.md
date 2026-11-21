# Tasks

Paweł decided the scope and the re-render criterion on 2026-11-21 (both fixes in one pull
request; an untouched `AGENTS.md` is re-rendered whenever its template changed). The rest
of `design.md` is open to his review in the pull request.

## 1. `AGENTS.md` follows its template (D1, D2)

- [x] 1.1 Tests first: template changed without a breaking entry; template unchanged with a breaking entry; owner declines and the next plan offers it again; no render inputs leaves the base up to date; `null` output hash is a proposal with its own note; the proposal taken whole is recorded and followed later
- [x] 1.2 `planner.py`: request `AGENTS.md` by default when the template differs from the stamp's `template_hash` and `apply` can act on it; drop the breaking-entry test; the summary notes
- [x] 1.3 `SKILL.md`: Phase 3 and Phase 4 describe the new default and the way out for a `null` hash; `CONTRIBUTING.md` table

## 2. Caption de-duplication (D3)

- [x] 2.1 Test first: a manual track whose cue starts with the previous cue's last line keeps it (back to back and with a gap)
- [x] 2.2 `yt_fetch.py`: drop repeated lines only in a file with inline timestamps; otherwise coalesce identical cues only

## 3. Finish

- [x] 3.1 `CHANGELOG.md` under `[Unreleased]`, with an "Existing bases" paragraph per entry
- [x] 3.2 `python tests/run_tests.py`, `python tests/run_skill_tests.py`, `openspec validate fix-upgrade-replay-findings --strict`
- [ ] 3.3 Push the branch, open the PR, `Tests` green on Ubuntu and Windows
- [ ] 3.4 Run the Codex review, record it in `review.md`, act on what holds up
- [ ] 3.5 Report: PR number, tests and CI, what a `null`-hash base gets and its way out, what stayed unverified
