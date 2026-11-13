# Privacy rules for /export --public

Optional per-vault overrides for the default redaction policy (see
`.claude/skills/brain-export/SKILL.md` → step 3a). `--public` exports read this
file, and `/b:watch` reads its "Always cut" list. It is underscore-prefixed, so it
is excluded from the site build, the indexes, and can never be packed into a
bundle itself.

Delete this file to run on defaults alone — that is also what happens while
every rule below stays commented out.

This file is committed. A name that must not even appear in the repository (a
client under NDA) goes in the "## Always cut" section of
`content/_privacy.local.md` instead: same format, git-ignored, read by both.

## Always cut (extends the defaults)

Add terms that must never leave this vault, one per line:

<!-- - "Acme Corp" — client, under NDA -->
<!-- - "Project Falcon" — internal codename -->

## Exceptions (overrides the defaults)

Things the defaults would cut but that are public for THIS vault:

<!-- - The vault owner's full name — this vault is published under it -->
<!-- - The company name "MyStudio" — it is my public brand -->

## Notes for the redactor

Free-form guidance the redaction pass should honor:

<!-- - Health topics: cut mentions of specific conditions, general fitness content is fine -->
<!-- - Finance: amounts and holdings are private; the fact that I invest is not -->
