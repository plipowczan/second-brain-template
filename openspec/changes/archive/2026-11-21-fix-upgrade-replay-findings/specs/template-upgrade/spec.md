## RENAMED Requirements

- FROM: `### Requirement: Rendered files are re-rendered on request, or after a breaking release, and only if untouched`
- TO: `### Requirement: Rendered files are re-rendered on request, or when the template of AGENTS.md changed, and only if untouched`

## MODIFIED Requirements

### Requirement: Rendered files are re-rendered on request, or when the template of AGENTS.md changed, and only if untouched

brain-upgrade SHALL re-render `CLAUDE.md`, `AGENTS.md` and `content/WRITING_STYLE.md` when
the owner asks for it. It SHALL also re-render `AGENTS.md`, and no other file, unless the
owner declines, when the source's template for it differs from the template hash the stamp
records for it, whether or not the update range holds a **BREAKING** entry. It SHALL
render from the source's templates and `.kb-onboard.json`, and SHALL write the result only
if the local file matches the stamp's output hash, which a `null` hash never does.
Otherwise it SHALL show a proposal and leave the file unchanged, and the summary SHALL say
whether the file was edited or cannot be proven untouched because its output hash is
`null`.

#### Scenario: Untouched file, re-render requested
- **WHEN** the owner requests a re-render and `AGENTS.md` matches its recorded output hash
- **THEN** `AGENTS.md` is rewritten from the new template and the stamp records the new hashes

#### Scenario: Breaking release, untouched file
- **WHEN** the update range holds a **BREAKING** entry, the source's `AGENTS.template.md` differs from the stamp's template hash for `AGENTS.md`, no re-render was requested, and `AGENTS.md` matches its recorded output hash
- **THEN** the plan says `AGENTS.md` will be re-rendered and why, and without a refusal it is rewritten, while `content/WRITING_STYLE.md` and `CLAUDE.md` stay unchanged

#### Scenario: No breaking entry
- **WHEN** the update range holds no **BREAKING** entry, the template for `AGENTS.md` changed, no re-render was requested, and `AGENTS.md` matches its recorded output hash
- **THEN** `AGENTS.md` is re-rendered by default all the same, and the other rendered files stay unchanged

#### Scenario: Breaking release, owner declines
- **WHEN** the template for `AGENTS.md` changed and the owner declines the re-render
- **THEN** `AGENTS.md` is not written, the stamp keeps its old template hash, and the next dry run offers the re-render again

#### Scenario: Template unchanged
- **WHEN** the template for `AGENTS.md` equals the stamp's template hash and no re-render was requested
- **THEN** no rendered file is written, even when the update range holds a **BREAKING** entry or the rendering would differ

#### Scenario: Hand-edited file
- **WHEN** `AGENTS.md` differs from its recorded output hash
- **THEN** the file is not written, and the difference to a fresh rendering is shown as a proposal

#### Scenario: Output hash not recorded
- **WHEN** the stamp records `null` as the output hash of `AGENTS.md` and its template changed
- **THEN** the file is not written, the summary says it cannot be proven untouched, and a fresh rendering is shown as a proposal

#### Scenario: Proposal taken whole
- **WHEN** the owner replaces a `null`-hash `AGENTS.md` with the fresh rendering, commits it and plans again
- **THEN** the file is reported as current, `apply` records its output hash in the stamp, and a later change to its template re-renders it by default

#### Scenario: New placeholder without a value
- **WHEN** the new template uses a placeholder that `.kb-onboard.json` has no value for
- **THEN** the owner is asked for the value, it is saved to `.kb-onboard.json`, and the render proceeds

#### Scenario: Render inputs missing
- **WHEN** `.kb-onboard.json` does not exist
- **THEN** rendered files are only reported as proposals
