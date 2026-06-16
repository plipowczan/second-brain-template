#!/usr/bin/env python3
"""SessionStart hook: print the vault map so the agent has it in context from the
start (enforces the progressive-disclosure protocol in CLAUDE.md). Output on stdout
is injected as session context by Claude Code."""
import os
import sys

root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
path = os.path.join(root, "content", "_indexes", "vault-map.md")

try:
    with open(path, encoding="utf-8") as f:
        sys.stdout.write(f.read())
except FileNotFoundError:
    sys.stdout.write(
        "No content/_indexes/vault-map.md yet. "
        "Run /onboard (new vault) or /reindex to build the navigation indexes.\n"
    )
