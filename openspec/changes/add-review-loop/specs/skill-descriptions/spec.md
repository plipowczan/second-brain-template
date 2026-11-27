# Spec Delta

## Purpose

Defines the shape of a skill's description and body, so that the agent picks the right
skill among overlapping ones and every skill ends in a predictable result, while the
descriptions that enter every session stay short.

## ADDED Requirements

### Requirement: New and edited skills follow the description pattern

A skill added or edited after this change SHALL have a single-quoted YAML description
that starts with "Use when" and its trigger phrases, says in one sentence what it does
and what it writes, and, where a neighbouring skill overlaps, names it after "Do NOT use
for". Its body SHALL have a `## Calibration` section with the typical failure and what
right looks like, and SHALL state the shape of the output it ends with.
`CONTRIBUTING.md` SHALL describe the pattern.

#### Scenario: Review and lint
- **WHEN** an agent reads the descriptions of `brain-review` and `brain-lint`
- **THEN** each names the other after "Do NOT use for", so a request for a health audit goes to lint and a request for a look back goes to the review

### Requirement: Descriptions cannot grow without notice

`dev/build_codex_files.py --check` SHALL fail when a skill's description is longer than
500 characters, in addition to its existing checks.

#### Scenario: Long description
- **WHEN** a contributor writes a 520-character description
- **THEN** the check fails and names the skill and the length
