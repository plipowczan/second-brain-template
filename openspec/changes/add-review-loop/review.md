# Review record — add-review-loop

## Design review 1 — 2026-11-27 — reviewed 0749d2d (`design.md`)

One independent reviewer with no context from the session that wrote the design (a fresh
agent given only the repository and the change). `/egm:egm-review` was not run: it can be
started only by the maintainer. Twelve findings; every one checked against the code
before it was taken.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | blocker | `apply` deleting the temp folders without git breaks the merge phase (it reads the payload) and the `commit` step; deleting the download breaks the offline reuse `plan` advertises; re-run plans are never recorded | Taken in part: `apply` deletes nothing; `commit` deletes only the folder of the plan and its payload, as its last step, git or not, because merges come before it and nothing after it reads the plan (checked against Phase 7 and the cycle after an adoption); it keeps the download for offline reuse; downloads, `fetch` folders and superseded plans go to a `cleanup` step at the end of the skill. Every deletion checks the temp parent, the prefix and links (D11). Not taken: moving every deletion to `cleanup`, because the upgrade to `0.5.0` runs the old skill, which has no such step, so `commit` is the only cleanup that run gets |
| 2 | major | The upgrade to `0.5.0` runs the old skill and old `fetch`, so new skill steps and `fetch` output are absent on that run | Taken: D11 says per bug what the first run gets; three changelog steps cover the rest |
| 3 | major | `undo` restored copies without checking for later edits, refused `content/WRITING_STYLE.md`, and could be run on an older backup first | Taken: hashes before and after for every path, restore only on a match, `WRITING_STYLE.md` allowed, newest backup first by the stamp |
| 4 | major | `## Recent Changes` in `vault-map.md` is already a change list and the design ignored it | Taken: D2 states the relation; the review reads both |
| 5 | major | Backlog: unusable files stall the queue, attachments counted as sources, URLs beyond N lose their checkpoint, batches split clusters, no hash script, the argument rule of `ingest-plan` | Taken: unusable files excluded from N, attachments defined, every URL taken then the inbox fills N, clusters within a batch stated as the price, `inbox_order.py`, argument rule and archive order (D8, "Archive order") |
| 6 | major | `lint_links.py` keeps no edges and has one test; links counted loosely; weak notes from `graph.md` contradict D4; missing scripts; 0 notes | Taken: rewrite behind golden tests, distinct note-to-note links, `weak` computed in `metrics.py`, missing scripts reported, `null` for an empty vault (D4, D5) |
| 7 | major | Learning sessions and free-text topics in a committed log can publish private things | Taken: topic slugs and every log path pass the private-terms check of `privacy_sweep.py`; committing the sessions is question 5 for Paweł (D1, D7) |
| 8 | minor | Union merge leaves two metric rows for one day, out of order | Taken: the last row per date wins, rows sorted on read (D4) |
| 9 | minor | "About a third of current levels" was false; one orphan in a small base trips the step; slow decay is missed | Taken: steps need at least 2 notes, a second comparison with a snapshot at least 28 days old, rationale corrected (D6) |
| 10 | minor | `git log` quotes non-ASCII paths; curate calls git per note; uncommitted work; CRLF; UTC vs local; `rmtree(onexc=)`; temp dirs in tests; same-day second review | Taken: `-z`, one call stated as new code, `git status --porcelain -z`, bytes with LF, `--since` is a UTC date, no `onexc`, tests set `TMP`/`TEMP`/`TMPDIR`, a same-day review re-covers the last period and never overwrites a report (D4, D5, D11) |
| 11 | scope | Calibration sections and new descriptions on seven unchanged skills only create upgrade conflicts; the 500-character check does not exist yet | Taken: the pattern goes on the two new skills and `brain-ingest` only; the check is listed as new work (D10) |
| 12 | minor | D1's reason was wrong (only refactor and watch run `build_indexes.py`); qa offers compile and enhance, not ingest; `brain-output`; nested skills double rows; Workflows and `_raw/skipped/` rows missing | Taken: reason corrected, offers corrected, `brain-output` writes no row, a nested skill writes none, `AGENTS.template.md` rows added (D1, D2, D7, D12) |

The reviewer also confirmed sixteen claims of the design against the code (indexes and
lint skip `_outputs/` and `_` files, the hook's blocking classes, export exclusions,
seeded `content/`, the meaning of `--batch`, the orphan rule of `lint_links.py`, the
missing lines of isolated notes in `graph.md`, the skill and command counts, the longest
description, the engine's single write under `content/`, today's backup, the commit
body, lint's type source, `mkdtemp`, the union driver, lint's 10-note floor, the
`0.3.0` and `0.4.0` precedents). The Quartz ignore list and the metrics of the
maintainer's base were checked by the session that wrote the design.
