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
