#!/usr/bin/env python3
"""The dry run of brain-upgrade: build a plan, never write to the instance.

- owned files: three-way decision between the stamp baseline B, the source S and the
  local file L (design D6);
- rendered files: re-render only on request and only while untouched (design D7);
- seeded files: information only; author-class leftovers: deleted only when pristine;
- `--adopt`: align an unstamped instance with the nearest release R (design D9).
"""

from __future__ import annotations

import difflib
import json
import types
from pathlib import Path

import kbtemplate as kt
import sources

RENDER_PY = ".claude/skills/brain-onboard/scripts/render.py"


# --- small helpers -------------------------------------------------------------------

def local(instance: Path, path: str) -> str | None:
    return kt.file_hash(instance / path)


def diff_text(path: str, old: bytes | None, new: bytes | None) -> str:
    if (old and kt.is_binary(old)) or (new and kt.is_binary(new)):
        return f"Binary file {path} differs\n"
    a = (old or b"").decode("utf-8", "replace").replace("\r\n", "\n").splitlines(keepends=True)
    b = (new or b"").decode("utf-8", "replace").replace("\r\n", "\n").splitlines(keepends=True)
    return "".join(difflib.unified_diff(a, b, f"a/{path} (local)", f"b/{path} (template)"))


def find_render_py(files: dict[str, bytes]) -> bytes | None:
    if RENDER_PY in files:
        return files[RENDER_PY]
    for path in sorted(files):
        if path.startswith(".claude/skills/") and path.endswith("/scripts/render.py"):
            return files[path]
    return None


def load_renderer(code: bytes) -> types.ModuleType:
    """The render.py of a given template version, loaded from its bytes."""
    mod = types.ModuleType("kb_template_render")
    exec(compile(code, "render.py", "exec"), mod.__dict__)
    return mod


def render(code: bytes | None, template: bytes, values: dict) -> tuple[bytes | None, list[str], str | None]:
    """(output, missing keys, error) for one template rendered with `values`."""
    if code is None:
        return None, [], "no render.py in the template"
    mod = load_renderer(code)
    try:
        out = mod.render(template.decode("utf-8"), values)
    except mod.RenderError as e:
        msg = str(e)
        for prefix in ("missing values for: ", "conditional flag not in values: "):
            if msg.startswith(prefix):
                return None, [k.strip() for k in msg[len(prefix):].split(",")], None
        return None, [], msg
    return out.encode("utf-8"), [], None


def read_values(instance: Path) -> dict | None:
    path = instance / kt.ONBOARD_VALUES
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def tracked(instance: Path, path: str) -> bool:
    return kt.git(instance, "ls-files", "--error-unmatch", "--", path, check=False).returncode == 0


def dirty_paths(instance: Path, paths: list[str]) -> list[str]:
    """Planned paths with uncommitted work (modified, staged or untracked)."""
    if not paths:
        return []
    out = kt.git(instance, "status", "--porcelain", "-z", "--untracked-files=all", "--",
                 *paths).stdout
    found = []
    for rec in out.split("\0"):
        if len(rec) > 3 and rec[2] == " ":
            found.append(rec[3:])
    return sorted(set(found) & set(paths))


def action(path, kind, *, B=None, S=None, L=None, selected=None, note="", warning=""):
    a = {"path": path, "kind": kind, "B": B, "S": S, "L": L, "selected": selected,
         "choice": None, "note": note}
    if warning:
        a["warning"] = warning
    return a


# --- rendered files ------------------------------------------------------------------

