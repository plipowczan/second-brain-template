# Tasks

The design is waiting for Paweł's review (proposed 2026-11-09, revised after the EGM
review on 2026-11-16). Nothing below starts before he accepts `design.md`. Merge `main`
into this branch first.

Terms:

- **The generator** is `dev/build_codex_files.py`; **the check** is
  `python dev/build_codex_files.py --check`.
- **The migration output** is what Codex's `/import` wrote (proposal, Why).
- **A scratch clone** is `git clone . ../<name>`, outside this checkout's folder.

Rules for every task: stage files by name (`git add -- <path>`), never with `git add -A`.
A commit that changes a shipped file adds to the `CHANGELOG.md` entry under
`[Unreleased]` in the same commit. After each section, `python tests/run_tests.py` ends
with `ALL PASS`.

## 0. Before any code (D2, D3, D5, D9)

- [ ] 0.1 In the maintainer's checkout, where `git status` lists `.agents/` and `.codex/`
  as untracked, copy both folders to a folder outside any repository (the input of task
  6.3), then delete them. Done when `git status` lists neither and the copy exists.
- [ ] 0.2 In a scratch clone named `kb-codex-trial`, write two stubs by hand as D3 shows
  (`brain-reindex`, `excalidraw-diagram`) and `.codex/hooks.json` as D5 shows. Copy the
  clone without its `.git` folder to a second folder, the ZIP base. Done when both folders
  hold the three files.
- [ ] 0.3 Run the trial in Codex on Windows (PowerShell). Record the Codex version.
  - Start Codex in the clone's root, trust the project, approve the hook in `/hooks`.
    Expected: the session starts with the vault map.
  - Run `$brain-reindex`. Expected: the agent reads `.claude/skills/brain-reindex/SKILL.md`
    and runs its script.
  - Ask `$excalidraw-diagram` for a small diagram. Expected: the agent reads files under
    `.claude/skills/excalidraw-diagram/references/`.
  - Start Codex in `content/`. Expected: the hook fails and the session still starts.
  - Start Codex in the root of the ZIP base, trust it, approve the hook. Expected: `/skills`
    lists both stubs, and the session starts with the vault map.
  - On Linux or macOS, if one is at hand, repeat the first step; otherwise record the gap.
- [ ] 0.4 Read the Copilot and Cursor docs: does either read `.agents/skills/` as well as
  `.claude/skills/`?
- [ ] 0.5 Record the results of 0.3 and 0.4 in `review.md`. If Codex did not follow a
  stub, stop and ask Paweł: the design then switches to the full-copy fallback of D3. Done
  when the results are recorded and, if needed, Paweł has answered.

## 1. Generator and its tests (D1, D3, D4, D5)

- [ ] 1.1 Write `dev/test_build_codex_files.py` first. It builds a temporary git tree as
  `dev/test_check_manifest.py` does and runs the generator with `--root`. One test per
  case:
  - a stub is the source's frontmatter lines, unchanged, plus the fixed body of D3 with
    the skill's name; nothing else is written under `.agents/skills/<skill>/`;
  - `.codex/hooks.json` equals the content in D5;
  - a second run of the generator changes nothing;
  - `--check` writes nothing;
  - `--check` fails, and its output names the path, for each of: a stale stub, a missing
    stub, a missing `hooks.json`, a `hooks.json` with an absolute path, a directory under
    `.agents/skills/` with no source (`source-command-b-qa`), and a stray file in a
    stub's folder;
  - `--check` fails, and its output names the skill and the field, for each of: no
    frontmatter block, invalid YAML, a missing or non-string `name` or `description`, and
    an unquoted description that contains ` #`;
  - a stub with CRLF line endings and a source with LF is not a difference;
  - paths the manifest excludes (`__pycache__/`, `.DS_Store`) under `.agents/skills/` are
    skipped, and a git-ignored Markdown file under `.claude/skills/` (an excalidraw
    `.venv/`) is not read;
  - write mode deletes a file under `.agents/skills/` that has no source, and writes
    nothing when a source frontmatter fails.

  Done when every test runs and fails only because the generator does not exist yet.
