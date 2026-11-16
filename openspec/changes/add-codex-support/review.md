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