def plan_rendered(instance: Path, manifest: kt.Manifest, new_files: dict[str, bytes],
                  previous: dict, requested: bool, *, adopt_files: dict | None = None):
    """Entries for CLAUDE.md, AGENTS.md and content/WRITING_STYLE.md.

    `new_files` is the tree whose templates would be rendered now (the source).
    `previous` holds the stamp's rendered entries (upgrade). For an adoption,
    `adopt_files` is release R's tree: the stamp entry is decided against R's rendering.
    Returns (entries, payload {key: bytes}, questions).
    """
    values = read_values(instance)
    code = find_render_py(new_files)
    entries, payload, questions = [], {}, []
    for out, template in sorted(manifest.rendered.items()):
        tpl = new_files.get(template)
        L = local(instance, out)
        e = {"path": out, "template": template, "L": L, "requested": requested,
             "S_template": kt.content_hash(tpl) if tpl is not None else None,
             "rendered": None, "missing": [], "status": None, "entry": None}
        prev = previous.get(out)
        if adopt_files is not None:
            r_tpl = adopt_files.get(template)
            r_out = None
            if r_tpl is not None and values is not None:
                r_out, _, _ = render(find_render_py(adopt_files), r_tpl, values)
            if r_tpl is not None and L is not None:
                prev = {"template": template, "template_hash": kt.content_hash(r_tpl),
                        "output_hash": L if r_out is not None and kt.content_hash(r_out) == L else None}
            e["requested"] = False
        e["entry"] = prev
        if tpl is None:
            e["status"] = "no-template"
        elif values is None:
            e["status"] = "no-values"
        else:
            out_bytes, missing, err = render(code, tpl, values)
            if err:
                e["status"], e["error"] = "error", err
            elif missing:
                e["status"], e["missing"] = "missing-values", missing
                questions.append({"path": out, "missing": missing})
            else:
                e["rendered"] = kt.content_hash(out_bytes)
                payload[f"render/{out}"] = out_bytes
                if L == e["rendered"]:
                    e["status"] = "current"
                    if adopt_files is None:  # an adoption records R's rendering only
                        e["entry"] = {"template": template, "template_hash": e["S_template"],
                                      "output_hash": L}
                elif prev and prev.get("output_hash") and prev["output_hash"] == L:
                    e["status"] = "writable"
                else:
                    e["status"] = "edited"
        if tpl is not None:
            payload[f"template/{template}"] = tpl
        e["template_changed"] = bool(prev) and tpl is not None and prev.get("template_hash") != e["S_template"]
        e["untouched"] = bool(prev and prev.get("output_hash") and prev["output_hash"] == L)
        if adopt_files is not None:
            e["writable"] = False
        else:
            e["writable"] = e["untouched"]
        entries.append(e)
    if code is not None:
        payload["render.py"] = code
    return entries, payload, questions


# --- seeded and author ---------------------------------------------------------------

def seeded_info(source: sources.Source, previous: dict | None) -> list[dict]:
    """What changed upstream in seeded files since the stamp (information only)."""
    if previous is None:
        return []
    now = {p: source.hash(p) for p in source.by_class()["seeded"]}
    info = []
    for p in sorted(set(now) | set(previous)):
        if p not in previous:
            info.append({"path": p, "change": "added upstream"})
        elif p not in now:
            info.append({"path": p, "change": "removed upstream"})
        elif now[p] != previous[p]:
            info.append({"path": p, "change": "changed upstream"})
    return info


def author_leftovers(instance: Path, source: sources.Source, index: kt.HistoryIndex):
    """Author-class files the template once shipped: pristine ones are proposed for
    deletion; any other content is the owner's and left alone."""
    actions, kept = [], []
    paths = {p for p in index.files if source.manifest.classify(p) == "author"}
    paths |= set(source.by_class()["author"])
    for p in sorted(paths):
        L = local(instance, p)
        if L is None:
            continue
        if index.known(p, L) or L == source.hash(p):
            actions.append(action(p, "author-delete", L=L, selected=True,
                                  note="template-development file the template shipped"))
        else:
            kept.append(p)
    return actions, kept


# --- the plan ------------------------------------------------------------------------

