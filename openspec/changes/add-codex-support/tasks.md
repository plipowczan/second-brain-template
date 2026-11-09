# Tasks

Design waiting for Paweł's review (proposed 2026-11-09). Nothing below starts before he
accepts `design.md`. Commit by path, never `git add -A`, until task 0.1 is done.

## 0. Migration output (D9)

- [ ] 0.1 In the maintainer's checkout, delete the untracked `.agents/` and `.codex/` the Codex migration wrote on 2026-10-15; `git status` lists neither. Do it first: the check from task 2.2 fails on any file under `.agents/skills/` it did not write, so the old copies would fail every local test run there

## 1. Source skills (D3)

- [ ] 1.1 In `brain-export`, `brain-reindex` and `brain-upgrade`, write the relative mentions of `scripts/…` as repository-root paths (`.claude/skills/<skill>/scripts/…`); quote the `brain-ingest` `description` so its frontmatter is valid YAML (D4); no other text changes
- [ ] 1.2 `python tests/run_skill_tests.py` still passes (no script changed)

## 2. Generator and its check (D1, D3, D4)

- [ ] 2.1 `dev/test_build_codex_skills.py` first, on a temporary tree: copy equals source byte for byte; Markdown under `references/` copied, `scripts/`, `*.py`, `*.json` and `__pycache__/` not; a stale copy, a missing copy, an orphan directory (`source-command-b-qa`) and an orphan file each fail `--check` and are named; CRLF in a Windows checkout is not drift; a relative `scripts/x.py` in a source `SKILL.md` fails with skill and path; a frontmatter that is not valid YAML, an empty `description`, a `description` over 1024 characters and a `name` over 64 each fail; `--check` writes nothing
- [ ] 2.2 `dev/build_codex_skills.py`: standard library only, runs from the repository root, writes `.agents/skills/` from `.claude/skills/`, `--check` mode; the skill list comes from the directories under `.claude/skills/` that the manifest ships
- [ ] 2.3 The check also reads `.codex/hooks.json` and fails on an absolute path (POSIX, drive letter, UNC) or a SessionStart command other than `python .claude/hooks/load_vault_map.py` (D5); tests for each
- [ ] 2.4 `tests/run_tests.py`: run the check where `dev/` exists, next to `dev/check_manifest.py`
- [ ] 2.5 Generate the copies, commit them by path

## 3. Codex session hook (D5)

- [ ] 3.1 `.codex/hooks.json` as in D5: one SessionStart hook, matcher `startup|resume|clear|compact`, command `python .claude/hooks/load_vault_map.py`; `additionalContextLimit` only if Paweł answers the open question
- [ ] 3.2 `.claude/hooks/load_vault_map.py` and `.claude/settings.json` unchanged; Claude Code session start in a scratch clone still prints the map
- [ ] 3.3 Try it in a real Codex session in a scratch clone at a path other than the template's, on Windows (PowerShell): trust the project, approve in `/hooks`, the session starts with the vault map; started in `content/`, the hook fails without blocking; the same in a copy without `.git` (a ZIP base): skills found, hook runs; note the Codex version in `review.md`

## 4. Manifest (D7)

- [ ] 4.1 `.kb-manifest.json`: `.agents/**` and `.codex/**` in `owned`
- [ ] 4.2 `python dev/check_manifest.py` passes; `build_known_hashes.py --check` reports the file stale until the release (expected)

## 5. Docs (D6, D8)

- [ ] 5.1 `ENVIRONMENTS.md`: the Codex row says where skills and the hook come from, how to start a skill (`$brain-ingest` for `/b:ingest`, or `/skills`), to open the base's root folder, trust the project and approve the hook in `/hooks`, not to run `/import` in a base, and that an edited skill must be copied to `.agents/skills/` by hand
- [ ] 5.2 `README.md` "Works beyond Claude Code": one line on Codex skills
- [ ] 5.3 `CONTRIBUTING.md`: `dev/build_codex_skills.py` under "Author tools in `dev/`", and under "Before you commit": edit `.claude/skills/`, then run the generator
- [ ] 5.4 `CHANGELOG.md` under `[Unreleased]` → `Added`, with "Existing bases": what the upgrade adds, the two approvals in Codex, the hand copy after editing a skill, and for owners who ran `/import`: delete `.agents/skills/source-command-*` and the old `.codex/hooks.json` before the upgrade (or as 6.2 finds)

## 6. Integration checks

- [ ] 6.1 `python tests/run_tests.py` and `python tests/run_skill_tests.py` pass on Windows; CI green on Ubuntu and Windows
- [ ] 6.2 Upgrade a scratch base from the latest release to this branch (`--allow-repository`): the plan adds the new files and nothing else; repeat with a base that already holds untracked migration output at the same paths, and write down what the plan does with it (D8)
- [ ] 6.3 In a scratch clone opened in Codex: `$brain-reindex` runs its script from `.claude/skills/`, `$brain-onboard` renders `CLAUDE.md` and `AGENTS.md` once each, the session starts with the vault map

## 7. Review

- [ ] 7.1 Codex review loop on the pull request; record rounds in `review.md`
- [ ] 7.2 Paweł merges
