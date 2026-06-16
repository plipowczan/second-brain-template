#!/usr/bin/env python3
"""Structural gap signals from the vault link graph. Parses
content/_indexes/graph.md to compute per-note link degree and surface
weakly-connected notes (total degree <= 1). The `gaps` skill layers semantic
analysis (missing topics, stale clusters) on top of these signals.

Usage:
  python gaps.py                 # reads content/_indexes/graph.md
  python gaps.py --graph PATH
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def parse_graph(text):
    out_deg, in_deg = {}, {}
    section = None
    for line in text.splitlines():
        s = line.strip()
        low = s.lower()
        if low.startswith("## outgoing"):
            section = "out"; continue
        if low.startswith("## incoming"):
            section = "in"; continue
        if not s or s.startswith("#"):
            continue
        if section == "out" and "->" in s:
            left, right = s.split("->", 1)
            node = left.strip()
            tgts = [t for t in (x.strip() for x in right.split(",")) if t]
            out_deg[node] = out_deg.get(node, 0) + len(tgts)
            in_deg.setdefault(node, in_deg.get(node, 0))
        elif section == "in" and "<-" in s:
            left, right = s.split("<-", 1)
            node = left.strip()
            srcs = [t for t in (x.strip() for x in right.split(",")) if t]
            in_deg[node] = in_deg.get(node, 0) + len(srcs)
            out_deg.setdefault(node, out_deg.get(node, 0))
    return out_deg, in_deg


def analyze(text):
    out_deg, in_deg = parse_graph(text)
    nodes = set(out_deg) | set(in_deg)
    degree = {n: out_deg.get(n, 0) + in_deg.get(n, 0) for n in nodes}
    weak = sorted(n for n in nodes if degree[n] <= 1)
    return {"nodes": len(nodes), "weak_count": len(weak), "weakly_connected": weak}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Structural gap signals from the link graph.")
    ap.add_argument("--graph", default=os.path.join("content", "_indexes", "graph.md"))
    args = ap.parse_args(argv)
    try:
        text = open(args.graph, encoding="utf-8").read()
    except FileNotFoundError:
        print(f"gaps: no graph index at {args.graph}; run /reindex first", file=sys.stderr)
        return 2
    print(json.dumps(analyze(text), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
