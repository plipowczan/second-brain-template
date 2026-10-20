# Limits

Where this way of keeping knowledge goes wrong, and what to do about each failure. It is
written for the owner of the base and for the agent that maintains it. `/b:qa` and
`/b:lint` read it before they say the base is sure of anything.

The method earns its keep: an agent does not get bored, does not forget a backlink, and
updates five notes in one pass. None of that makes the notes correct.

## 1. Errors compound

A note gets something subtly wrong. An answer built on that note repeats it. The answer
is filed back into the base, and now two notes agree on the error. A few months later it
reads like consensus. Lint does not catch this: it checks structure, and the model that
reviews the notes is the model that wrote them.

What to do:

- **Owner:** before a decision that costs money or time, open the source in
  `content/_raw/processed/` and check the claim yourself.
- **Owner:** promoting a saved answer with `/b:compile` or `/b:enhance` adds a new claim
  to the base. It does not confirm an old one.
- **Agent:** never write an answer back into notes without the owner's choice. When two
  notes agree, check whether they rest on the same single source before you treat that as
  agreement.
- **Agent:** mark a conflict with a `> [!contradiction]` callout and leave the decision to
  the owner. Never resolve it by rewriting one side.

## 2. A citation looks like proof and is not

Grounding answers in your own sources reduces invention, but does not remove it. The model
can still connect two facts that no source connects. A citation shows only that a file
name was written next to a claim. A tidy note with sources and links looks
authoritative, so it gets checked less than a chat reply would.

What to do:

- **Owner:** on notes you are about to act on, pick a claim at random and find it in the
  cited source.
- **Owner:** treat a claim that rests on one source as one source's view.
- **Agent:** keep what the notes say apart from what you infer. A saved answer lists the
  notes it rests on and marks its inferences.
- **Agent:** the lint warning for missing source files catches paths that lead nowhere,
  not claims a source never made. Do not present a clean source check as verification.

## 3. The context ceiling

The indexes let the agent open only the notes it needs. As the base grows, a catalog
section stops fitting in one read. The agent then either reads more than it should or
misses notes, and answers start to have blind spots. Long sources lose detail in the
middle when they are read in one pass.

What to do:

- **Owner:** keep `summary:` to one line, split folders that grow too large, and keep
  unrelated fields in separate bases.
- **Owner:** run `/b:reindex` when the indexes drift.
- **Agent:** when you could not read everything relevant, say which parts you skipped.
  Do not answer as if you had read them.

## 4. Every operation costs

Every ingest, question and lint spends tokens. A careful ingest that updates five notes
costs more than one that writes a single summary, and that difference is the price of the
method.

What to do:

- **Owner:** use the strongest model for ingest and hard questions. A cheaper one is fine
  for reindexing and formatting.
- **Owner:** `/b:ingest --batch` is cheaper and gives thinner notes, because nobody
  corrects the reading. Use it for a backlog, not for sources you care about.
- **Owner:** `/b:qa --no-save` skips saving a question you will not need again.

## 5. One model's reading

The whole base is one model's reading of your sources, with that model's habits built
in. You will not see them, because everything you read went through the same filter.

What to do:

- **Owner:** for a decision that matters, ask a second model the same question against
  the same notes and compare the answers. Look where they disagree.
- **Agent:** do not present the base agreeing with itself as independent confirmation.

## Tidy is not true

A clean `/b:lint` means the frontmatter, links, indexes and source paths are in order.
It says nothing about whether the content is right. Keep the two apart, in reports and in
answers.

You can add limits of your own to this file. An upgrade keeps your edits and asks only
when the template changed the same file.
