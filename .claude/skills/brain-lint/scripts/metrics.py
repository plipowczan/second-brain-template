#!/usr/bin/env python3
"""Link and freshness metrics of the vault, and their dated snapshots.

Run from the vault root (the folder that holds content/):

  python .claude/skills/brain-lint/scripts/metrics.py [--record] [--today YYYY-MM-DD]
      [--folder NAME]...

Prints one JSON object: `snapshot` (today's values), `previous` (the latest recorded
snapshot before today), `older` (the newest one at least 28 days before today),
`callouts` (metrics that got worse by at least one step), `comparable`, `lists` (up to
20 note paths per metric) and `recorded`. `--record` writes today's row into
content/_outputs/metrics.md; without it nothing is written. With `--folder` (a folder
under content/, `(root)` for the notes at its top; repeatable) it also prints
`in_folders`: the orphans, isolated and weak notes in those folders, up to 20 each,
chosen before the lists are cut, so a folder late in the alphabet is not lost.

The note set, link resolution and orphan rule are those of lint_links.py, imported:

- notes, orphans: exactly as lint_links.py counts them (a self-link is incoming).
- isolated: notes with no link to or from another note; self-links do not count.
- weak: notes with at most one distinct link to or from another note, counted as in
  brain-gaps: distinct notes linked to plus distinct notes linking in, so A <-> B is two.
- links_per_note: distinct links from a note to another note, averaged over notes.
- islands: connected groups of 2 or more notes besides the largest one; a note on its own
  is isolated, not an island.
- untouched_90d: notes whose last touch is 90 or more days before today. Last touch is the
  latest of frontmatter `date`, `agent-reviewed` and, when the vault root is the top of a
  git work tree with a commit (basis `git`), the file's last commit date; else the basis
  is `frontmatter`. A note with no date from any source counts in untouched_unknown.

Notes that share a file name: lint resolves a link by name, without case, so a link to
`Dup` reaches every `Dup.md` and cannot tell them apart. Here the name (lower case) is
the target of a link: each file counts as a note and keeps its own outgoing links, every
file of the name gets the links into it, one `[[Dup]]` is one distinct link, and a link
between two files of one name is a self-link. Islands are counted over names.

Shares are 0-100 with one decimal, links_per_note has two; with 0 notes they are null.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_links  # noqa: E402
import lint_scan  # noqa: E402

ROOT = lint_links.ROOT
UNTOUCHED_DAYS = 90
OLDER_DAYS = 28
MIN_NOTES = 30
LIST_LIMIT = 20
BASES = ("git", "frontmatter")

HEADING = "# Vault metrics"
COLUMNS = ["Date (UTC)", "Basis", "Notes", "Orphans", "Isolated", "Weak", "Links per note",
           "Islands", "Untouched 90d"]
FIELDS = ["date", "basis", "notes", "orphans", "isolated", "weak", "links_per_note", "islands",
          "untouched_90d"]
COUNTS = ["notes", "orphans", "isolated", "weak", "islands", "untouched_90d"]
TABLE_HEADER = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]

DAY = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
ISO_DAY = re.compile(r'\d{4}-\d{2}-\d{2}')
INT = re.compile(r'\d+')
DECIMAL = re.compile(r'\d+(\.\d+)?')


def metrics_path(root=ROOT):
    return os.path.join(root, "_outputs", "metrics.md")


# --- graph -----------------------------------------------------------------------------

def graph(result):
    """Per-note link counts from lint_links.scan(). Returns {"out": {path: set of target
    names}, "in": {path: set of source paths}, "islands": int}, self-links left out."""
    key_of = {p: lint_links.name_key(n) for p, n in result["notes"]}
    out = {p: set() for p in key_of}
    into = {}
    adj = {k: set() for k in key_of.values()}
    for src, tgt in result["edges"]:
        s, t = key_of[src], lint_links.name_key(tgt)
        if s == t:
            continue
        out[src].add(t)
        into.setdefault(t, set()).add(src)
        adj[s].add(t)
        adj[t].add(s)
    incoming = {p: into.get(k, set()) for p, k in key_of.items()}
    return {"out": out, "in": incoming, "islands": islands(adj)}


def islands(adj):
    """Connected groups of 2 or more nodes besides the largest one."""
    seen, groups = set(), 0
    for start in adj:
        if start in seen or not adj[start]:
            continue
        groups += 1
        stack = [start]
        seen.add(start)
        while stack:
            for nxt in adj[stack.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return max(groups - 1, 0)


# --- last touch ------------------------------------------------------------------------

def parse_day(value):
    """A YYYY-MM-DD date at the start of a frontmatter value, quoted or not; else None."""
    if not isinstance(value, str):
        return None
    m = DAY.match(value.strip().strip("\"'").strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def frontmatter_days(path):
    """The `date` and `agent-reviewed` of a note that has them."""
    with open(path, encoding="utf-8") as f:
        fm, _ = lint_scan.parse_fm(f.read())
    fm = fm or {}
    return [d for d in (parse_day(fm.get("date")), parse_day(fm.get("agent-reviewed"))) if d]


def _git(args):
    try:
        r = subprocess.run(["git", *args], capture_output=True, stdin=subprocess.DEVNULL)
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


def git_basis():
    """True when the working directory is the top of a git work tree with a commit."""
    prefix = _git(["rev-parse", "--show-prefix"])
    if prefix is None or prefix.strip():
        return False
    return _git(["rev-parse", "-q", "--verify", "HEAD^{commit}"]) is not None


def _path_key(rel):
    return unicodedata.normalize("NFC", rel)


def commit_days(root=ROOT):
    """{path relative to root: date of its last commit}, from one `git log` over root.
    -z keeps non-ASCII paths as they are; the date is the committer date (%cs), as
    brain-curate reads it. None when git fails."""
    out = _git(["-c", "core.quotePath=false", "-c", "log.showSignature=false", "log", "-z",
                "--no-renames", "--no-color", "--name-only", "--format=%x01%cs", "--", root])
    if out is None:
        return None
    prefix = root.replace("\\", "/").rstrip("/") + "/"
    days, current = {}, None
    # Each commit is "\x01<date>\0", then "\n" and its paths, each ending in "\0".
    for tok in out.decode("utf-8", errors="surrogateescape").split("\0"):
        tok = tok.lstrip("\n")
        if tok.startswith("\x01"):
            current = parse_day(tok[1:])
        elif tok.startswith(prefix) and current:
            key = _path_key(tok[len(prefix):])
            if key not in days or current > days[key]:
                days[key] = current
    return days


# --- snapshot --------------------------------------------------------------------------

def share(count, notes):
    return round(100.0 * count / notes, 1) if notes else None


def make_snapshot(values):
    """A snapshot in the contract's key order from its counts (date, basis, notes,
    orphans, isolated, weak, links_per_note, islands, untouched_90d and, optionally,
    untouched_unknown); shares are computed here."""
    n = values["notes"]
    snap = {"date": values["date"], "basis": values["basis"], "notes": n}
    for key in ("orphans", "isolated", "weak"):
        snap[key] = values[key]
        snap[key + "_pct"] = share(values[key], n)
    snap["links_per_note"] = values["links_per_note"] if n else None
    snap["islands"] = values["islands"]
    snap["untouched_90d"] = values["untouched_90d"]
    snap["untouched_90d_pct"] = share(values["untouched_90d"], n)
    snap["untouched_unknown"] = values.get("untouched_unknown")
    return snap


def folder_of(name):
    """The folder of a note name (its path under content/ without .md), `(root)` for a
    note at the top: the folder names /b:review uses."""
    return name.rsplit("/", 1)[0] if "/" in name else "(root)"


def measure(root, today, commit_dates=None, folders=None):
    """(snapshot, lists) for the vault under root on `today`. commit_dates is None for
    the frontmatter basis, else commit_days() for the git basis. With `folders`, lists
    also holds `in_folders`: the orphans, isolated and weak notes in those folders, each
    list filtered first and cut after."""
    result = lint_links.scan(root)
    notes = [p for p, _ in result["notes"]]
    rel = {p: os.path.relpath(p, root).replace("\\", "/") for p in notes}
    g = graph(result)
    degree = {p: len(g["out"][p]) + len(g["in"][p]) for p in notes}

    lower = {}
    for k, d in (commit_dates or {}).items():
        if k.lower() not in lower or d > lower[k.lower()]:
            lower[k.lower()] = d
    touched, unknown = {}, 0
    for p in notes:
        days = frontmatter_days(p)
        if commit_dates is not None:
            key = _path_key(rel[p])
            d = commit_dates.get(key) or lower.get(key.lower())
            if d:
                days.append(d)
        if days:
            touched[p] = max(days)
        else:
            unknown += 1
    untouched = sorted((touched[p], rel[p][:-3]) for p in touched
                       if (today - touched[p]).days >= UNTOUCHED_DAYS)

    def names(paths):
        return sorted(rel[p][:-3] for p in paths)

    orphans = names(p for p, _ in result["orphan_notes"])
    isolated = names(p for p in notes if degree[p] == 0)
    weak = names(p for p in notes if degree[p] <= 1)
    links = sum(len(g["out"][p]) for p in notes)
    snap = make_snapshot({
        "date": today.isoformat(),
        "basis": "frontmatter" if commit_dates is None else "git",
        "notes": len(notes), "orphans": len(orphans), "isolated": len(isolated),
        "weak": len(weak), "links_per_note": round(links / len(notes), 2) if notes else None,
        "islands": g["islands"], "untouched_90d": len(untouched), "untouched_unknown": unknown,
    })
    lists = {"orphans": orphans[:LIST_LIMIT], "isolated": isolated[:LIST_LIMIT],
             "weak": weak[:LIST_LIMIT], "untouched_90d": [p for _, p in untouched][:LIST_LIMIT]}
    if folders is not None:
        wanted = set(folders)
        lists["in_folders"] = {
            kind: [n for n in full if folder_of(n) in wanted][:LIST_LIMIT]
            for kind, full in (("orphans", orphans), ("isolated", isolated), ("weak", weak))}
    return snap, lists


# --- metrics.md ------------------------------------------------------------------------

def format_row(snap):
    cells = [snap[f] for f in FIELDS]
    lpn = snap["links_per_note"]
    cells[FIELDS.index("links_per_note")] = "-" if lpn is None else f"{lpn:.2f}"
    return "| " + " | ".join(str(c) for c in cells) + " |"


def parse_row(line):
    """The values of a valid table row, else None (header, separator, other text)."""
    s = line.strip()
    if len(s) < 2 or not (s.startswith("|") and s.endswith("|")):
        return None
    cells = [c.strip() for c in s[1:-1].split("|")]
    if len(cells) != len(FIELDS):
        return None
    values = dict(zip(FIELDS, cells))
    if not ISO_DAY.fullmatch(values["date"]):
        return None
    try:
        date.fromisoformat(values["date"])
    except ValueError:
        return None
    if values["basis"] not in BASES:
        return None
    for key in COUNTS:
        if not INT.fullmatch(values[key]):
            return None
        values[key] = int(values[key])
    if any(values[k] > values["notes"] for k in COUNTS):
        return None
    lpn = values["links_per_note"]
    if lpn == "-":
        values["links_per_note"] = None
    elif DECIMAL.fullmatch(lpn):
        values["links_per_note"] = float(lpn)
    else:
        return None
    if values["notes"] and values["links_per_note"] is None:
        return None
    return values


def _lines(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line.rstrip("\r") for line in lines]


def read_text(path):
    """The file's text, None when it does not exist. Bytes that are not UTF-8 survive a
    rewrite unchanged."""
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", errors="surrogateescape")
    except FileNotFoundError:
        return None


def read_history(text):
    """Snapshots from the file's text: the last row of each date, sorted by date. A row
    has no untouched_unknown column, so that value is null."""
    by_date = {}
    for line in _lines(text or ""):
        values = parse_row(line)
        if values:
            by_date[values["date"]] = values
    return [make_snapshot(by_date[d]) for d in sorted(by_date)]


def recorded_text(text, snap):
    """The file's text with snap's row in it: a new (or blank) file gets the heading and
    the table header; a row of the same date is replaced (and any further row of that date
    dropped); else the row goes after the last table line. Other lines stay."""
    row = format_row(snap)
    if text is None or not text.strip():
        return "\n".join([HEADING, ""] + TABLE_HEADER + [row]) + "\n"
    lines = _lines(text)
    same = [i for i, line in enumerate(lines)
            if (parse_row(line) or {}).get("date") == snap["date"]]
    if same:
        lines[same[-1]] = row
        for i in reversed(same[:-1]):
            del lines[i]
    else:
        table = [i for i, line in enumerate(lines) if line.strip().startswith("|")]
        if table:
            lines.insert(table[-1] + 1, row)
        else:
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend(TABLE_HEADER + [row])
    return "\n".join(lines) + "\n"


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(text.encode("utf-8", errors="surrogateescape"))


# --- comparison ------------------------------------------------------------------------

def pick_earlier(history, day):
    """(previous, older): the latest snapshot dated before `day`, and the newest one at
    least OLDER_DAYS before it. day is a date."""
    previous = older = None
    for snap in history:
        d = date.fromisoformat(snap["date"])
        if d < day:
            previous = snap
        if (day - d).days >= OLDER_DAYS:
            older = snap
    return previous, older


def comparable(current, earlier):
    """Whether untouched_90d can be compared: both snapshots exist and share a basis."""
    return earlier is not None and earlier["basis"] == current["basis"]


def callouts(current, earlier, against):
    """Metrics that got worse from `earlier` to `current` by at least one step (design
    D6 of add-review-loop): orphans or isolated +2 percentage points and at least 2 more
    notes, islands +1, links_per_note -0.5, untouched_90d +5 points and at least 2 more
    notes (only on the same basis). None below MIN_NOTES notes now, or without an
    earlier snapshot. Differences are rounded to the precision shown before comparing.
    `from` and `to` are the metric's values in the two snapshots (counts for the share
    metrics, which also carry `from_pct` and `to_pct`)."""
    if earlier is None or current["notes"] < MIN_NOTES:
        return []
    found = []

    def share_step(metric, points):
        a, b = earlier[metric + "_pct"], current[metric + "_pct"]
        if a is None or b is None:
            return
        if round(b - a, 1) >= points and current[metric] - earlier[metric] >= 2:
            found.append({"metric": metric, "against": against, "from": earlier[metric],
                          "to": current[metric], "from_pct": a, "to_pct": b})

    share_step("orphans", 2.0)
    share_step("isolated", 2.0)
    if current["islands"] - earlier["islands"] >= 1:
        found.append({"metric": "islands", "against": against, "from": earlier["islands"],
                      "to": current["islands"]})
    a, b = earlier["links_per_note"], current["links_per_note"]
    if a is not None and b is not None and round(b - a, 2) <= -0.5:
        found.append({"metric": "links_per_note", "against": against, "from": a, "to": b})
    if comparable(current, earlier):
        share_step("untouched_90d", 5.0)
    return found


# --- command line ----------------------------------------------------------------------

def _day_arg(value):
    try:
        if not ISO_DAY.fullmatch(value):
            raise ValueError
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value}")


def run(root, today, record=False, commit_dates=None, folders=None):
    """The JSON object the script prints; writes the row when record is true."""
    snap, lists = measure(root, today, commit_dates, folders)
    in_folders = lists.pop("in_folders", None)
    path = metrics_path(root)
    text = read_text(path)
    previous, older = pick_earlier(read_history(text), today)
    if record:
        write_text(path, recorded_text(text, snap))
    out = {
        "snapshot": snap,
        "previous": previous,
        "older": older,
        "callouts": callouts(snap, previous, "previous") + callouts(snap, older, "older"),
        "comparable": {"previous": comparable(snap, previous), "older": comparable(snap, older)},
        "lists": lists,
        "recorded": bool(record),
    }
    if in_folders is not None:
        out["in_folders"] = in_folders
    return out


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # avoid cp1252 crash on non-Latin content
    ap = argparse.ArgumentParser(description="Link and freshness metrics of the vault.")
    ap.add_argument("--record", action="store_true",
                    help="write today's row into content/_outputs/metrics.md")
    ap.add_argument("--today", type=_day_arg, default=None,
                    help="the snapshot date, YYYY-MM-DD (default: today in UTC)")
    ap.add_argument("--folder", action="append", default=None, metavar="NAME",
                    help="also list the thin notes of this folder under content/ "
                         "((root) for its top) before the lists are cut; repeatable")
    args = ap.parse_args(argv)
    if not os.path.isdir(ROOT):
        print(f"metrics.py: no {ROOT}/ folder here; run it from the vault root",
              file=sys.stderr)
        return 2
    today = args.today or datetime.now(timezone.utc).date()
    commit_dates = commit_days(ROOT) if git_basis() else None
    print(json.dumps(run(ROOT, today, args.record, commit_dates, args.folder), indent=1,
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
