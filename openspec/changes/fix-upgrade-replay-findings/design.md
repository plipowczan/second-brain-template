# Design

## Context

The replay (2026-11-16) upgraded `second-brain-demo-recipes` from `0.2.1` to `v0.3.0` in
its PR #2 and repeated the upgrade on a copy of a base from July, on two paths: one already
upgraded to `0.2.1`, one still on `0.1.0`. Notes stayed intact and tests stayed green.
Two defects remain open from that run, and Paweł decided on 2026-11-21 to fix both in one
pull request.

Facts that shape the decisions:

- The stamp's entry for a rendered file holds `template_hash`, the template the file was
  last rendered from, and `output_hash`, the file that rendering produced. An upgrade that
  does not re-render the file keeps both (`test_not_requested_is_not_written`).
- Adoption writes `output_hash: null` when the local file is not release R's rendering,
  edited or rendered from another template. `null` never matches a file.
- The plan comes from the engine of the release being installed. A change to the default
  reaches a base with its first upgrade to a release that contains it.
- A base on `0.2.0` or `0.2.1` that was adopted from `0.1.0` and upgraded before
  `fix-upgrade-path` has an untouched `AGENTS.md` rendered from the `0.1.0` template, with
  the command names `0.2.0` renamed.

## Goals / Non-Goals

**Goals:** an untouched `AGENTS.md` catches up with its template at the next upgrade,
whatever the version range holds; an edited file is never written; a caption track that
does not roll keeps every line; rolling auto-captions keep each line once.

**Non-Goals:** writing a file the engine cannot prove untouched; re-rendering
`CLAUDE.md` or `content/WRITING_STYLE.md` without a request; rendering older templates to
recognise an old rendering; changing `second-brain-demo-recipes`; re-fetching transcripts
already ingested.

## Decisions

### D1. `AGENTS.md` is re-rendered by default when its template changed

**Decision.** The plan requests `AGENTS.md` by default when the source's
`AGENTS.template.md` differs from the stamp's `template_hash` for it. The breaking-entry
test goes.

| Criterion | Base from `0.1.0`, upgraded to `0.2.1` before `fix-upgrade-path`, now upgrading to `0.3.0` | Verdict |
|---|---|---|
| A **BREAKING** entry in the version range (today) | `0.3.0` and `0.4.0` have none: the old names stay | Rejected: a breaking entry is a proxy for "the instructions changed". It misses every re-render an older engine skipped, and every template change in a release without one: the `0.4.0` sentence about `/b:<name>` in Codex reaches no base by default |
| The template changed within the range | Needs the old version's template, which the history index does not hold; misses a skipped re-render too | Rejected |
| The template differs from the one the file was rendered from | `template_hash` is the `0.1.0` template: re-rendered | **Chosen** |

- Everything else from `fix-upgrade-path` D2 stays: the test of "untouched" (the local
  file matches `output_hash`), `"rerender": []` to decline, `--rerender` for all three
  files, the reason in the summary, a new placeholder stopping `apply` until it has a
  value, adoption writing no rendered file.
- A declined re-render leaves the stamp's `template_hash` as it was, so the next upgrade
  offers it again, the way a declined executable bit comes back. An owner who wants the
  old text for good edits the file, which makes it a proposal.
- When the template is unchanged but the rendering differs (another `render.py`, or values
  edited in `.kb-onboard.json`), nothing is requested by default, with or without a
  breaking entry: the instructions did not change, and the owner's values are theirs to
  apply with `--rerender`. That case is the only one the old criterion covered and this one
  does not.
- When the template changed but renders to the same file, the entry is current and the
  stamp takes the new `template_hash`, as before.
- The default request is made only where `apply` can act on it: write the file, ask for
  a missing value, or report a proposal. Without `.kb-onboard.json` (a second clone of a
  base that never committed it) or with a template that fails to render, a request could
  never be carried out, and since the check for "up to date" counts requested writable
  files, the base would never be reported up to date again.
- `CLAUDE.md` holds only the import of `AGENTS.md`, and `content/WRITING_STYLE.md` is the
  owner's style guide, so both stay on request.

### D2. A `null` output hash: still a proposal, with a way out

**Decision.** A file whose stamp entry has `output_hash: null` stays a proposal, as before.
The engine cannot tell an old rendering from an owner's edit without the old template's
rendered text, and fetching older templates to render them is still out of scope (the
known limit of `fix-upgrade-path` D2). Writing it anyway would break the one promise the
rule makes: an edit is never overwritten.

Two changes make the case visible and leave it a way out:

- The summary says `not provably untouched` for a `null` hash, not `edited by hand`. For
  the demo base, whose `AGENTS.md` differs from the template's rendering only by template
  text, "edited by hand" was wrong.
- The way out already works and is now written down in the skill: when the owner never
  edited the file, or does not need their edits, they take the proposal whole once. Copy
  `payload/render/AGENTS.md` from the plan over `AGENTS.md`, commit it, and plan again. The
  file now matches the fresh rendering, the plan reports it as current, and `apply` records
  its output hash in the stamp. From then on it is untouched, and D1 re-renders it whenever
  its template changes. An owner who wants to keep their edits merges by hand, and the file
  stays a proposal at every upgrade that changes the template.

### D3. Captions: line de-duplication only in rolling auto-captions

**Decision.** `parse_vtt` drops the lines a cue repeats from the cue before it only when
the file carries inline cue timestamps (`<00:00:01.120>`), and treats the whole file the
same way.

| Option | Manual track, cues `A / B` then `B / C` | Verdict |
|---|---|---|
| Drop repeated lines in every file (`0.3.0`) | `A B`, `C` | Rejected: drops text |
| Drop them only when a cue starts where the previous one ended | Manual tracks are usually back to back: `A B`, `C` | Rejected |
| Drop them only in a file with inline word timestamps | `A B`, `B C` | **Chosen** |

- YouTube's automatic captions carry inline word timestamps, and those are the tracks
  that roll: each cue repeats the previous line above the new one. A manual track
  normally has none.
- Any other track keeps the `0.2.1` rule: a cue whose whole text equals the cue before it
  coalesces, and nothing else is dropped.
- A track that rolls without inline timestamps (a roll-up track uploaded by hand) shows
  each line twice, as in `0.2.1`. That repeats text and loses none, which is the safer
  failure.

## Risks / Trade-offs

- **More re-renders by default.** Every release that edits `AGENTS.template.md` now
  rewrites an untouched `AGENTS.md` unless the owner declines. That is the intent: the
  agent reads the file in every session. The Phase 4 table shows the row with a default of
  yes and the reason.
- **A new placeholder stops `apply` more often.** It stops whenever the template gained a
  placeholder, not only after a breaking release. The QUESTION line asks for the value, and
  nothing is written until it is answered.
- **The way out in D2 is manual.** It costs one copy and one extra plan, and only bases
  adopted from an older rendering need it.
