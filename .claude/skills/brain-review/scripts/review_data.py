#!/usr/bin/env python3
"""Gather the facts for `/b:review` into one JSON object (brain-review skill).

Run from the vault root (the folder that holds `content/`):

    python .claude/skills/brain-review/scripts/review_data.py [--since YYYY-MM-DD | --days N]

The period starts at the last `review` row of the operation log (`content/_outputs/log.md`);
that row carries `days=N`, and when it is from today the period it covered is covered
again. Without such a row the period starts at the date of the newest
`content/_outputs/reports/*_review.md` before today, else 7 days ago. `--since` (a UTC
date) and `--days` override it. Dates are UTC.

Reads the log, `## Recent Changes` of `vault-map.md`, saved answers and learning sessions,
git history and uncommitted changes, and the inbox; runs `oplog.py`, `lint_scan.py`,
`inbox_order.py` and `metrics.py --record` (the metrics only when the base has at least 10
notes) as subprocesses with this interpreter. A script that is missing or fails is listed
in `unavailable` and the rest is still gathered. Writes nothing itself; `metrics.py
--record` writes today's row of `content/_outputs/metrics.md`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
SCRIPTS = {
    "oplog": SKILLS / "brain-reindex" / "scripts" / "oplog.py",
    "lint_scan": SKILLS / "brain-lint" / "scripts" / "lint_scan.py",
    "metrics": SKILLS / "brain-lint" / "scripts" / "metrics.py",
    "inbox_order": SKILLS / "brain-ingest" / "scripts" / "inbox_order.py",
}
DEFAULT_DAYS = 7
MIN_NOTES = 10  # the floor of /b:lint
LIST_CAP = 20
REPORT = re.compile(r"^(\d{4}-\d{2}-\d{2})_review(?:-\d+)?\.md$")
DATED = re.compile(r"^- (\d{4}-\d{2}-\d{2})\s+(.*)$")
CONTRADICTION = re.compile(r"^(.*) \((\d+) markers?\)$")
FM_FIELD = re.compile(r"^(title|date|gaps|missed|mode|score)\s*:\s*(.*?)\s*$")
EXCLUDE_TOP = {"_raw", "_indexes", "_outputs", "_graveyard", "templates", "ATTACHMENTS"}
EXCLUDE_FILES = {"WRITING_STYLE.md", "WRITING_STYLE_ANALYSIS.md", "_index.md"}


def utc_today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def parse_date(text) -> dt.date | None:
    m = re.match(r"^\s*['\"]?(\d{4}-\d{2}-\d{2})", str(text or ""))
    if not m:
        return None
    try:
        return dt.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def note_key(path: str) -> str:
    """A path as the log and the metrics name a note: relative to `content/`, `/`
    separators, no `.md`."""
    p = path.replace("\\", "/")
    if p.startswith("content/"):
        p = p[len("content/"):]
    return p[:-3] if p.endswith(".md") else p


def is_note(rel_to_content: str) -> bool:
    """Whether a path under `content/` (with `.md`) is a note in the sense of lint."""
    parts = rel_to_content.replace("\\", "/").split("/")
    name = parts[-1]
    if not name.endswith(".md") or name.endswith(".template.md"):
        return False
    if len(parts) > 1 and (parts[0] in EXCLUDE_TOP or parts[0].startswith(".")):
        return False
    return not (name.startswith("_") or name in EXCLUDE_FILES)


def folder_of(key: str) -> str:
    return key.rsplit("/", 1)[0] if "/" in key else "(root)"


def ranked(counter: Counter) -> list[dict]:
    return [{"folder": f, "count": n}
            for f, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0].casefold()))]


# --- subprocesses -----------------------------------------------------------------------

def run_json(script: Path, args: list[str], root: Path):
    """(parsed JSON, None) or (None, reason)."""
    if not script.is_file():
        return None, f"{shown(script)} is missing"
    try:
        r = subprocess.run([sys.executable, str(script), *args], cwd=root,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"{script.name} could not run: {e}"
    if r.returncode != 0:
        first = (r.stderr.strip().splitlines() or [""])[-1]
        return None, f"{script.name} failed (exit {r.returncode}): {first}".rstrip(": ")
    try:
        return json.loads(r.stdout), None
    except json.JSONDecodeError:
        return None, f"{script.name} printed no JSON"


def shown(path: Path) -> str:
    """A script's path relative to the vault root when it lies inside it."""
    try:
        return path.relative_to(SKILLS.parent.parent).as_posix()
    except ValueError:
        return path.as_posix()


