# Review record — add-codex-support

The pull request holds the design only, so the review reads the documents as the
deliverable. Codex CLI 0.163.0 through the `codex` plugin 1.0.6.

## Round 1 — 2026-11-14 — reviewed efb190e

`codex review --base origin/main` (the built-in reviewer).

No findings. "This patch adds only design-stage OpenSpec documents and explicitly defers
implementation pending review."

The built-in reviewer looks for defects in code, so a clean verdict on documents says
little. Round 2 asked about the documents themselves.

## Round 2 — 2026-11-14 — reviewed efb190e

Adversarial review (`/codex:adversarial-review --base origin/main`) with a focus on the
documents: claims about the repository, agreement between proposal, design, specs and
tasks, tasks that can be done literally, decisions that fail in a real base. Codex rates
`high` / `medium`; read here as P1 / P2.

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R2-1 | P1 | tasks.md:39-44, design.md D8 | A base that ran Codex's `/import` has untracked files at the new paths; `apply` refuses them and the plan marks them `conflict`, yet tasks 5.4 and 6.2 only record the outcome, so the migration path of D8 has no success criterion | fixed in 891d1fa |
| R2-2 | P2 | tasks.md:12, design.md D1 | The D1 check rejects a non-Markdown file of the skill named without the `.claude/skills/<skill>/` prefix, but `brain-onboard` (`render.py`), `brain-ingest` (`yt_fetch.py`) and `brain-lint` (`lint_links.py`) name scripts by bare file name, outside the three skills task 1.1 edits, so the check would fail the source tree | fixed in 891d1fa |

Checks: `openspec validate add-codex-support --strict` — valid; `python dev/check_manifest.py` — ok.
No code changed, so `tests/run_tests.py` is left to CI.

## Round 3 — 2026-11-14 — reviewed cce88c6

Adversarial review again, asked whether the round-2 fixes hold against
`.claude/skills/brain-upgrade/scripts/planner.py`, `upgrade.py` and the `SKILL.md` files,
and whether the documents still agree.

No findings. "Both round-2 fixes hold against the branch's upgrade code and SKILL.md
files; proposal, design, specs and tasks agree. Runtime implementation remains
unverified."

The round limit (3) is reached. The implementation, when it lands on this branch, starts
its own rounds (task 7.1).

## EGM review — 2026-11-16 — reviewed 8b7c574

`/egm:egm-review` (EGM 0.1.0), all five stages in one run: zoom out, comprehension,
critic (design, structure, style), a second zoom out, implementation readiness. Nine
fresh-context reviewers; none read this file. The reports and the full traceability
matrix are kept outside the repository, in the session notes of this review.

The reviewers read the branch, whose base is older than `main`. Checked on `main` at
`08fa2c1`: `brain-ingest` is invalid YAML there, `brain-export`'s description is cut to 49
of 452 characters by an unquoted ` #` (on both), there are 21 skills, and `0.3.0` is
tagged.

| id | sev | finding | outcome |
|---|---|---|---|
| A1 | blocker | "Standard library only" in 2.2 contradicts parsing YAML | fixed: PyYAML allowed (D1) |
| A2 | major | Pointer stubs never weighed; full copies drift in bases, need source edits and a path rule | fixed: a stub per skill (D3); full copy kept as the fallback |
| A3 | major | The claims CI cannot test come last; ZIP base without `.git` unexplained | fixed: trial in Codex first (tasks 0.2-0.5); assumption in D2 |
| A4 | major | The check targets the wrong skill and passes the real defect (`brain-export`) | fixed: both frontmatters quoted, one rule "read whole" (D4) |
| A5 | major | `.codex/**` owned lets stray Codex files ship; the Why overstates the risk | fixed: owned patterns narrowed (D7) |
| A6 | major | Hook file content open; a bespoke absolute-path detector | fixed: the generator writes the literal file (D5) |
| A7 | major | Spec does not state the check's rules; four names for one tool; no Purpose | fixed: specs rewritten |
| A8 | major | Facts measured before `main` moved | fixed: re-based on `main` |
| A9 | major | Codex agent sees only `/b:*`; `/import` is Codex's migration command | fixed: one `AGENTS.template.md` sentence; two descriptions say `/b:import`, `/b:export` |
| A10-A16 | major | Migration vs `/import`, "the docs", base-root condition, no security entry, owner workflow, other tools, "best effort", Migration Plan, D8/D9 density | fixed |
| A17-A19 | major | Task order breaks the tests; no done conditions; generator interface open; 6.2 would install `v0.3.0` (no `--ref HEAD`) and 0.1 deletes its input | fixed: tasks rewritten |
| A20-A21 | nit | Docs task details, wording, term drift | fixed |
| R1-R9 | — | Check inside bases; symlink behaviour; precise path rule (moot with stubs); end-state tree and source pointers; closing the open questions now; Non-goals in one file; survey of every tool; hook encoding fix; absolute-path regexes | rejected with reasons in the matrix |

