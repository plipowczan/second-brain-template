#!/usr/bin/env python3
"""brain-upgrade engine (standard library only). Run it from the template version you
are installing, against your base:

  python <source>/.claude/skills/brain-upgrade/scripts/upgrade.py plan --instance <base> ...

Subcommands:
  plan    [--source DIR|ZIP] [--ref REF] [--to VERSION] [--adopt] [--base DIR|ZIP]
          [--rerender] [--diff PATH|all] [--out FILE]
          Dry run. Writes a JSON plan to the temp directory and prints a summary; changes
          nothing in the base. Without --source it downloads the release archive.
  apply   --plan FILE --decisions FILE
          Checks every planned path, then writes the approved actions and the stamp.
  commit  --plan FILE
          One git commit with exactly the applied paths, the stamp and .kb-onboard.json.
  stamp   Records the current files as the baseline (used by /b:onboard).
  prune-author
          Deletes author-class files from a fresh clone (used by /b:onboard).
  fetch   [--source DIR|ZIP] [--to VERSION]
          Resolves a source (downloading if needed), unpacks archives to the temp
          directory and prints where that version's engine is.

Every subcommand takes --instance (default: the current directory).
Exit codes: 0 ok, 1 refused or failed (nothing written unless the message says so).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kbtemplate as kt  # noqa: E402
import planner  # noqa: E402
import sources  # noqa: E402

CHOICES = ("keep", "overwrite", "merge")


def say(msg: str = "") -> None:
    print(msg)


def refuse_in_source(instance: Path) -> None:
    if (instance / "CLAUDE.local.md").exists():
        raise kt.TemplateError(
            f"{instance} has CLAUDE.local.md: this looks like the template source, not a "
            "knowledge base. Nothing was changed. Try it in a scratch clone instead.")


# --- plan ----------------------------------------------------------------------------

def write_plan(plan: dict, out: Path | None, instance: Path) -> Path:
    payload = plan.pop("_payload", {})
    if out is None:
        stamp = kt.utc_now().replace(":", "").replace("-", "")
        out = sources.private_dir() / f"plan-{instance.name}-{plan['mode']}-{stamp}.json"
    out = out.resolve()
    pdir = out.with_suffix(".files")
    if pdir.exists():
        shutil.rmtree(pdir)
    for key, data in payload.items():
        target = pdir / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    plan["payload"] = str(pdir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(kt.dump_json(plan))
    return out


def payload_bytes(plan: dict, key: str) -> bytes | None:
    p = Path(plan["payload"]) / key
    return p.read_bytes() if p.is_file() else None


def verified(plan: dict, key: str, want: str | None) -> bytes:
    """Payload bytes whose hash equals the one the plan recorded; anything else (a
    missing or replaced file in the temp directory) stops apply before any write."""
    data = payload_bytes(plan, key)
    if data is None or want is None or kt.content_hash(data) != want:
        raise kt.TemplateError(
            f"the plan's copy of {key} is missing or does not match the plan. Nothing was "
            "written. Run plan again.")
    return data


def print_diffs(plan: dict, instance: Path, which: str) -> None:
    items = [(a["path"], f"src/{a['path']}") for a in plan["actions"]]
    items += [(e["path"], f"render/{e['path']}") for e in plan["rendered"]
              if e["status"] in ("writable", "edited")]
    shown = False
    for path, key in items:
        if which not in ("all", path):
            continue
        local = instance / path
        old = local.read_bytes() if local.is_file() else None
        text = planner.diff_text(path, old, payload_bytes(plan, key))
        say(text if text else f"(no difference for {path})")
        shown = True
    if not shown:
        say(f"(nothing to diff for {which})")


def cmd_plan(args, opener) -> int:
    instance = Path(args.instance).resolve()
    if not instance.is_dir():
        raise kt.TemplateError(f"--instance {instance}: no such directory")
    stamp = kt.read_stamp(instance)
    if args.adopt and stamp is not None:
        raise kt.TemplateError(
            f"{instance} already has {kt.STAMP}; it is adopted. Run a plain upgrade "
            "(without --adopt). Nothing was changed.")
    if not args.adopt and stamp is None:
        raise kt.TemplateError(
            f"{instance} has no {kt.STAMP}, so brain-upgrade cannot tell template files "
            "from your edits. Adopt the base first: run the same command with --adopt. "
            "Nothing was changed.")
    repo = (stamp or {}).get("repository") or kt.DEFAULT_REPOSITORY
    src = sources.resolve(args.source, ref=args.ref, to=args.to, repository=repo, opener=opener)
    if src.kind == "download":
        say(f"Downloaded {src.location}\n  to {src.archive}\n  (reuse it offline with "
            f"--source {src.archive})")
    if args.adopt:
        plan = planner.plan_adopt(instance, src, base=args.base, opener=opener)
    else:
        plan = planner.plan_upgrade(instance, src, rerender=args.rerender)
    path = write_plan(plan, Path(args.out) if args.out else None, instance)
    say(planner.summary(plan))
    if args.diff:
        print_diffs(plan, instance, args.diff)
    say(f"Plan: {path}")
    if not plan["up_to_date"]:
        say("Nothing has been written. Review the plan, then run apply with --plan and "
            "--decisions.")
    return 0


# --- apply ---------------------------------------------------------------------------

def load_plan(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise kt.TemplateError(f"--plan {path}: no such file")
    plan = json.loads(p.read_text(encoding="utf-8"))
    plan["_path"] = str(p.resolve())
    return plan


def save_plan(plan: dict) -> None:
    path = Path(plan.pop("_path"))
    path.write_bytes(kt.dump_json(plan))
    plan["_path"] = str(path)


def plan_instance(plan: dict, given: str | None) -> Path:
    instance = Path(given or plan["instance"]).resolve()
    if str(instance) != plan["instance"]:
        raise kt.TemplateError(f"the plan is for {plan['instance']}, not {instance}")
    return instance


def stale_paths(plan: dict, instance: Path) -> list[str]:
    stale = []
    if kt.file_hash(instance / kt.STAMP) != plan["stamp_before"]:
        stale.append(kt.STAMP)
    if kt.file_hash(instance / kt.ONBOARD_VALUES) != plan["onboard_before"]:
        stale.append(kt.ONBOARD_VALUES)
    for item in plan["actions"] + plan["rendered"]:
        if planner.local(instance, item["path"]) != item["L"]:
            stale.append(item["path"])
    return sorted(set(stale))


def may_touch(rel: str, role: str) -> bool:
    """`role` is "action" (a planned add/update/delete), "render" (a requested re-render)
    or "own" (apply's own bookkeeping: the stamp and .kb-onboard.json)."""
    if role == "own":
        return rel in (kt.STAMP, kt.ONBOARD_VALUES)
    if not kt.protected(rel):
        return True
    return role == "render" and rel == kt.WRITING_STYLE


def target_of(instance: Path, rel: str, role: str) -> Path:
    """The file a planned path names, checked before anything is written: a safe relative
    path that this role may touch, which resolves to that same path inside the base. A
    link, a junction or a Windows short name (CONTEN~1) that leads elsewhere, even
    elsewhere inside the base, is refused."""
    kt.check_paths([rel], "apply")
    if not may_touch(rel, role):
        raise kt.TemplateError(f"apply: refusing to touch {rel}, which belongs to the base. "
                               "Nothing was written.")
    root = instance.resolve()
    target = (root / rel).resolve()
    if root not in target.parents:
        raise kt.TemplateError(f"apply: {rel} resolves outside the base ({target}). "
                               "Nothing was written.")
    if target.relative_to(root).as_posix().casefold() != rel.casefold():
        raise kt.TemplateError(f"apply: {rel} resolves to {target.relative_to(root).as_posix()} "
                               "through a link or an alias. Nothing was written.")
    return target


def _write(path: Path, data: bytes) -> None:
    """Replace a file in one step: write a sibling temp file, then rename it over."""
    tmp = path.with_name(path.name + ".kb-upgrade-tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _unlink(path: Path) -> None:
    path.unlink()


def resolve_mutations(instance: Path, mutations: list) -> list:
    """(path, bytes | None, role) -> (path, target, bytes | None), every target checked."""
    kt.check_paths([rel for rel, _, _ in mutations], "apply")
    return [(rel, target_of(instance, rel, role), data) for rel, data, role in mutations]


def transaction(instance: Path, items: list) -> None:
    """Apply (path, target, bytes | None for delete) in order, all or nothing.

    Before the first change it journals each target's previous bytes (or that it did not
    exist). On any failure it puts every touched target back, removes the files and the
    folders it created, and raises: the base is then as it was before apply.
    """
    journal = [(t, t.read_bytes() if t.is_file() else None) for _, t, _ in items]
    mutations = [(rel, data) for rel, _, data in items]
    created: list[Path] = []
    step = -1
    try:
        for step, ((rel, data), (target, before)) in enumerate(zip(mutations, journal)):
            if data is None:
                if before is not None:
                    _unlink(target)
                continue
            missing = []
            d = target.parent
            while not d.exists():
                missing.append(d)
                d = d.parent
            for d in reversed(missing):
                d.mkdir()
                created.append(d)
            _write(target, data)
    except BaseException as e:
        failed_rel = mutations[step][0] if step >= 0 else "?"
        problems = []
        for target, before in reversed(journal[:step + 1]):
            try:
                if before is None:
                    if target.exists():
                        _unlink(target)
                elif not target.is_file() or target.read_bytes() != before:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    _write(target, before)
            except BaseException as err:  # keep going: restore as much as possible
                problems.append(f"{target.relative_to(instance.resolve())} ({err})")
        for d in reversed(created):
            try:
                d.rmdir()
            except OSError:
                pass
        if problems:
            raise kt.TemplateError(
                f"apply failed at {failed_rel} ({e}), and these could not be put back: "
                + "; ".join(problems) + ". Restore them from git (git status) or the backup "
                "folder before anything else.") from e
        raise kt.TemplateError(
            f"apply failed at {failed_rel} ({e}). Every change was rolled back: the base "
            "is as it was before apply. Fix the cause (a locked file, a full disk) and run "
            "apply again.") from e


def remove_empty_dirs(instance: Path, start: Path) -> None:
    instance = instance.resolve()
    d = start
    while d != instance and instance in d.parents:
        try:
            d.rmdir()
        except OSError:
            return
        d = d.parent


def cmd_apply(args) -> int:
    plan = load_plan(args.plan)
    instance = plan_instance(plan, args.instance)
    if plan.get("applied"):
        raise kt.TemplateError("this plan was already applied; run plan again for a new one")
    decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    if decisions.get("approve") is False:
        say("Plan rejected: nothing was written.")
        return 0
    if plan["up_to_date"]:
        say("Up to date: nothing to apply.")
        return 0
    # The plan sat in a temp folder: check its paths like any untrusted input before
    # reading anything through them.
    planner.check_invariants(plan)
    kt.check_paths([e["template"] for e in plan["rendered"]], "the plan's templates")

    stale = stale_paths(plan, instance)
    if stale:
        raise kt.TemplateError(
            "changed since the dry run: " + ", ".join(stale) +
            ". Nothing was written. Run plan again and review the new plan.")

    chosen = decisions.get("actions", {})
    known = {a["path"] for a in plan["actions"]}
    unknown = sorted(set(chosen) - known)
    if unknown:
        raise kt.TemplateError("decisions name paths that are not in the plan: " + ", ".join(unknown))
    writes, deletes, merges, unresolved = [], [], [], []
    for a in plan["actions"]:
        d = chosen.get(a["path"])
        if a["kind"] == "conflict":
            choice = d if d in CHOICES else None
            if choice is None:
                unresolved.append(a["path"])
            elif choice == "overwrite":
                writes.append(a)
            elif choice == "merge":
                merges.append(a)
            continue
        if a["kind"] == "keep":
            continue
        selected = d if isinstance(d, bool) else a["selected"]
        if selected:
            (deletes if a["kind"] in ("delete", "author-delete") else writes).append(a)
    if unresolved:
        raise kt.TemplateError(
            "choose keep, overwrite or merge for: " + ", ".join(unresolved) +
            ". Nothing was written.")

    rr = decisions.get("rerender")
    if rr is True:
        requested = {e["path"] for e in plan["rendered"]}
    elif isinstance(rr, list):
        requested = set(rr)
    else:
        requested = {e["path"] for e in plan["rendered"] if e["requested"]}
    if plan["mode"] == "adopt":
        requested = set()
    new_values = decisions.get("values") or {}
    renders, proposals = [], []
    for e in plan["rendered"]:
        if e["path"] not in requested or e["status"] == "current":
            continue
        if not e["writable"]:
            proposals.append(e["path"])
            continue
        values = planner.read_values(instance)
        if values is None:
            proposals.append(e["path"])
            continue
        values.update(new_values)
        tpl = verified(plan, f"template/{e['template']}", e["S_template"])
        code = verified(plan, "render.py", plan.get("render_py"))
        out, missing, err = planner.render(code, tpl, values)
        if missing or err:
            raise kt.TemplateError(
                f"cannot re-render {e['path']}: " + (err or "missing values for " + ", ".join(missing)) +
                ". Add them under \"values\" in the decisions. Nothing was written.")
        renders.append((e, out))

    blobs = {a["path"]: verified(plan, f"src/{a['path']}", a["S"]) for a in writes}
    s = plan["stamp"]
    rendered = dict(s["rendered"])
    for e, out in renders:
        rendered[e["path"]] = {"template": e["template"], "template_hash": e["S_template"],
                               "output_hash": kt.content_hash(out)}
    stamp = kt.make_stamp(s["repository"], s["version"], s["commit"], s["files"], rendered,
                          s.get("seeded"))
    mutations = [(a["path"], blobs[a["path"]], "action") for a in writes]
    mutations += [(a["path"], None, "action") for a in deletes]
    mutations += [(e["path"], out, "render") for e, out in renders]
    if new_values:
        values = planner.read_values(instance) or {}
        values.update(new_values)
        mutations.append((kt.ONBOARD_VALUES, kt.dump_json(values), "own"))
    mutations.append((kt.STAMP, kt.dump_json(stamp), "own"))  # last: it names the new version
    # Every target is checked here, before the dirty check, the backup or any write.
    items = resolve_mutations(instance, mutations)
    for a in merges:
        target_of(instance, a["path"], "action")

    targets = [a["path"] for a in writes + deletes + merges] + [e["path"] for e, _ in renders]
    if plan["git"]:
        dirty = planner.dirty_paths(instance, targets)
        if dirty:
            raise kt.TemplateError(
                "uncommitted changes in planned paths: " + ", ".join(dirty) +
                ". Commit or stash them, then run apply again. Nothing was written.")

    backup = None
    if not plan["git"]:
        when = kt.utc_now().replace(":", "").replace("-", "")
        backup = instance.resolve() / kt.BACKUP_DIR / f"{plan['to_version']}-{when}"
        for rel, target, _ in items:
            if target.is_file():
                dst = backup / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, dst)

    transaction(instance, items)
    for rel, target, data in items:
        if data is None:
            remove_empty_dirs(instance, target.parent)

    plan["applied"] = {
        "time": kt.utc_now(),
        "written": sorted(a["path"] for a in writes) + sorted(e["path"] for e, _ in renders),
        "deleted": sorted(a["path"] for a in deletes),
        "merge": sorted(a["path"] for a in merges),
        "onboard_values": bool(new_values),
        "backup": str(backup) if backup else None,
    }
    save_plan(plan)
    ap = plan["applied"]
    say(f"Applied: {len(ap['written'])} written, {len(ap['deleted'])} deleted; "
        f"{kt.STAMP} now names {s['version']}.")
    for p in ap["written"]:
        say(f"  wrote   {p}")
    for p in ap["deleted"]:
        say(f"  deleted {p}")
    if ap["merge"]:
        say("Waiting for a merge with the owner (the file is unchanged so far): "
            + ", ".join(ap["merge"]))
    if proposals:
        say("Not re-rendered (edited by hand or no render inputs; proposal only): "
            + ", ".join(proposals))
    if backup:
        say(f"Backup of every replaced or deleted file: {backup}")
    return 0


# --- commit --------------------------------------------------------------------------

def cmd_commit(args) -> int:
    plan = load_plan(args.plan)
    instance = plan_instance(plan, args.instance)
    applied = plan.get("applied")
    if not applied:
        raise kt.TemplateError("this plan has not been applied yet; run apply first")
    if not kt.is_git_root(instance):
        say("Not a git repository: nothing to commit."
            + (f" Backup: {applied['backup']}" if applied.get("backup") else ""))
        return 0
    if plan.get("committed"):
        raise kt.TemplateError(f"already committed as {plan['committed']}")
    paths = applied["written"] + applied["deleted"] + applied["merge"] + [kt.STAMP]
    onboard = applied["onboard_values"] or plan["track_onboard"]
    present = [p for p in paths if (instance / p).exists() or planner.tracked(instance, p)]
    if present:
        kt.git(instance, "add", "-A", "--", *present)
    if onboard and (instance / kt.ONBOARD_VALUES).is_file():
        kt.git(instance, "add", "-f", "--", kt.ONBOARD_VALUES)
        present.append(kt.ONBOARD_VALUES)
    if kt.git(instance, "diff", "--cached", "--quiet", "--", *present, check=False).returncode == 0:
        say("Nothing to commit.")
        return 0
    repo, version = plan["repository"], plan["stamp"]["version"]
    subject = (f"chore(template): adopt {repo} {version}" if plan["mode"] == "adopt"
               else f"chore(template): upgrade to {repo} {version}")
    src = plan["source"]
    body = (f"Source: {src['kind']} {src['location']}"
            + (f" ({src['commit']})" if src.get("commit") else "")
            + f"\n{len(applied['written'])} written, {len(applied['deleted'])} deleted"
            + (f", merged by hand: {', '.join(applied['merge'])}" if applied["merge"] else ""))
    kt.git(instance, "commit", "-q", "-m", subject, "-m", body, "--", *present)
    sha = kt.head_commit(instance)
    plan["committed"] = sha
    save_plan(plan)
    say(f"Committed {sha[:12]}: {subject}")
    return 0


# --- stamp and onboarding helpers ----------------------------------------------------

def walk(instance: Path) -> list[str]:
    return sources.read_dir_paths(instance)


def cmd_stamp(args) -> int:
    instance = Path(args.instance).resolve()
    refuse_in_source(instance)
    if (instance / kt.STAMP).exists() and not args.force:
        raise kt.TemplateError(f"{kt.STAMP} already exists; pass --force to replace it")
    man = kt.Manifest.load(instance)
    git = kt.is_git_root(instance)
    paths = kt.tracked_files(instance) if git else walk(instance)
    owned, seeded = {}, {}
    for p in paths:
        c = man.classify(p)
        h = kt.file_hash(instance / p)
        if h is None:
            continue
        if c == "owned":
            owned[p] = h
        elif c == "seeded":
            seeded[p] = h
    rendered = {}
    for out, template in man.rendered.items():
        t, o = kt.file_hash(instance / template), kt.file_hash(instance / out)
        if t and o:
            rendered[out] = {"template": template, "template_hash": t, "output_hash": o}
    commit = None
    if git:
        head, tag = kt.head_commit(instance), kt.tag_commit(instance, f"v{man.version}")
        commit = head if head and head == tag else None
    stamp = kt.make_stamp(man.repository, man.version, commit, owned, rendered, seeded)
    kt.write_stamp(instance, stamp)
    say(f"Wrote {kt.STAMP}: version {man.version}, commit {commit or 'null'}, "
        f"{len(owned)} owned files, {len(rendered)} rendered files.")
    return 0


def cmd_prune_author(args) -> int:
    instance = Path(args.instance).resolve()
    refuse_in_source(instance)
    man = kt.Manifest.load(instance)
    gone = []
    for p in walk(instance):
        if man.classify(p) == "author":
            target = instance / p
            target.unlink()
            remove_empty_dirs(instance, target.parent)
            gone.append(p)
    say(f"Deleted {len(gone)} template-development files"
        + (": " + ", ".join(gone) if gone else "."))
    return 0


def cmd_fetch(args, opener) -> int:
    src = sources.resolve(args.source, ref=args.ref, to=args.to,
                          repository=args.repo or kt.DEFAULT_REPOSITORY, opener=opener)
    if src.kind in ("zip", "download"):
        name = (src.manifest.repository if src.manifest else args.repo or kt.DEFAULT_REPOSITORY)
        tag = (src.commit or "unknown")[:12]
        root = sources.private_dir() / f"{name.split('/')[-1]}-{src.version}-{tag}"
        src.materialize(root)
    else:
        root = Path(src.location).resolve()
    engine = root / ".claude" / "skills" / "brain-upgrade" / "scripts" / "upgrade.py"
    say(json.dumps({"source": src.describe(), "root": str(root), "engine": str(engine),
                    "engine_exists": engine.is_file(), "warnings": src.warnings}, indent=2))
    return 0


# --- CLI -----------------------------------------------------------------------------

def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Update a knowledge base from its template.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="dry run: write a plan, change nothing")
    p.add_argument("--instance", default=".")
    p.add_argument("--source", help="template clone, unpacked release, or release .zip")
    p.add_argument("--ref", help="git ref of a clone source (default: tag v<version>)")
    p.add_argument("--to", help="version to download (default: latest release)")
    p.add_argument("--adopt", action="store_true", help="adopt a base that has no stamp")
    p.add_argument("--base", help="adoption: release archive or folder of the nearest release")
    p.add_argument("--rerender", action="store_true", help="re-render untouched instruction files")
    p.add_argument("--diff", metavar="PATH|all", help="also print diffs")
    p.add_argument("--out", help="where to write the plan (default: temp directory)")

    p = sub.add_parser("apply", help="apply a reviewed plan")
    p.add_argument("--instance")
    p.add_argument("--plan", required=True)
    p.add_argument("--decisions", required=True)

    p = sub.add_parser("commit", help="commit an applied plan (git only)")
    p.add_argument("--instance")
    p.add_argument("--plan", required=True)

    p = sub.add_parser("stamp", help="record the current files as the template baseline")
    p.add_argument("--instance", default=".")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("prune-author", help="delete author-class files (onboarding)")
    p.add_argument("--instance", default=".")

    p = sub.add_parser("fetch", help="resolve a source and print its engine path")
    p.add_argument("--source")
    p.add_argument("--ref")
    p.add_argument("--to")
    p.add_argument("--repo")
    return ap


def main(argv=None, opener=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = parser().parse_args(argv)
    opener = opener or sources.default_open
    try:
        if args.cmd == "plan":
            return cmd_plan(args, opener)
        if args.cmd == "apply":
            return cmd_apply(args)
        if args.cmd == "commit":
            return cmd_commit(args)
        if args.cmd == "stamp":
            return cmd_stamp(args)
        if args.cmd == "prune-author":
            return cmd_prune_author(args)
        return cmd_fetch(args, opener)
    except kt.TemplateError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
