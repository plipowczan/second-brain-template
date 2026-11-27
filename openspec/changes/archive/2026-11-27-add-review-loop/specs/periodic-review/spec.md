# Spec Delta

## Purpose

Defines `/b:review`: the look back over a period that tells the owner what the base
gained, where it is thin, how its metrics moved, and what to do next.

## ADDED Requirements

### Requirement: The period starts where the last review ended

`brain-review` SHALL review the period from the time of the last `review` row in
`content/_outputs/log.md` until now; that row SHALL carry `days=N`, the length of the
period it covered. When the last review row is from the same UTC day, the review SHALL
cover that row's period again. Without a review row, the period SHALL start at the date of
the newest `content/_outputs/reports/*_review.md`, else 7 days ago. `--since YYYY-MM-DD`,
read as a UTC date, and `--days N` SHALL override it.

#### Scenario: First review
- **WHEN** the base has no review row and no review report
- **THEN** the review covers the last 7 days

#### Scenario: Second review on the same day
- **WHEN** a review ran this morning over 7 days and the owner runs it again
- **THEN** the second review covers the same 7 days, not the hours since the first

### Requirement: The review reads every record, not the log alone

`brain-review/scripts/review_data.py` SHALL gather, for the period: the log rows; the
`## Recent Changes` entries of `vault-map.md`; the answers and learning sessions dated in
it, with their gap counts; in a git base, the notes committed or changed but not
committed in it; the sources waiting in `_raw/inbox/`; the open contradictions from
`lint_scan.py`; and a recorded metrics snapshot from `metrics.py --record`. It SHALL
print them as one JSON document.

#### Scenario: Empty log after an upgrade
- **WHEN** the log has no rows in the period but git shows notes changed in it
- **THEN** the review reports those notes under what came in

### Requirement: A missing script does not stop the review

`review_data.py` SHALL report a script that is missing or fails as unavailable and SHALL
still gather the rest.

#### Scenario: brain-lint deleted by the owner
- **WHEN** `lint_scan.py` and `metrics.py` are missing
- **THEN** the report says contradictions and metrics are unavailable and still covers the rest

### Requirement: The report has a fixed shape

The review SHALL write `content/_outputs/reports/YYYY-MM-DD_review.md` (with `-2`, `-3`
when the name is taken, never overwriting) in the vault language with these sections in
this order: what came in, where attention went, open contradictions, thin places,
questions the base could not answer, metrics (now, before, change), three moves. It SHALL
write no note and SHALL append one `review` row to the log.

#### Scenario: Quiet week
- **WHEN** nothing came in during the period
- **THEN** the report still has every section, and the empty ones say that nothing happened

### Requirement: The report ends with three moves in a fixed priority

Each of the three moves SHALL be one command or action with its target, chosen in this
order of priority: an open contradiction, an unanswered question, an orphan or weak note
in a folder touched in the period, a waiting inbox, an untouched note.

#### Scenario: Contradiction open
- **WHEN** a note carries a `> [!contradiction]` callout
- **THEN** the first move names that note and asks the owner to decide which claim holds

### Requirement: The review needs no person and refuses a young base

The review SHALL ask no question, so it can run unattended. Below 10 notes it SHALL say
that the base is too young for a review, give the count, and write nothing.

#### Scenario: Seven notes
- **WHEN** the vault holds 7 notes
- **THEN** the review says so and writes no report, no snapshot and no log row
