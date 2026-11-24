# Design

## Context

See `proposal.md` (Why) for the measurement. The protocol lives in three places: the
brain-qa workflow (`.claude/skills/brain-qa/SKILL.md`), the Navigation Protocol of the
agent instructions (`AGENTS.template.md`, rendered to `AGENTS.md` in an instance), and the
`/b:qa` command, which until now only told the agent to use the skill.

The new text was measured on a copy of a base that is older than this repository and not
yet an instance of it. Its `SKILL.md` and `qa.md` were byte-identical to the template's
before the change; its `AGENTS.md` has a different layout from `AGENTS.template.md`. The
copy had no session-start hook, so the vault map was not in context at all.

## Goals / Non-Goals

**Goals:**
- Ship the measured text, so that the before/after measurement describes what instances
  get.
- Keep accuracy as measured: every question the vault answers is answered, and "the vault
  does not cover this" comes only after a full fallback search.

**Non-Goals:**
- The session-start hook and the map it prints (it feeds every workflow and needs its own
  measurement on an instance that has the hook).
- `LIMITS.md` itself: its opening line (`/b:qa` and `/b:lint` read it before they say the
  base is sure of anything) stays true.
- Other workflows that read the map first (ingest, compile, lint, and so on).

## Decisions

### D1. Port the measured text verbatim

Any rewording is an unmeasured change. For the skill and the command the measured diffs
apply as they are, because the files were byte-identical to the measured "before". For
`AGENTS.template.md` the same sentences are carried into the template's own layout:

- Level 0 header `— read FIRST on every operation` → `— the map`. The template's Level 0
  has no sentence about the session start, so there is nothing to keep or add.
- Level 1 header `— read for search/navigation` → `— search it with a pattern`, and its
  `Read only the folder sections you need.` → the measured sentence about pattern search.
- Level 2: the measured sentence about searching for a note's title. Its header stays.
- Rules 1, 2 and 4 in the measured wording. The measured base's rule 1 also exempts
  workflows that name their note or only run a script; the template's rule 1 never had
  that sentence, and this change does not add it.
- Rule 5 keeps the measured condition in the template's shorter sentence: "Search the
  notes under `content/` directly only after the catalog found nothing — use indexes
  first." The measured base's rule 5 is longer: it also names a value the indexes do not
  carry and the scanners that read `content/` by design, which the template's rule never
  had.

Alternative: rewrite the rules for the template's tone. Rejected: the measurement would
no longer describe the shipped text.

### D2. One phrase differs from the measured text: the pattern example

Step 1 of the measured skill illustrated the pattern with a phrase from the measurement's
own question set and the title word of a note in that base. `CONTRIBUTING.md` forbids
values from one base in skills, and this repository is public. The example is replaced
by one of the same build (a question in a language other than the vault's, answered by a
pattern of the words a note title would use, with synonyms): `"przepis na ciasto"` →
`cake|baking|recipe`. Nothing else in the skill differs from the measured text.

### D3. A new capability instead of modifying `method-limits`

The requirement that Q&A reads `LIMITS.md` before claiming certainty sits in the
`method-limits` delta of `add-quality-guards`, which is complete but not archived, so
`openspec/specs/` has no `method-limits` spec to modify. Archiving that change here would
pull seven unrelated capabilities into this pull request. The new `qa-navigation`
capability adds requirements only, and the one about `LIMITS.md` is worded to stay within
`method-limits`: the file is still read before any claim of certainty.

### D4. Keep the full fallback before "not covered"

In the measurement the agent, before saying the vault does not cover a question, mostly
searched the notes directly and rarely read the map or catalog sections (sections in 2 of
80 runs), and every refusal was correct. Step 2 stays in the measured wording as a safety
net: it costs nothing when the catalog pattern finds the note, and a base with a different
title vocabulary may need it. Shortening it would need its own measurement.

### D5. The command includes the skill by file reference

`/b:qa` includes `.claude/skills/brain-qa/SKILL.md` with a Claude Code file reference
instead of a copy of its text, so the workflow stays in one file and a question without
the command still reaches the same text through the skill. Codex does not use
`.claude/commands/`, so it is unaffected.

The file reference resolves against the folder the session started in, so a session
started in a subfolder of the base (for example `content/`) gets the command without the
skill text, while the command still says not to load the skill. One sentence after the
measured instruction covers that case: if the workflow text is missing, load the
`brain-qa` skill instead. It is not part of the measured text. From the base root the text
is included, so the sentence does not apply there and the measured result stands.

## Risks / Trade-offs

- [The measurement ran without the session-start hook] → An instance already has the map
  in context, so there the change removes the skill's second read of the map rather than
  the only one; that case was not measured. If accuracy held with no map in context at
  all, it should hold with the map in context.
- [One base, one model, 40 questions] → The fallback in step 2 is kept whole (D4), so a
  base whose titles do not match the question's words still gets the map, the sections
  and a direct search before "not covered".
- [The command saves input and time more than money] → The removed call read the cached
  session start, so the 40 questions cost 0.17 USD less with the command than without it.
  The cost figure for owners is the whole change, not the command alone.
- [The tests do not check the protocol text] → The evidence is the before/after
  measurement; the tests guard only that nothing else broke.

## Migration Plan

Nothing for notes. Existing bases get the skill and the command with `/b:upgrade` (owned
files). An untouched `AGENTS.md` is re-rendered by the upgrade because its template
changed; an edited one gets the difference as a proposal. Rollback is a revert of the
commit.