def base_plan(instance: Path, mode: str, source: sources.Source) -> dict:
    stamp_file = instance / kt.STAMP
    return {
        "format": 1,
        "mode": mode,
        "instance": str(instance.resolve()),
        "created": kt.utc_now(),
        "source": source.describe(),
        "base": None,
        "repository": source.manifest.repository,
        "from_version": None,
        "to_version": source.version,
        "stamp_before": kt.file_hash(stamp_file),
        "onboard_before": kt.file_hash(instance / kt.ONBOARD_VALUES),
        "up_to_date": False,
        "changelog": [],
        "actions": [],
        "rendered": [],
        "questions": [],
        "info": {"uptodate": 0, "seeded": [], "ignored": [], "author_kept": []},
        "warnings": list(source.warnings),
        "git": kt.is_git_root(instance),
        "track_onboard": False,
        "stamp": None,
    }


def finish(plan: dict, instance: Path, payload: dict) -> dict:
    """Common warnings: untracked render inputs, uncommitted planned paths."""
    if plan["git"]:
        if (instance / kt.ONBOARD_VALUES).is_file() and not tracked(instance, kt.ONBOARD_VALUES):
            plan["track_onboard"] = True
            plan["warnings"].append(
                f"{kt.ONBOARD_VALUES} is not tracked by git; the commit will add it so "
                "the render inputs travel with the base")
        dirty = dirty_paths(instance, write_paths(plan))
        if dirty:
            plan["warnings"].append(
                "uncommitted changes in planned paths (apply refuses until they are "
                "committed or stashed): " + ", ".join(dirty))
    plan["_payload"] = payload
    return plan


def write_paths(plan: dict) -> list[str]:
    """Every path apply might write or delete under this plan."""
    paths = [a["path"] for a in plan["actions"] if a["kind"] != "keep"]
    paths += [e["path"] for e in plan["rendered"] if e["writable"]]
    return sorted(set(paths))


def plan_upgrade(instance: Path, source: sources.Source, *, rerender: bool = False) -> dict:
    stamp = kt.read_stamp(instance)
    if stamp is None:
        raise kt.TemplateError(
            f"{instance} has no {kt.STAMP}, so brain-upgrade cannot tell template files "
            "from your edits. Adopt the base first: run the same command with --adopt. "
            "Nothing was changed.")
    if kt.parse_version(source.version) < kt.parse_version(stamp["version"]):
        raise kt.TemplateError(
            f"the source is {source.version}, older than this base's {stamp['version']}; "
            "downgrades are not supported. Nothing was changed.")
    plan = base_plan(instance, "upgrade", source)
    plan["from_version"] = stamp["version"]
    changelog = source.files.get("CHANGELOG.md", b"").decode("utf-8", "replace")
    plan["changelog"] = kt.changelog_range(changelog, stamp["version"], source.version)

    S_owned = source.owned()
    B = stamp["files"]
    payload: dict = {}
    for p in sorted(set(S_owned) | set(B)):
        S, b, L = S_owned.get(p), B.get(p), local(instance, p)
        if S is not None:
            if L == S:
                plan["info"]["uptodate"] += 1
                continue
            if b is None:
                a = (action(p, "add", S=S, selected=True) if L is None else
                     action(p, "conflict", S=S, L=L,
                            note="new template file, but this base has its own file here"))
            elif L is None:
                a = action(p, "restore", B=b, S=S, selected=False,
                           note="deleted in this base; stays deleted unless you restore it")
            elif L == b:
                a = action(p, "update", B=b, S=S, L=L, selected=True)
            elif S == b:
                a = action(p, "keep", B=b, S=S, L=L, note="edited in this base; template unchanged")
            else:
                a = action(p, "conflict", B=b, S=S, L=L,
                           note="changed in the template and in this base")
            payload[f"src/{p}"] = source.files[p]
            plan["actions"].append(a)
        else:
            if L is None:
                continue
            if L == b:
                plan["actions"].append(action(p, "delete", B=b, L=L, selected=True,
                                              note="removed from the template"))
            else:
                plan["actions"].append(action(
                    p, "delete", B=b, L=L, selected=False, note="removed from the template",
                    warning="edited in this base: kept unless you select the deletion"))

    leftovers, kept = author_leftovers(instance, source, source.index)
    plan["actions"] += leftovers
    plan["info"]["author_kept"] = kept
    plan["info"]["seeded"] = seeded_info(source, stamp.get("seeded"))
    plan["info"]["ignored"] = source.by_class()[None]

    entries, rpayload, questions = plan_rendered(instance, source.manifest, source.files,
                                                 stamp["rendered"], rerender)
    payload.update(rpayload)
    plan["rendered"], plan["questions"] = entries, questions
    plan["render_py"] = kt.content_hash(rpayload["render.py"]) if "render.py" in rpayload else None

    plan["stamp"] = {
        "repository": source.manifest.repository,
        "version": source.version,
        "commit": source.commit,
        "files": S_owned,
        "seeded": {p: source.hash(p) for p in source.by_class()["seeded"]},
        "rendered": {e["path"]: e["entry"] for e in entries if e["entry"]},
    }
    pending = [a for a in plan["actions"] if a["kind"] != "keep"]
    plan["up_to_date"] = (source.version == stamp["version"] and not pending
                          and not any(e["requested"] and e["writable"] for e in entries))
    return finish(plan, instance, payload)


