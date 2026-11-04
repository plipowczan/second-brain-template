# Tasks

Nothing here starts before Paweł accepts `design.md`.

## 1. Default path (D1)

- [ ] 1.1 `test_skill_path.py`: read Phase 3 from `SKILL.md`, run `fetch`, `plan`, `apply`, `commit` with a stub opener and no `--allow-repository`; it fails today
- [ ] 1.2 Refusal tests: foreign zip at `fetch` and `plan`, the same zip with a planted record, the archive `fetch` saved passed back without consent
- [ ] 1.3 `upgrade.py`: the refusal names the way out (`--to <version>`, the repository), only when the zip claims the base's repository
- [ ] 1.4 `SKILL.md`: Phase 1 step 2 sets `VERSION` and no `SOURCE`; Phase 3 default lines; `--allow-repository` for named sources only; the commit check; the offline note; Bootstrap steps 3 and 4

## 2. `AGENTS.md` after a breaking release (D2)

- [ ] 2.1 Tests: breaking range, no breaking entry, edited file, `WRITING_STYLE.md` and `CLAUDE.md` untouched, `"rerender": []` honoured
- [ ] 2.2 `planner.py`: per-file `requested`, the reason in `render_note`
- [ ] 2.3 `SKILL.md`: Phase 4 default, Phase 7 reminder about `README.md`

## 3. Executable files (D3)

- [ ] 3.1 Fixtures: `executable` in `fixtures.manifest`, a `.githooks/pre-commit` file
- [ ] 3.2 Tests: bit with equal content; base already past the update; added file; update of an executable file; edited file with the bit taken and declined; adoption; rollback; `git status` clean; a protected path refused
- [ ] 3.3 `.kb-manifest.json`: add `executable`; `kbtemplate.Manifest` reads and checks it
- [ ] 3.4 `planner.py`: the `Executable bit` section, pending rows, stale and dirty checks, `check_invariants`
- [ ] 3.5 `upgrade.py`: `_write` keeps bits; writes and bit-only rows set them; journal and rollback; `applied["modes"]`; `build_commit_index`
- [ ] 3.6 `dev/check_manifest.py` and its tests: the list against the index, both directions
- [ ] 3.7 `SKILL.md` Phase 4 and 5: the row and the `executable` decision; `CONTRIBUTING.md`: the list and the check

## 4. Rename line (D4)

- [ ] 4.1 Tests: skill folder with a prefix, command moved into `b/`, no match, nothing written differently
- [ ] 4.2 `planner.py`: the match and the summary section; `SKILL.md` Phase 4

## 5. Docs (D5, D7)

- [ ] 5.1 `SKILL.md` and `README.md`: undo order, `.kb-onboard.json`, its recovery checked on a real revert
- [ ] 5.2 `README.md`: drop "~500 sources", add the course link

## 6. `yt_fetch.py` (D6)

- [ ] 6.1 Tests: `process_url` hands yt-dlp the canonical URL; a planted `yt_dlp.py` in the working directory does not run
- [ ] 6.2 Canonical URL in `process_url`; the fallback command without the current folder on `sys.path`

## 7. Finish

- [ ] 7.1 `CHANGELOG.md` under `[Unreleased]`, with an "Existing bases" paragraph per entry, and no capitalised breaking marker in a first line
- [ ] 7.2 `python tests/run_tests.py`, `python tests/run_skill_tests.py`, `openspec validate fix-upgrade-path --strict`
- [ ] 7.3 Reproduce bug 12 on a base built from `v0.1.0`, in a scratch folder, before and after
- [ ] 7.4 Push the branch, open the PR, `Tests` green on Ubuntu and Windows
- [ ] 7.5 Run the Codex review, record it in `review.md`, act on what holds up
- [ ] 7.6 Report per the brief: PR number, tests on both systems, D1 and D3, `yt_fetch.py`, what stayed unverified, and the proposal to close PR #2