The four open questions stay. Each now carries the review's recommendation: keep the
generator in `dev/`; release in `0.4.0`; leave the hook output limit at its default;
keep the base-root rule.

Checks: `openspec validate add-codex-support --strict` — valid; `python dev/check_manifest.py` — ok.

## Round 4 — 2026-11-16 — reviewed 2f70a81

The EGM review changed the design (stubs instead of copies), so one adversarial round ran
on the revised documents (`/codex:adversarial-review --base origin/main`), asked to check
the facts against `origin/main`. Verdict `needs-attention`, three findings. Each was
checked against `origin/main` before it was taken.

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R4-1 | P1 | design.md D8 | The cleanup deletes imported skills and the hook with no copy, so an owner's edits to them are lost. Deleting committed migration output leaves uncommitted deletions at planned paths, which `apply` refuses (`upgrade.py`, `planner.dirty_paths`). Task 6.3 covers only untracked output | fixed: copy aside and carry edits over first; commit a `git rm -r`; new task 6.4 for committed output; spec scenario |
| R4-2 | P2 | design.md D8 | A base that deleted a template skill gets its stub anyway: the deleted source is `restore?`, not selected (`planner.py` 400-402), and the stub is a selected `add`. The stub then points at nothing | fixed: the stub's last sentence says the skill was removed and stops (D3), the owner deletes the stub after the upgrade (D8, docs), trial 0.3 and task 6.2 check it. Not taken: tying stubs to sources in `brain-upgrade`, which this change leaves untouched |
| R4-3 | P2 | tasks.md 1.1 | The tests were to copy the tracked tree as `dev/test_check_manifest.py` does; that copy holds the two broken frontmatters, so the success cases cannot pass before section 2 | fixed: the tests use the template's manifest and fixture skills of their own |

Checks: `openspec validate add-codex-support --strict` — valid; `python dev/check_manifest.py` — ok.

## Trial in Codex — 2026-11-16 (tasks 0.1-0.5)

