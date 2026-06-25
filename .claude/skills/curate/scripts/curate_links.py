#!/usr/bin/env python3
"""Live link-status classification for the /curate skill. A network failure is
never treated as proof a link is dead — only explicit 404/410 are 'dead'.
Everything ambiguous is 'unverified' so the skill never auto-retires on a
transient error. Run only on the already-flagged subset, not the whole vault."""
import json
import sys
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_UA = {"User-Agent": "Mozilla/5.0 (curate-skill link check)"}


def classify_status(status_code, network_error=False):
    """Map an HTTP status (or network failure) to alive/dead/unverified."""
    if network_error or status_code is None:
        return "unverified"
    if status_code in (404, 410):
        return "dead"
    if 200 <= status_code < 400:
        return "alive"
    # 401/403/429 blocks, 5xx server errors -> not proof of death
    return "unverified"


def check_url(url, timeout=8.0):
    """Fetch headers for `url` and classify. Falls back to GET if HEAD is refused."""
    req = urllib.request.Request(url, method="HEAD", headers=_UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return classify_status(resp.status)
    except urllib.error.HTTPError as e:
        if e.code == 405:  # HEAD not allowed — retry with GET
            try:
                greq = urllib.request.Request(url, method="GET", headers=_UA)
                with urllib.request.urlopen(greq, timeout=timeout) as resp:
                    return classify_status(resp.status)
            except urllib.error.HTTPError as e2:
                return classify_status(e2.code)  # GET-confirmed 404/410 -> dead
            except Exception:
                return classify_status(None, network_error=True)
        return classify_status(e.code)
    except Exception:
        return classify_status(None, network_error=True)


if __name__ == "__main__":
    results = {u: check_url(u) for u in sys.argv[1:]}
    print(json.dumps(results, indent=1, ensure_ascii=False))
