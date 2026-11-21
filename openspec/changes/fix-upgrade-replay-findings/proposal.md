# Proposal

## Why

The replay of `/b:upgrade` from `0.2.1` to `v0.3.0` on `second-brain-demo-recipes`
(2026-11-16, PR #2 there) kept the notes intact and the tests green, and found two defects
that would reach the people the update mail (PL-664) sends down that path:

- **A base past `0.2.0` keeps stale instructions.** `AGENTS.md` is re-rendered by default
  only when the version range holds a **BREAKING** entry. A base that crossed the `0.2.0`
  command rename with an older engine, which re-rendered nothing by default, still lists
  the old command names. The range `0.2.1` → `0.3.0` holds no breaking entry, so the file
  stays stale, although it is untouched and its template changed since it was rendered.
- **Caption de-duplication drops real text** (Codex review of that PR, R1-1, P2). Since
  `a2f6317` (in `0.3.0`), `parse_vtt` drops the lines a cue repeats from the cue before
  it, in every caption file. That is right for YouTube's rolling auto-captions and wrong
  for every other track: cues `A / B` then `B / C` give `A B` and `C`, where `0.2.1` gave
  `A B` and `B C`.

Paweł decided on 2026-11-21: both fixes in one pull request, the re-render tied to the
template, not to a breaking entry.

## What Changes

- **`AGENTS.md` follows its template.** An untouched `AGENTS.md` is re-rendered by default
  whenever its template differs from the one the stamp says it was rendered from. The
  breaking-entry criterion goes. The owner can still decline with `"rerender": []`, and a
  declined re-render is offered again at the next upgrade. An edited file, and a file
  whose output hash is `null`, stay proposals. `CLAUDE.md` and `content/WRITING_STYLE.md`
  still change only on request.
- **The plan says why a file is only a proposal.** A `null` output hash is reported as
  "not provably untouched" instead of "edited by hand", and the skill tells the owner how
  such a file can follow the template again: take the proposal whole, once.
- **Rolling-caption de-duplication only where captions roll.** Lines repeated from the
  previous cue are dropped only in a file that carries YouTube's inline word timestamps.
  Any other track keeps every line, and only a cue identical to the one before it
  coalesces, as in `0.2.1`.

No new commands or options. No breaking change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `template-upgrade`: when `AGENTS.md` is re-rendered by default, and what a `null`
  output hash means for it.

Caption parsing has no capability spec, as with `yt_fetch.py` in `fix-upgrade-path`.

## Impact

- **Code:** `.claude/skills/brain-upgrade/scripts/planner.py` and its tests,
  `.claude/skills/brain-ingest/scripts/yt_fetch.py` and its tests.
- **Docs:** `.claude/skills/brain-upgrade/SKILL.md`, `CHANGELOG.md`.
- **Existing bases:** the re-render rule arrives with the first upgrade to a release that
  contains it, because the engine of the release being installed makes the plan. A base
  whose stamp holds `output_hash: null` for `AGENTS.md`, such as the demo base, still gets
  a proposal: design D2 says why and what the way out is. The caption fix reaches a base
  with the upgrade that replaces `yt_fetch.py`; transcripts already ingested are not
  re-fetched.
- **Maintainer's base:** if `brain-ingest` is on the list of shared skills, the
  `yt_fetch.py` change is ported to `brain` by hand (CONTRIBUTING).