On Windows 11, in PowerShell. Codex TUI 0.169.0 (Paweł's sessions) and `codex exec`
0.163.0 (agent runs), both on `eb900de` (this branch with `main` merged).

**0.1.** The migration output in the maintainer's checkout (87 files, untracked) was
copied to `C:\Projects\kb-codex-migration-output\`, outside any repository, with matching
checksums, then deleted. `git status` lists neither folder.

**0.2.** Scratch clone `C:\Projects\kb-codex-trial` with two hand-written stubs
(`brain-reindex`, `excalidraw-diagram`) and `.codex/hooks.json`, as D3 and D5 show. ZIP
base: the same tree without `.git`, `C:\Projects\kb-codex-trial-zip`.

**0.3.**

| step | result |
|---|---|
| Session in the clone root, project trusted, hook approved | Pass. The session starts with the vault map: asked for the first row of the Folders table, Codex quotes it without reading a file. |
| `$brain-reindex` | Pass. The agent reads the stub, then `.claude/skills/brain-reindex/SKILL.md`, and rebuilds the indexes. The three index files change only in `updated:`, which is the script's output; the `exec` event log of 0.163 does not show the script call itself. |
| `$excalidraw-diagram` | Pass. The agent uses the project's stub, reads `.claude/skills/excalidraw-diagram/SKILL.md` and both files it needs from `references/`, and writes the diagram. The maintainer also has a user-level `excalidraw-diagram` in `~/.agents/skills/`; Codex lists both, and `$excalidraw-diagram` in the clone took the project's. |
| Stub whose source is gone (`SKILL.md` renamed) | Pass. The agent says the skill was removed from this base and stops; the indexes are untouched. |
| Session started in `content/` | Pass. The hook exits with code 1, no map, the session starts and answers. |
| ZIP base (no `.git`), trusted, hook approved | Pass. `/skills` lists `brain-reindex` (and `exec` lists both stubs); the session starts with the vault map. No `git init` is needed. |
| Linux or macOS | Not run: none at hand. Gap kept until task 5.1's CI and a later manual check. |

Found on the way, for `ENVIRONMENTS.md` (task 4.1):

- Codex asks for the hook review with every changed hook at once. With plugins installed
  the base's hook is one of many (19 here), and "Trust all" would trust every one. The
  owner should pick "Review hooks" and trust only `python .claude/hooks/load_vault_map.py`.
- In TUI 0.169.0, "Review hooks" failed once with `config/read failed in TUI`. The project
  trust was already saved; a second attempt worked (a restart, or `/hooks` in the session).
- Untrusted plugin hooks print a "Hook failed" line each at every prompt. That is noise
  from the owner's own setup, not from the base.

**0.4.** From the docs, not tested locally:

- **GitHub Copilot CLI** reads `.github/skills`, `.agents/skills` and `.claude/skills`; on
  the same `name` the first found wins in that order, so the stub hides the source and
  points at it. The VS Code and cloud-agent docs do not say how duplicates behave.
  (docs.github.com, Copilot CLI command reference, "Skill locations".)
- **Cursor** reads `.agents/skills` and `.cursor/skills`, and `.claude/skills` for
  compatibility, on by default. Its docs do not say which of two skills with one name
  wins. (cursor.com/docs/skills.)

Either way the agent reaches the same `.claude/skills/` text, so the design stands.

**0.5.** Codex followed every stub. The design keeps the stub (D3); the full-copy
fallback is not needed.

## Implementation — 2026-11-16 (sections 1-4)

| section | commit | checks |
|---|---|---|
| 1. Generator and its tests | ed30298 | 19 tests in `dev/test_build_codex_files.py`, written first; they failed only because the generator was missing, then pass. |
| 2. Source frontmatter | 313f46a | The check reported exactly `brain-export` (cut at ` #`) and `brain-ingest` (invalid YAML). Both are quoted, text unchanged; `/b:import` and `/b:export` in two descriptions. `run_skill_tests.py` passes (1 skip). |
| 3. Manifest and Codex files | 8e266a7, 9310d59 | The generator wrote 21 stubs and `.codex/hooks.json`; the check exits 0 and `dev/check_manifest.py` passes. `tests/run_tests.py`: ALL PASS, fails and names the stub after one byte of `brain-qa`'s stub changed, ALL PASS after the revert. A committed `.codex/config.toml` fails the manifest check ("matches no class"). `git diff main` of the Claude Code hook and `settings.json` is empty; a Claude Code session in a scratch clone starts with the vault map. |
| 4. Docs | 57cc7e5 (4.2-4.5), 4.1 below | `tests/run_tests.py`: ALL PASS. |

## Upgrade of existing bases — 2026-11-16 (tasks 6.1-6.4)

Each scratch base is tag `v0.3.0` cloned from the maintainer's checkout, stamped with
`upgrade.py stamp` and committed. Each `plan` ran
`--source <this worktree> --ref HEAD --allow-repository plipowczan/second-brain-template`
at 57cc7e5, and `apply` took the defaults (`{}`). The manifest still says `0.3.0`, so the
plan reads `0.3.0 -> 0.3.0` with the `[Unreleased]` entries. The bases were not pruned
the way `/b:onboard` prunes, so each plan also deletes the author-class files
(`CONTRIBUTING.md`, `dev/`, `openspec/`); that is the scratch setup, not this change.

**6.2, owner dropped `brain-gaps`.** `add` for all 21 stubs (`brain-gaps` and the new
`brain-watch` included) and `.codex/hooks.json`. The three `brain-gaps` files are
`restore?`, not selected. Other actions: `add` for the `brain-watch` skill and
`.claude/commands/b/watch.md`; `update` for `brain-export` (and two of its scripts),
`brain-import`, `brain-ingest`, `.gitignore`, `.kb-manifest.json`, `CHANGELOG.md` and
`tests/run_tests.py`. Nothing under `content/` is written: `content/_privacy.md` is
"changed upstream, information only" and `content/WRITING_STYLE.md` only a proposal.
`apply` and `commit` complete; the stubs and the hook equal the template's, and
`.claude/skills/brain-gaps/` stays deleted.

**6.3, `/import` output untracked, with the owner's `my-skill`.** `plan` marks 21 paths
`CONFLICT` ("new template file, but this base has its own file here"): the 20 migrated
skill copies and `.codex/hooks.json`. `brain-watch`, which the migration never saw, is a
plain `add`. It also warns that `apply` refuses uncommitted changes in those paths.
`apply` with the defaults stops ("choose keep, overwrite or merge"); with `overwrite` on
every conflict it stops on the uncommitted changes. Neither writes anything. After the D8
steps (copy aside, delete the template skills' folders, `.codex/hooks.json`, every
`source-command-*`, `.codex/hooks/`, `.codex/agents/`), `plan` lists 21 stub `add`s and
the hook `add`, no conflict. `apply` and `commit` complete; every stub equals the
template's, and `my-skill` is unchanged and still untracked.

**6.4, `/import` output committed.** Before the clean-up, the same 21 `CONFLICT`s as in
6.3. After `git rm -r` of the D8 paths and a commit, `plan` lists the stubs and the hook
as `add`, not `restore?`: the stamp never had these paths. `apply` and `commit`
complete; every stub equals the template's, and `my-skill` is unchanged.

## Round 5 — 2026-11-16 — reviewed 7617e75

The first round on the implementation (sections 1-4 without 4.1, and the record of
6.1-6.4): `codex review --base origin/main` through the `ss:review-fix` helper, Codex CLI
0.169.0, plugin 1.0.6. The repository has no `REVIEW.md`, so the default scale applied
(P0-P2 important).

No findings. "No actionable correctness issues were identified in the diff. The generated
Codex files pass `python -B dev/build_codex_files.py --check`; full integration tests and
interactive Codex behavior were not verified."

Checks: `tests/run_tests.py` — ALL PASS on 57cc7e5; the record commit changed no code.
