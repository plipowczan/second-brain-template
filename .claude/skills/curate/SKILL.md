---
name: curate
description: Use when user says "curate", "prune", "cleanup the vault", "retire stale notes", "wyczyść bazę". Scores notes for staleness/isolation/dead-links/duplication, writes a triage report, and on confirmation moves retired notes to _graveyard/.
---

# CURATE

## When to use

Trigger phrases: "curate", "prune", "cleanup", "retire stale notes", "wyczyść bazę".
The user wants a hygiene sweep that proposes (and, on confirmation, executes)
reversible retirement of stale/unused content. Recommended cadence: quarterly.

`/lint` diagnoses; `/curate` treats. This skill is action-oriented but every
mutation is gated on explicit user confirmation. Nothing is ever `git rm`'d.

## Workflow

### Phase 1 — Gather (read-only)

1. Read `content/_indexes/vault-map.md`, `catalog.md`, `graph.md` (Navigation
   Protocol — never grep all of `content/`). If any index is missing/stale, run
   `/reindex` first.
2. For each note collect: frontmatter `date` and `agent-reviewed`; git last-touched
   date via `git log -1 --format=%cs -- <path>`. Use the most recent of these as
   the "last touched" date.
3. Parse graph edges with `curate_score.parse_graph(open("content/_indexes/graph.md").read())` to get
   per-note (in_edges, out_edges).

### Phase 2 — Score

For every note compute `age_days = curate_score.days_since(last_touched, today)`
then `score, reasons = curate_score.score_note(age_days, in_edges, out_edges, dead_link)`.

- `dead_link` starts False. Only run live checks on the **flagged subset** — notes
  that already have age_points>0 or isolation_points>0, prioritising `tool` notes.
  For those, extract the `source:`/repo URL and run
  `python .claude/skills/curate/scripts/curate_links.py <url> ...`. A `"dead"`
  result sets `dead_link=True`; `"unverified"` leaves it False and is noted as
  `unverified` in the report (never auto-flag on a network error).
- Detect duplication/superseded: if a newer `compiled-note` (or newer note with the
  same topic per catalog summaries) covers the same ground, set `has_superseder=True`
  for the older note.
- `action = curate_score.recommend_action(score, dead_link, has_superseder)`.

### Phase 3 — Triage report

Write `content/_outputs/reports/YYYY-MM-DD_curate.md`. Group candidates by
recommended action (`archive`, `merge`, `refresh`, `keep`). For each: note path,
score, signals fired (`reasons`), recommended action, one-line rationale, and any
`unverified` flags. Print summary counts per action to the user. This report is
the dry-run; produce it before any mutation.

### Phase 4 — Execute (only after explicit user confirmation)

Present the grouped candidates and ask the user to confirm which actions to run.
Then, per confirmed note:

- **archive** → move the file to `content/_graveyard/` preserving its folder name as
  a prefix if needed to avoid collisions; preserve all frontmatter and add
  `archived: YYYY-MM-DD` and `archived-reason: "<reasons joined>"`. Repair or stub
  inbound wikilinks (delegate to `/refactor` link-repair).
- **merge** → delegate to `/refactor` (merge into the superseding note; it repairs
  wikilinks).
- **refresh** → delegate to `/enhance` (re-verify and update the note in place).
- **keep** → no action.

After mutations, update all three indexes per CLAUDE.md auto-update rules (remove
archived notes from counts, catalog entries, graph nodes/edges). Optionally run
`npx quartz build` to confirm the build still succeeds.

## Safety

- Mutation is gated on explicit confirmation. Default is the dry-run report.
- Reversible: retirement = move to `_graveyard/` (build-excluded). Restore by moving
  the file back to its topic folder.
- Network errors / blocked status codes are `unverified`, never `dead`.
- Never modify `.obsidian/`, the `quartz/` engine dir, or `.github/`.

## See also

- CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
- `/reindex` — rebuilds indexes if missing or stale. Run before curate if needed.
- `/lint` — passive diagnosis. `/refactor` — merge + wikilink repair. `/enhance` — refresh.