# --- adoption ------------------------------------------------------------------------

def nearest_release(instance: Path, source: sources.Source) -> tuple[str, dict[str, str], int]:
    """(R, R's owned files {path: hash}, R's state number) — the tagged release no newer
    than the source whose owned files this instance matches best; ties go to the older."""
    index, man = source.index, source.manifest
    top = kt.parse_version(source.version)
    candidates = []
    for version, state in index.releases().items():
        if kt.parse_version(version) <= top:
            files = {p: h for p, h in index.release_files(state).items()
                     if man.classify(p) == "owned"}
            candidates.append((version, files, state))
    if source.version not in index.releases():
        candidates.append((source.version, source.indexed(), len(index.states)))
    if not candidates:
        raise kt.TemplateError("the source knows no release to adopt")
    cache: dict[str, str | None] = {}

    def score(files):
        n = 0
        for p, h in files.items():
            if p not in cache:
                cache[p] = local(instance, p)
            n += cache[p] == h
        return n

    candidates.sort(key=lambda c: kt.parse_version(c[0]))
    scored = [(score(c[1]), -i, c) for i, c in enumerate(candidates)]
    return max(scored, key=lambda s: s[:2])[2]


def base_tree(source: sources.Source, release: str, base: str | None, opener) -> sources.Source:
    """Release R's own content (design D9): the source itself only when it is R's
    release, else the tag of a git-clone source, `--base`, or a download."""
    man, index = source.manifest, source.index
    if release == source.version and source.proven_release(release, index, man):
        return source
    if source.kind == "git" and kt.tag_commit(Path(source.location), f"v{release}"):
        return sources.from_git(Path(source.location), f"v{release}", require_manifest=False)
    if base:
        b = sources.resolve(base, require_manifest=False)
        if b.version not in (None, release) or not (
                b.version == release and b.release
                or b.proven_release(release, index, man)
                or (release == source.version and b.indexed(man) == source.indexed(man))):
            raise kt.TemplateError(
                f"--base {base} is not the release v{release} this adoption needs")
        return b
    try:
        return sources.download(man.repository, release, opener)
    except sources.OfflineError:
        name = man.repository.split("/")[-1]
        raise kt.TemplateError(
            f"adopting this base needs the template release v{release} (the nearest "
            f"release), and it cannot be downloaded (no network?). Nothing was changed. "
            f"Pass it with --base <path to {name}-{release}.zip or an unpacked copy>, or "
            f"use a git clone of {man.repository} as --source.") from None