- [ ] 1.2 Write the generator as D1, D3 and D5 say:
  - Command line: `python dev/build_codex_files.py [--root PATH] [--check]`. The root
    defaults to the repository the script is in, as in `dev/check_manifest.py`.
  - Build it on `kbtemplate` as `dev/check_manifest.py` does. The skills are the
    directories under `.claude/skills/` whose `SKILL.md` is tracked and classed `owned`
    (`tracked_files`, `Manifest.classify`). Compare files with `content_hash`. The scan of
    `.agents/skills/` reads the disk and skips `Manifest.excluded` paths.
  - The frontmatter block runs from the first line `---` to the next line `---`. Parse it
    with `yaml.safe_load`. When a `description` is unquoted on one line, its parsed value
    must equal the rest of that line.
  - Write stubs with `Path.write_bytes`, so no file gets the executable bit.
  - Print one line per problem, `<kind>: <path>: <reason>`, as `dev/check_manifest.py`
    does. Exit 1 on any problem, 0 otherwise.
  - `.codex/hooks.json` has no `additionalContextLimit` unless Paweł sets a value under
    "Vault map size in Codex" in `design.md`.

  Done when the 1.1 tests pass. `tests/run_tests.py` already runs `python -m unittest` in
  `dev/`, so it picks the tests up.

## 2. Source frontmatter (D4)

- [ ] 2.1 Run the check on the merged tree and fix exactly the frontmatter problems it
  reports. Expected: `brain-export` and `brain-ingest`. Wrap each description in single
  quotes and leave its text unchanged (double any `'` inside). Done when the check reports
  no frontmatter problem; it still reports the missing Codex files until section 3.
- [ ] 2.2 In the `brain-export` and `brain-import` descriptions, write `/b:import` and
  `/b:export` where they say `/import` and `/export`. Change no other text.
- [ ] 2.3 Run `python tests/run_skill_tests.py`; it passes. Commit 2.1 and 2.2 with a
  `Fixed` line in `CHANGELOG.md`.

## 3. Manifest and Codex files (D3, D5, D7)

- [ ] 3.1 Add `.agents/skills/**` and `.codex/hooks.json` to `owned` in `.kb-manifest.json`.
- [ ] 3.2 Run the generator. Stage `.kb-manifest.json`, `.agents/skills/` and
  `.codex/hooks.json` by name and commit them together, with the `Added` entry in
  `CHANGELOG.md`. Done when the check exits 0, `python dev/check_manifest.py` passes, and
  `git status` shows nothing else under `.agents/` or `.codex/`.
- [ ] 3.3 In `tests/run_tests.py`, run the check right after `dev/check_manifest.py` with
  the existing `run()` helper, and name it in the SKIP message. Done when
  `python tests/run_tests.py` ends with `ALL PASS`, fails after one byte of a stub is
  changed, and passes again after the change is reverted.
- [ ] 3.4 In a scratch clone, commit a `.codex/config.toml`. Expected:
  `python dev/check_manifest.py` fails and names it ("matches no class"). Delete the
  scratch clone.
- [ ] 3.5 `git diff main -- .claude/hooks/load_vault_map.py .claude/settings.json` is
  empty, and a Claude Code session in a scratch clone still starts with the vault map.

## 4. Docs (D6, D8)

- [ ] 4.1 In `ENVIRONMENTS.md`, add a `## Codex` section after "Key cross-tool facts" and
  link it from the Codex row of the tool matrix. Update the "Verified" date, and the
  Codex source link, which now redirects to `learn.chatgpt.com/docs`. The section says:
  - skills come from the stubs in `.agents/skills/`, which point at `.claude/skills/`; the
    session hook comes from `.codex/hooks.json`;
  - start a skill by name, `$brain-ingest` for `/b:ingest`, or pick it from `/skills`;
  - open the base's root folder, trust the project, and approve the hook in `/hooks`;
  - for a ZIP base, what task 0.3 found (run `git init` once, if that was needed);
  - for the five `brain-research*` skills, what task 6.4 found;
  - do not run `/import` in a base;
  - in a base that already ran it, delete the paths D8 lists before upgrading;
  - after adding a skill or editing a description, write or edit its stub by hand (show
    the file from D3);
  - keep `.agents/` and `.codex/` even without Codex: deleting them brings back a
    "restore?" row at every upgrade.