def git(root: Path, *args: str):
    """stdout as text, or None when git fails or is missing."""
    try:
        r = subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=root,
                           capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", errors="replace")


# --- the period -------------------------------------------------------------------------

def last_review(rows: list[dict]):
    reviews = [r for r in rows if r.get("op") == "review" and parse_date(r.get("time"))]
    return max(reviews, key=lambda r: r["time"]) if reviews else None


def newest_report(root: Path, today: dt.date) -> dt.date | None:
    folder = root / "content" / "_outputs" / "reports"
    dates = []
    if folder.is_dir():
        for p in folder.iterdir():
            m = REPORT.match(p.name)
            d = parse_date(m.group(1)) if m else None
            if d and d < today:
                dates.append(d)
    return max(dates) if dates else None


def find_period(root: Path, today: dt.date, rows: list[dict], since: dt.date | None,
                days: int | None) -> dict:
    """{"since", "until", "days", "basis", "after"}: `after` is the time of the review row
    the period starts at (log rows at or before it belong to that review), else None."""
    after = None
    if since is not None:
        start, basis = since, "since"
    elif days is not None:
        start, basis = today - dt.timedelta(days=days), "days"
    else:
        row = last_review(rows)
        report = newest_report(root, today)
        if row is not None:
            row_day = parse_date(row["time"])
            covered = (row.get("counts") or {}).get("days")
            if row_day == today:
                n = covered if isinstance(covered, int) and covered >= 0 else DEFAULT_DAYS
                start, basis = today - dt.timedelta(days=n), "last review, today"
            else:
                start, basis, after = row_day, "last review", row["time"]
        elif report is not None:
            start, basis = report, "last report"
        else:
            start, basis = today - dt.timedelta(days=DEFAULT_DAYS), "default"
    return {"since": start.isoformat(), "until": today.isoformat(),
            "days": (today - start).days, "basis": basis, "after": after}


# --- the sources ------------------------------------------------------------------------

def log_part(rows: list[dict], period: dict) -> dict:
    since = period["since"]
    keep = [r for r in rows
            if str(r.get("time", ""))[:10] >= since
            and str(r.get("time", ""))[:10] <= period["until"]
            and (period["after"] is None or r["time"] > period["after"])]
    keep.sort(key=lambda r: r["time"])
    by_op, folders = {}, Counter()
    for r in keep:
        if r.get("op") == "review":
            continue
        entry = by_op.setdefault(r["op"], {"runs": 0, "counts": {}})
        entry["runs"] += 1
        for k, v in (r.get("counts") or {}).items():
            entry["counts"][k] = entry["counts"].get(k, 0) + v
        for n in r.get("notes") or []:
            key = note_key(n)
            if key and not key.startswith("_") and key != "[private]":
                folders[folder_of(key)] += 1
    return {"rows": keep, "by_op": by_op, "folders": ranked(folders)}


def recent_changes(root: Path, period: dict) -> list[dict]:
    path = root / "content" / "_indexes" / "vault-map.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Recent Changes"
            continue
        m = DATED.match(line) if inside else None
        if m and period["since"] <= m.group(1) <= period["until"]:
            out.append({"date": m.group(1), "text": m.group(2)})
    return out


