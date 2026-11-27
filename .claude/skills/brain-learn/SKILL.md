---
name: brain-learn
description: 'Use when the user says "learn", "quiz me", "test me on X", "let me explain X back", "przepytaj mnie". Teaches a topic from the vault: explains it plainly, has the owner explain it back and names each gap (the base lacks it, its sources lack it, you missed it); `--quiz` asks graded questions. Saves the session to `_outputs/learning/` and one log row, changes no note. Do NOT use for answering a question (use `/b:qa`).'
---

# LEARN

## When to use

The owner wants to check what they understand of a subject their base covers, not to
get an answer. Two modes:

- `/b:learn <topic or [[Note]]>` — explain-back: the agent explains the subject in plain
  words, the owner explains it back in their own words, and the agent names what is
  missing.
- `/b:learn --quiz <topic or [[Note]]> [N]` — N questions (5 when N is omitted, at most
  20), one at a time, each graded against the note it came from.

**A person must be present.** When the run cannot get a reply (a scheduled run, a
non-interactive call), say that this skill needs someone to answer and stop before the
first question: no session file, no log row. Without a topic, ask for one.

## Workflow

1. **Find the notes** the way `brain-qa` does: search
   `content/_indexes/catalog.md` with a pattern first, then the folder sections, then
   the notes; follow `graph.md` only when the subject spans linked notes. For a
   `[[Note]]`, start from that note and the notes it links to. Read at most five notes:
   the ones that carry the subject. When nothing covers it, say that the base has no
   note on the subject, offer `/b:compile <topic>` or an ingest of a source on it, and
   stop without a session file.
2. **Run the mode** (below). Ground every point you explain, ask or grade in a note you
   read, and name that note. Anything you add from outside the notes is marked as
   yours, never presented as the base's.
3. **Save the session** (below), then **log the run**:

   ```bash
   python .claude/skills/brain-reindex/scripts/oplog.py append --op learn --count questions=<N, 0 for explain-back> --count gaps=<number of gaps> --note <session path without content/ and .md> --note <each note a point, question or gap came from, relative to content/, without .md>
   ```

   When `oplog.py` is missing, skip the row and say so in the closing message.
4. **Offer, do not write.** Change no note. For each kind of gap, offer the step that
   would close it:
   - the base lacks it → `/b:compile <subject>`, or drop a source on it into the inbox
     and run `/b:ingest`;
   - its sources lack it → `/b:enhance [[Note]]`, to check the claim against the source
     or find a source that supports it;
   - you missed it → reread `[[Note]]`, or `/b:learn --quiz <topic>` later.

### Explain-back

1. Explain the subject in one short paragraph of plain words, in the language the owner
   uses. No term the notes do not define. Do not show the notes yet.
2. Ask the owner to explain it back in their own words, as they would to someone new to
   it, and wait for the reply.
3. Compare the reply with the notes. Name what the owner got right in one line, then
   every gap as one of three kinds:
   - **the base lacks it**: the subject needs a point no note covers, or the owner said
     something true that no note has. This is a gap in the base, not a mistake of the
     owner.
   - **its sources lack it**: a note claims it, but the archived source the note cites
     does not support it. Read only the sources cited (`source:` / `sources:`) by the
     notes in use, under `content/_raw/processed/`; when a cited file is missing, say so.
   - **you missed it**: the notes have it and the owner did not say it, or said
     something the notes contradict (give the note's version).

### Quiz

1. Ask N questions one at a time, mixing recall ("what is …"), why ("why does …") and
   application ("what would you do if …") as far as N allows. Each question comes from one note; do not
   give the answer away in the question.
2. After each answer, grade it: **right** (1 point), **partly** (0.5) or **wrong** (0),
   with the note named and the point it makes in one sentence. "I don't know" or "skip"
   is wrong, with the answer shown. A grade follows what the note says, not what you
   know: when you think the note itself is wrong, grade against the note and add a gap
   of kind "its sources lack it" or "the base lacks it".
3. "Stop" ends the quiz: score the questions asked so far.
4. End with the score (`3.5/5`) and the notes to revisit: those behind every partly or
   wrong answer. Every partly or wrong answer is a gap of kind "you missed it", unless
   step 2 gave it another kind.

## The session file

`content/_outputs/learning/YYYY-MM-DD_<slug>.md`, where `<slug>` is what
`python .claude/skills/brain-reindex/scripts/oplog.py slug "<topic>"` prints (it prints
`private` when the topic holds a private term; without the script, a short kebab-case
slug of the topic). When the name is taken, add `-2`, `-3`: never overwrite a session.

**On the first run** (the folder does not exist yet), tell the owner once, in the
closing message, before the block: sessions are
tracked by git like saved answers, so they reach every clone of the base, and
`/b:export --public` leaves them out; to keep them local, add
`content/_outputs/learning/` to `.gitignore`.

```markdown
---
title: "<Learning session or Quiz, in the vault language>: <topic>"
date: YYYY-MM-DD
type: learning-session
mode: <explain | quiz>
score: "<points>/<N>"
gaps: <number of gaps, 0 when none>
agent-created: true
---

# <title>

## <"Notes used">
- [[Note A]]

## <"Your explanation" (the owner's words as given), or "Questions and answers":>
### Q1 (<recall | why | application>) — <right | partly | wrong>
<the question>
<"Your answer">: <the owner's answer as given>
<"From"> [[Note]]: <the point the note makes>

## <"Gaps">
### <"The base lacks it">
### <"Its sources lack it">
### <"You missed it">
<each kind lists its gaps with the note named, or says none in one line>

## <"Next steps">
```

`score:` is written for a quiz only. The headings are in the vault's primary language, from the writing-style document
(`content/WRITING_STYLE.md`, or the one AGENTS.md "Writing Style" names in an older base);
`gaps:` is a number, so `/b:review` and `/b:gaps` can count it whatever the language.
Inside the file, link notes with `[[wikilinks]]`. `content/_outputs/` is outside the
indexes, so saving needs no index update.

## Calibration

A session goes wrong when the agent explains or grades from its own knowledge instead
of the notes, gives the answer away in the question, or counts a true statement the
notes lack as the owner's mistake. Right: every point names its note, outside knowledge
is marked, and a gap the base has is called the base's gap.

## Closing message

```
<Explain-back | Quiz>: <topic> — <score, quiz only>
Gaps: <n> the base lacks · <n> its sources lack · <n> you missed
Revisit: [[Note]], [[Note]]
Saved: <session path>
Next: <the offers from step 4>
```

## See also

`brain-qa` for answers from the vault. `LIMITS.md` before telling the owner the base is
sure of something.