def plan_adopt(instance: Path, source: sources.Source, *, base: str | None = None,
               opener=sources.default_open) -> dict:
    if kt.read_stamp(instance) is not None:
        raise kt.TemplateError(
            f"{instance} already has {kt.STAMP}; it is adopted. Run a plain upgrade "
            "(without --adopt). Nothing was changed.")
    man, index = source.manifest, source.index
    release, _, _ = nearest_release(instance, source)
    rtree = base_tree(source, release, base, opener)
    R = rtree.owned(man)
    plan = base_plan(instance, "adopt", source)
    plan["to_version"] = release
    plan["base"] = rtree.describe()
    plan["base"]["version"] = release
    changelog = source.files.get("CHANGELOG.md", b"").decode("utf-8", "replace")
    plan["changelog"] = kt.changelog_version(changelog, release)

    owned_index = {p for p in index.files if man.classify(p) == "owned"}
    baselines, payload = {}, {}
    indexed_release = release in index.releases()

    def older(state: int) -> bool:
        return not indexed_release or index.in_release(state, release)

    def last_in_release(path: str) -> str | None:
        found = [(s, h) for h, sts in index.files.get(path, {}).items() for s in sts if older(s)]
        return max(found)[1] if found else None

    for p in sorted(set(R) | owned_index):
        Rh, L = R.get(p), local(instance, p)
        if L is not None and L == Rh:
            plan["info"]["uptodate"] += 1
            baselines[p] = Rh
            continue
        if L is None:
            if Rh is not None:
                plan["actions"].append(action(p, "add", S=Rh, selected=True,
                                              note=f"shipped by {release}; deselect to keep it out"))
                payload[f"src/{p}"] = rtree.files[p]
                baselines[p] = Rh
            continue
        if Rh is not None:
            payload[f"src/{p}"] = rtree.files[p]
        if p == kt.INDEX and Rh is not None:  # generated at release time, follows R
            plan["actions"].append(action(p, "update", S=Rh, L=L, selected=True,
                                          note=f"history index of {release}"))
            baselines[p] = Rh
            continue
        states = index.states_of(p, L)
        if states:  # pristine: some template state shipped exactly this content
            # Older means "in R's history"; a state after R or on a parallel branch is
            # newer, and the file is never rewound to R.
            if any(not older(s) for s in states):
                plan["actions"].append(action(p, "keep", S=Rh, L=L,
                                              note=f"from a template state newer than {release}; not rewound"))
                baselines[p] = L
            elif Rh is not None:
                plan["actions"].append(action(p, "update", S=Rh, L=L, selected=True,
                                              note=f"older template state, moved to {release}"))
                baselines[p] = Rh
            else:
                plan["actions"].append(action(p, "delete", L=L, selected=True,
                                              note=f"older template file that {release} no longer ships"))
        else:
            plan["actions"].append(action(p, "keep", S=Rh, L=L, note="edited in this base"))
            baselines[p] = Rh or last_in_release(p) or index.latest_hash(p)

    leftovers, kept = author_leftovers(instance, source, index)
    plan["actions"] += leftovers
    plan["info"]["author_kept"] = kept

    entries, rpayload, questions = plan_rendered(instance, man, source.files, {}, False,
                                                 adopt_files=rtree.files)
    payload.update(rpayload)
    plan["rendered"], plan["questions"] = entries, []
    plan["render_py"] = kt.content_hash(rpayload["render.py"]) if "render.py" in rpayload else None
    plan["stamp"] = {
        "repository": man.repository,
        "version": release,
        "commit": rtree.commit,
        "files": baselines,
        "seeded": {p: rtree.hash(p) for p in rtree.by_class(man)["seeded"]},
        "rendered": {e["path"]: e["entry"] for e in entries if e["entry"]},
    }
    return finish(plan, instance, payload)


# --- output --------------------------------------------------------------------------

LABEL = {"add": "add", "update": "update", "conflict": "CONFLICT", "restore": "restore?",
         "delete": "delete", "author-delete": "delete", "keep": "keep (yours)"}