def frontmatter(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as f:
            if f.readline().strip() != "---":
                return {}
            fields = {}
            for _ in range(60):
                line = f.readline()
                if not line or line.strip() == "---":
                    break
                m = FM_FIELD.match(line.rstrip("\n"))
                if m:
                    value = m.group(2)
                    if value[:1] in ("'", '"'):
                        value = value[1:].split(value[0], 1)[0]
                    else:
                        value = re.sub(r"\s+#.*$", "", value)
                    fields[m.group(1)] = value.strip()
            return fields
    except (OSError, UnicodeDecodeError):
        return {}


def dated_outputs(root: Path, folder: str, period: dict) -> list[dict]:
    base = root / "content" / "_outputs" / folder
    out = []
    if not base.is_dir():
        return out
    for p in sorted(base.glob("*.md")):
        fm = frontmatter(p)
        day = parse_date(fm.get("date")) or parse_date(p.name)
        if day is None or not (period["since"] <= day.isoformat() <= period["until"]):
            continue
        gaps = fm.get("gaps")
        item = {"path": p.relative_to(root).as_posix(), "date": day.isoformat(),
                "title": fm.get("title") or p.stem,
                "gaps": int(gaps) if gaps and gaps.isdigit() else None}
        if folder == "learning":
            item["mode"] = fm.get("mode")
            item["score"] = fm.get("score")
            missed = fm.get("missed")
            item["missed"] = int(missed) if missed and missed.isdigit() else None
        out.append(item)
    out.sort(key=lambda i: (i["date"], i["path"]), reverse=True)
    return out


def git_part(root: Path, period: dict) -> dict:
    top = git(root, "rev-parse", "--show-toplevel")
    if top is None or Path(top.strip()).resolve() != root.resolve():
        return {"available": False, "reason": "not the top of a git work tree"}
    if git(root, "rev-parse", "--verify", "-q", "HEAD") is None:
        return {"available": False, "reason": "no commits yet"}
    # From the last review's own minute when the period starts there: its commits belong
    # to that review. Otherwise from the start of the first day.
    start = period["after"] or f"{period['since']} 00:00"
    since = f"--since={start}:00 +0000"
    count = git(root, "rev-list", "--count", since, "HEAD", "--", "content")
    names = git(root, "log", since, "--format=", "--name-only", "-z", "--", "content")
    added = git(root, "log", since, "--diff-filter=A", "--format=", "--name-only", "-z",
                "--", "content")
    status = git(root, "status", "--porcelain", "-z", "--untracked-files=all", "--",
                 "content")

    def notes(raw):
        seen = []
        for p in (raw or "").split("\0"):
            p = p.strip("\n")
            if p.startswith("content/") and is_note(p[len("content/"):]):
                key = note_key(p)
                if key not in seen:
                    seen.append(key)
        return seen

    changed = [k for k in notes(names) if (root / "content" / (k + ".md")).is_file()]
    created = [k for k in notes(added) if k in changed]
    pending, entries, i = [], (status or "").split("\0"), 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if "R" in code or "C" in code:
            i += 1  # the next entry is the path it was renamed or copied from
        if path.startswith("content/") and is_note(path[len("content/"):]):
            pending.append(note_key(path))
    folders = Counter(folder_of(k) for k in changed)
    return {"available": True,
            "commits": int(count.strip()) if count and count.strip().isdigit() else 0,
            "created_count": len(created), "created": sorted(created)[:LIST_CAP],
            "changed_count": len(changed), "changed": sorted(changed)[:LIST_CAP],
            "uncommitted_count": len(pending), "uncommitted": sorted(pending)[:LIST_CAP],
            "folders": ranked(folders)}


def inbox_fallback(root: Path) -> dict:
    base = root / "content" / "_raw" / "inbox"
    n = 0
    if base.is_dir():
        for p in base.rglob("*"):
            rel = p.relative_to(base).parts
            if p.is_file() and not any(part.startswith(".") for part in rel):
                n += 1
    return {"sources": n, "unusable": None, "duplicates": None, "files_only": True}


def report_path(root: Path, today: dt.date) -> str:
    folder = Path("content") / "_outputs" / "reports"
    name, n = f"{today.isoformat()}_review", 1
    while True:
        candidate = folder / (f"{name}.md" if n == 1 else f"{name}-{n}.md")
        if not (root / candidate).exists():
            return candidate.as_posix()
        n += 1


# --- all of it --------------------------------------------------------------------------

def gather(root: Path, today: dt.date, since: dt.date | None = None,
           days: int | None = None, scripts: dict | None = None) -> dict:
    scripts = {**SCRIPTS, **(scripts or {})}
    unavailable = []

    def run(part, name, args):
        data, reason = run_json(scripts[name], args, root)
        if reason:
            unavailable.append({"part": part, "reason": reason})
        return data

    rows = run("log", "oplog", ["read"])
    if not isinstance(rows, list):
        rows = []
    period = find_period(root, today, rows, since, days)

    scan = run("contradictions", "lint_scan", [])
    notes = scan.get("total") if isinstance(scan, dict) else None
    contradictions = None
    if isinstance(scan, dict):
        contradictions = []
        for entry in (scan.get("issues") or {}).get("contradiction") or []:
            m = CONTRADICTION.match(str(entry))
            path, count = (m.group(1), int(m.group(2))) if m else (str(entry), 1)
            contradictions.append({"note": note_key(path), "count": count})

    metrics = None
    today_arg = ["--today", today.isoformat()]
    if notes is None:  # no lint_scan: count the notes with metrics.py, without recording
        metrics = run("metrics", "metrics", today_arg)
        if isinstance(metrics, dict):
            notes = (metrics.get("snapshot") or {}).get("notes")
    too_young = notes is not None and notes < MIN_NOTES
    if not too_young and (metrics is not None or notes is not None):
        recorded = run("metrics", "metrics", ["--record", *today_arg])
        metrics = recorded if isinstance(recorded, dict) else None

    inbox = run("inbox", "inbox_order", [])
    if isinstance(inbox, dict):
        inbox = {"sources": len(inbox.get("sources") or []),
                 "unusable": len(inbox.get("unusable") or []),
                 "duplicates": sum(1 for s in inbox.get("sources") or []
                                   if s.get("duplicate_of")),
                 "files_only": False}
    else:
        inbox = inbox_fallback(root)

    log = log_part(rows, period)
    git_data = git_part(root, period)
    touched = {f["folder"] for f in log["folders"]}
    if git_data.get("available"):
        touched |= {f["folder"] for f in git_data["folders"]}
    thin = {"in_touched_folders": []}
    if isinstance(metrics, dict):
        lists = metrics.get("lists") or {}
        found = {}
        for kind in ("orphans", "isolated", "weak"):
            for key in lists.get(kind) or []:
                if folder_of(key) in touched:
                    found.setdefault(key, []).append(kind)
        thin["in_touched_folders"] = [{"note": k, "kinds": v}
                                      for k, v in sorted(found.items())][:LIST_CAP]

    return {
        "period": period,
        "notes": notes,
        "too_young": too_young,
        "log": log,
        "recent_changes": recent_changes(root, period),
        "answers": dated_outputs(root, "answers", period),
        "learning": dated_outputs(root, "learning", period),
        "git": git_data,
        "inbox": inbox,
        "contradictions": contradictions,
        "metrics": metrics,
        "thin": thin,
        "unavailable": unavailable,
        "report_path": report_path(root, today),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--since", help="start of the period, a UTC date YYYY-MM-DD")
    group.add_argument("--days", type=int, help="the period is the last N days")
    ap.add_argument("--today", help=argparse.SUPPRESS)  # tests
    ap.add_argument("--root", default=".", help="the vault root (default: here)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(args.root)
    if not (root / "content").is_dir():
        print(f"no content/ folder in {root.resolve()}; run from the vault root",
              file=sys.stderr)
        return 2
    today = parse_date(args.today) if args.today else utc_today()
    if today is None:
        print("--today must be a date YYYY-MM-DD", file=sys.stderr)
        return 2
    since = None
    if args.since is not None:
        since = parse_date(args.since)
        if since is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.since):
            print("--since must be a date YYYY-MM-DD", file=sys.stderr)
            return 2
        if since > today:
            print("--since is after today", file=sys.stderr)
            return 2
    if args.days is not None and args.days < 1:
        print("--days must be 1 or more", file=sys.stderr)
        return 2
    print(json.dumps(gather(root, today, since, args.days), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