- [ ] 4.2 In `README.md`, section "Works beyond Claude Code", add one line: in Codex,
  start a skill by name, for example `$brain-ingest` for `/b:ingest`; details in
  `ENVIRONMENTS.md`. `README.md` is seeded, so this line reaches new bases only.
- [ ] 4.3 In `AGENTS.template.md`, under "Workflows", add one sentence: an agent without
  slash commands treats `/b:<name>` as the `brain-<name>` skill.
- [ ] 4.4 In `CONTRIBUTING.md`:
  - under "Author tools in `dev/`", add the generator and what the check fails on;
  - under "Before you commit", say: edit skills only in `.claude/skills/`, then run the
    generator; and name the check in step 2 among what `tests/run_tests.py` runs;
  - in the class table, add `.agents/skills/**` and `.codex/hooks.json` to the owned row.
- [ ] 4.5 Complete the `CHANGELOG.md` entry with an "Existing bases" paragraph. It says:
  - the upgrade adds one stub per skill and `.codex/hooks.json`, which Claude Code does
    not read;
  - in Codex, the owner trusts the project and approves the hook in `/hooks`, once per
    clone;
  - after adding a skill or editing a description, the owner edits the stub by hand;
  - the `AGENTS.md` sentence arrives only when the owner re-renders `AGENTS.md`;
  - an owner who ran `/import` deletes, before upgrading, `.agents/skills/<skill>/` for
    each template skill and `.codex/hooks.json` (required), and every
    `.agents/skills/source-command-*`, `.codex/hooks/` and `.codex/agents/` (advised), and
    keeps any skill of their own.

## 5. Integration checks

- [ ] 5.1 `python tests/run_tests.py` and `python tests/run_skill_tests.py` pass on
  Windows, and the `Tests` workflow passes on Linux and Windows.

## 6. Upgrade and Codex sessions

- [ ] 6.1 Make a scratch base from the latest release: clone tag `v0.3.0` into a scratch
  folder, stamp it as `brain-onboard` does
  (`python .claude/skills/brain-upgrade/scripts/upgrade.py stamp`), and commit.
- [ ] 6.2 In the scratch base, run
  `python .claude/skills/brain-upgrade/scripts/upgrade.py plan --source <this checkout> --ref HEAD --allow-repository plipowczan/second-brain-template`.
  Without `--ref HEAD` the plan would install tag `v0.3.0` instead of this branch.
  Expected: the `add` actions include every stub and `.codex/hooks.json`, and no action
  touches `content/`. Record the action list in `review.md`, then apply. Done when `apply`
  completes and commits.
- [ ] 6.3 Make a second scratch base as in 6.1. Put the copy from 0.1 into it at the same
  paths, untracked, and add the owner's own `.agents/skills/my-skill/SKILL.md`. Run `plan`
  as in 6.2, then `apply`, and record in `review.md` what each does. Expected: `plan`
  marks each migrated path at a template path as a conflict, and `apply` writes nothing.
  Then delete the paths D8 lists and run `plan` and `apply` again. Done when `apply`
  completes and commits, every stub under `.agents/skills/` equals the template's, and
  `my-skill` is unchanged.
- [ ] 6.4 In a scratch clone with the generated files, open Codex as in the first step of
  0.3. Run `$brain-reindex`: it runs its script. Run `$brain-onboard`: it renders
  `CLAUDE.md` and `AGENTS.md` once each. Run one `brain-research*` skill: record what the
  agent does where the skill says `Task` and `AskUserQuestion`. Record the results in
  `review.md`.

## 7. Review

- [ ] 7.1 Run Codex review rounds on the pull request until a round reports no P1 or P2
  finding. Record each round in `review.md`.
- [ ] 7.2 Paweł merges.