def summary(plan: dict) -> str:
    src = plan["source"]
    lines = []
    where = src["location"] + (f" @ {src['ref']}" if src.get("ref") else "")
    lines.append(f"Source: {src['kind']} {where}")
    lines.append(f"  version {src['version']}, commit {src['commit'] or 'unknown'}"
                 + (f", archive {src['archive']}" if src.get("archive") else ""))
    if plan["mode"] == "adopt":
        b = plan["base"]
        lines.append(f"Adoption: this base matches release {plan['to_version']} best; it is "
                     f"aligned with {plan['to_version']} (read from {b['kind']} {b['location']}"
                     + (f" @ {b['ref']}" if b.get("ref") else "") + ").")
        lines.append(f"  The upgrade to {src['version']} is a separate run afterwards.")
    else:
        lines.append(f"Upgrade: {plan['from_version']} -> {plan['to_version']}")
    for w in plan["warnings"]:
        lines.append(f"WARNING: {w}")
    if plan["up_to_date"]:
        lines.append("Up to date: nothing to change.")
        return "\n".join(lines) + "\n"

    lines.append("")
    lines.append("Changelog:" if plan["changelog"] else "Changelog: no entries in this range.")
    for block in plan["changelog"]:
        lines.append(f"  [{block['version']}]" + (f" - {block['date']}" if block.get("date") else ""))
        for s in block["sections"]:
            for e in s["entries"]:
                mark = "!! BREAKING " if e["breaking"] else ""
                lines.append(f"    {s['heading']}: {mark}{e['text'].splitlines()[0]}")

    lines.append("")
    lines.append(f"Files ({plan['info']['uptodate']} already current):")
    if not plan["actions"]:
        lines.append("  no owned file to change")
    for a in plan["actions"]:
        box = "" if a["selected"] is None else ("[x] " if a["selected"] else "[ ] ")
        extra = f" — {a['note']}" if a.get("note") else ""
        warn = f" (!) {a['warning']}" if a.get("warning") else ""
        lines.append(f"  {box}{LABEL[a['kind']]:<12} {a['path']}{extra}{warn}")
    lines.append("")
    lines.append("Instruction files (rendered):")
    for e in plan["rendered"]:
        lines.append(f"  {e['path']}: {render_note(e, plan['mode'])}")
    for q in plan["questions"]:
        lines.append(f"QUESTION: {q['path']} needs values for {', '.join(q['missing'])} "
                     f"(saved to {kt.ONBOARD_VALUES})")
    info = plan["info"]
    if info["seeded"]:
        lines.append("")
        lines.append("Starter content changed upstream (information only, never written):")
        for s in info["seeded"]:
            lines.append(f"  {s['change']}: {s['path']}")
    if info["author_kept"]:
        lines.append("Left alone (template-development paths with your own content): "
                     + ", ".join(info["author_kept"]))
    if info["ignored"]:
        lines.append("Ignored source files (no class in the manifest): " + ", ".join(info["ignored"]))
    return "\n".join(lines) + "\n"


def render_note(e: dict, mode: str) -> str:
    s = e["status"]
    if s == "no-template":
        return "the source has no template for it"
    if s == "no-values":
        return f"{kt.ONBOARD_VALUES} is missing, so changes can only be proposed"
    if s == "missing-values":
        return "the new template needs values: " + ", ".join(e["missing"])
    if s == "error":
        return f"cannot render: {e.get('error')}"
    if s == "current":
        return "matches the new template"
    changed = "template text changed upstream; " if e.get("template_changed") else ""
    if mode == "adopt":
        return ("not written during adoption; " +
                ("untouched, so later upgrades may re-render it" if e["entry"] and e["entry"].get("output_hash")
                 else "edited (or not provable), so later upgrades only propose") +
                "; differs from the new template (see --diff)")
    if s == "writable":
        return changed + ("will be re-rendered" if e["requested"] else
                          "untouched; re-render on request (--rerender)")
    return changed + "edited by hand: only a proposal (see --diff), never written"
