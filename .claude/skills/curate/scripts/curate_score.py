#!/usr/bin/env python3
"""Pure staleness-scoring functions for the /curate skill. No I/O here —
the SKILL.md orchestration gathers note data (ages, graph edges, link status)
and feeds it to these functions. Kept pure so it is unit-testable."""
import re
import sys
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def days_since(date_str, today):
    """Days from an ISO YYYY-MM-DD date string until `today`. None if unparseable."""
    if not date_str:
        return None
    s = date_str.strip().strip('"').strip("'")
    m = _DATE_RE.match(s)
    if not m:
        return None
    try:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return (today - d).days


def age_points(days):
    """Time-decay points. Unknown age (None) contributes nothing."""
    if days is None:
        return 0
    if days <= 365:
        return 0
    if days <= 545:
        return 1
    if days <= 730:
        return 2
    return 3


def isolation_points(in_edges, out_edges):
    """Graph-isolation penalty: 0 edges -> 2, exactly 1 edge -> 1, else 0."""
    total = in_edges + out_edges
    if total == 0:
        return 2
    if total == 1:
        return 1
    return 0


def score_note(age_days, in_edges, out_edges, dead_link):
    """Return (score, reasons). dead_link adds a heavy fixed weight of 4."""
    reasons = []
    score = 0
    ap = age_points(age_days)
    if ap:
        score += ap
        reasons.append(f"stale: ~{age_days}d since last touch")
    ip = isolation_points(in_edges, out_edges)
    if ip:
        score += ip
        reasons.append(f"graph-isolated: {in_edges} in / {out_edges} out links")
    if dead_link:
        score += 4
        reasons.append("dead source/repo link")
    return score, reasons


def recommend_action(score, dead_link, has_superseder):
    """Map a score + flags to one action. dead link or score>=4 -> archive;
    a newer note covering the topic -> merge; mid score -> refresh; else keep.
    Archive intentionally outranks merge: a note that is both highly stale
    (score>=4 or dead link) and superseded is archived, not merged. Archiving
    is reversible, so no information is lost."""
    if dead_link or score >= 4:
        return "archive"
    if has_superseder:
        return "merge"
    if score >= 2:
        return "refresh"
    return "keep"


def parse_graph(text):
    """Parse _indexes/graph.md into {note_name: (in_edges, out_edges)}.
    Reads the `## Outgoing` (A -> B, C) and `## Incoming` (B <- A) sections."""
    out_counts = {}
    in_counts = {}
    section = None
    for line in text.splitlines():
        if line.startswith("## Outgoing"):
            section = "out"
            continue
        if line.startswith("## Incoming"):
            section = "in"
            continue
        if line.startswith("#") or not line.strip():
            continue
        if section == "out" and "->" in line:
            left, right = line.split("->", 1)
            name = left.strip()
            targets = [t.strip() for t in right.split(",") if t.strip() and t.strip() != "-"]
            out_counts[name] = out_counts.get(name, 0) + len(targets)
            for t in targets:
                in_counts.setdefault(t, in_counts.get(t, 0))
            out_counts.setdefault(name, out_counts.get(name, 0))
        elif section == "in" and "<-" in line:
            left, right = line.split("<-", 1)
            name = left.strip()
            sources = [s.strip() for s in right.split(",") if s.strip() and s.strip() != "-"]
            in_counts[name] = in_counts.get(name, 0) + len(sources)

    names = set(out_counts) | set(in_counts)
    return {n: (in_counts.get(n, 0), out_counts.get(n, 0)) for n in names}
