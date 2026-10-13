#!/usr/bin/env python3
"""Build the history index `.claude/skills/brain-upgrade/known-hashes.json` (author tool).

Walks every commit reachable from HEAD and records, for each path the current
`.kb-manifest.json` puts in the owned or author class, every content hash it had and the
template states that shipped it (commit, date, release tag). `brain-upgrade --adopt` uses
it to recognise unmodified files from older template states (design D9).

Usage:
  python dev/build_known_hashes.py              index the history up to HEAD
  python dev/build_known_hashes.py --release    also index the staged tree as the release
                                                named by the staged manifest version
                                                (run on the release commit, after `git add`)
  python dev/build_known_hashes.py --check      exit 1 if the file is not up to date
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "brain-upgrade" / "scripts"))

import kbtemplate as kt  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    manifest = kt.Manifest.load(root)
    data = kt.dump_index(kt.build_index(root, manifest, release_tree=args.release))
    out = root / kt.INDEX
    if args.check:
        if out.is_file() and out.read_bytes() == data:
            print(f"{kt.INDEX} is up to date")
            return 0
        print(f"{kt.INDEX} is stale: run python dev/build_known_hashes.py")
        return 1
    out.write_bytes(data)
    index = kt.HistoryIndex.from_bytes(data)
    print(f"wrote {kt.INDEX}: {len(index.states)} states, {len(index.files)} paths, "
          f"releases {sorted(index.releases())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
