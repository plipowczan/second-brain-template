# Spec Delta

## Purpose

Defines `/b:review`: the look back over a period that tells the owner what the base
gained, where it is thin, how its metrics moved, and what to do next.

## ADDED Requirements

### Requirement: The period starts where the last review ended

`brain-review` SHALL review the period from the time of the last `review` row in
`content/_outputs/log.md`, else from the date of the newest
`content/_outputs/reports/*_review.md`, else from 7 days ago, until now. `--since
YYYY-MM-DD` and `--days N` SHALL override it.

#### Scenario: First review
- **WHEN** the base has no review row and no review report
- **THEN** the review covers the last 7 days

### Requirement: The review reads every record, not the log alone

`brain-review/scripts/review_data.py` SHALL gather, for the period: the log rows; the
answers and learning sessions dated in it, with their gap counts; in a git base, the
notes created or changed by commits in it; the sources waiting in `_raw/inbox/`; the open
contradictions from `lint_scan.py`; the weakly connected notes and unanswered questions
from `gaps.py`; and a recorded metrics snapshot with its comparison from
`metrics.py --record`. It SHALL print them as one JSON document.

#### Scenario: Empty log after an upgrade
- **WHEN** the log has no rows in the period but git shows notes changed in it
- **THEN** the review reports those notes under what came in

### Requirement: The report has a fixed shape

The review SHALL write `content/_outputs/reports/YYYY-MM-DD_review.md` in the vault
language with these sections in this order: what came in, where attention went, open
contradictions, thin places, questions the base could not answer, metrics (now, before,
change), three moves. It SHALL write no note and SHALL append one `review` row to the
log.

#### Scenario: Quiet week
- **WHEN** nothing came in during the period
- **THEN** the report still has every section, and the empty ones say that nothing happened

### Requirement: The report ends with three moves in a fixed priority

Each of the three moves SHALL be one command or action with its target, chosen in this
order of priority: an open contradiction, an unanswered question, an orphan or thin note
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
