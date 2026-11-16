#!/usr/bin/env python3
"""brain-watch: re-check the status of the tool notes in this vault.

Run from the vault root (or pass --root). Subcommands, in pipeline order:

  scan     Cheap pass. Resolves each in-scope note's repo or homepage, reads GitHub facts
           (or checks the URL), compares them with the snapshot, flags what changed and
           picks the notes for the deep pass. Writes scan.json. Never writes a note.
  outline  Writes outline.yaml + fields.yaml + results/ for the deep pass into a workspace.
  digest   Turns the deep-pass results into status-box lines. A note whose lines contain a
           private term is held back. Writes digest.json.
  apply    Writes the status boxes, the status frontmatter, the one-time repo/homepage
           fields and the snapshot. --dry prints what it would change and writes nothing.
  report   Writes the markdown report.

Needs Python 3 and PyYAML. GitHub is read with `gh api` when gh is installed, else over
HTTPS with $GH_TOKEN / $GITHUB_TOKEN, else anonymously (60 requests an hour). Every
request names its repository explicitly (repos/<owner>/<name>/...), so gh never falls
back to the repository of the current checkout.
"""
import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT = "content/_outputs/watch/snapshot.json"
VOCAB = ("active", "maintained", "slowing", "stale", "dead", "done", "sunset")
CALLOUT = {"active": "success", "maintained": "success", "done": "info",
           "slowing": "warning", "stale": "warning", "dead": "danger", "sunset": "danger"}
QUIET = ("dead", "done", "sunset")            # already retired: archived or gone is not news
SLEEPY = ("stale",) + QUIET                    # and for these, a quiet repo is not news
REVIVABLE = ("stale", "dead", "sunset")        # a new commit on these is news
STALE_DAYS = 180
MARK = re.compile(r"^> \[![A-Za-z-]+\] Status check \d{4}-\d{2}-\d{2}")
FM = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
GH_OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
GH_URL = re.compile(r"https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)
ANY_URL = re.compile(r"https?://[^\s<>\"'`)\]|]+")
NOT_OWNERS = {"orgs", "topics", "features", "sponsors", "marketplace", "settings", "apps",
              "collections", "trending", "login", "about", "pricing", "enterprise", "explore",
              "site", "security", "customer-stories", "readme", "events", "notifications",
              "codespaces", "copilot", "issues", "pulls", "search", "new", "users"}
SKIP_HOSTS = ("github.com", "githubusercontent.com", "github.io", "youtube.com", "youtu.be",
              "x.com", "twitter.com", "linkedin.com", "reddit.com", "news.ycombinator.com",
              "medium.com", "substack.com", "wikipedia.org", "archive.org", "t.co", "bit.ly",
              "discord.gg", "discord.com", "google.com", "facebook.com", "instagram.com")
SITE_SUBDOMAINS = ("docs", "doc", "developers", "developer", "api", "support", "help", "blog",
                   "platform", "status", "app", "dashboard", "console")
FIELDS = ["repo_url", "moved_or_renamed", "last_release", "last_commit", "archived_or_deprecated",
          "license", "liveness", "liveness_evidence", "successor_or_replacement",
          "changes_since_note", "sources"]
BOM = chr(0xFEFF)
NBSP = chr(0xA0)
UA = {"User-Agent": "Mozilla/5.0 (brain-watch link check)"}


# ---------------------------------------------------------------- files and frontmatter

def load(path):
    """(text with LF endings, had CRLF, had BOM)."""
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    bom = text.startswith(BOM)
    if bom:
        text = text[1:]
    return text.replace("\r\n", "\n"), "\r\n" in text, bom


def save(path, text, crlf=False, bom=False):
    if crlf:
        text = text.replace("\n", "\r\n")
    if bom:
        text = BOM + text
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n")


def split_fm(text):
    """(frontmatter text or None, body)."""
    m = FM.match(text)
    return (m.group(1), text[m.end():]) if m else (None, text)


def parse_fm(fm):
    try:
        d = yaml.safe_load(fm) if fm else {}
    except yaml.YAMLError:
        return {}
    return d if isinstance(d, dict) else {}


def set_fm(fm, key, value):
    """Set one top-level key, in place if present, else appended. Other lines untouched."""
    line = f"{key}: {value}"
    pat = re.compile(rf"^{re.escape(key)}:.*$", re.M)
    if pat.search(fm):
        return pat.sub(lambda m: line, fm, count=1)
    head = fm.rstrip("\n")
    return head + "\n" + line + fm[len(head):]  # blank lines before the closing --- stay


def fm_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def day(v):
    """A frontmatter or API date as YYYY-MM-DD, or None."""
    if v is None:
        return None
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()[:10]
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(v))
    return m.group(0) if m else None


def days_between(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


# ---------------------------------------------------------------- scope

def note_paths(root):
    """Vault notes under content/, skipping _*/.* folders and files, and templates/."""
    base = Path(root) / "content"
    for p in sorted(base.rglob("*.md")):
        parts = p.relative_to(base).parts
        if any(x.startswith(("_", ".")) or x == "templates" for x in parts[:-1]):
            continue
        if parts[-1].startswith("_") or parts[-1].endswith(".template.md"):
            continue
        yield p.relative_to(root).as_posix()


def has_callout(body):
    return any(MARK.match(line) for line in body.split("\n"))


def wikilink_targets(body):
    return sorted({t.strip().split("/")[-1] for t in re.findall(r"\[\[([^\]|#]+)", body)})


# ---------------------------------------------------------------- where a note points

def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def gh_slug(value):
    """owner/name from a GitHub URL or a bare owner/name, else None."""
    if not value:
        return None
    s = str(value).strip()
    m = GH_URL.match(s)
    if m:
        owner, name = m.groups()
    elif re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", s):
        owner, name = s.split("/")
    else:
        return None
    name = re.sub(r"\.git$", "", name).rstrip(".")
    # The slug becomes an authenticated API path (repos/<owner>/<name>/...): an owner
    # must be a GitHub login (letters, digits, inner hyphens) and the name may not be
    # empty, "." or "..", so a crafted link cannot reach another endpoint.
    if not GH_OWNER.fullmatch(owner) or owner.lower() in NOT_OWNERS or name in ("", ".", ".."):
        return None
    return f"{owner}/{name}"


def repo_links(text):
    seen = []
    for m in GH_URL.finditer(text):
        slug = gh_slug(m.group(0))
        if slug and slug.lower() not in {s.lower() for s in seen}:
            seen.append(slug)
    return seen


def host_of(url):
    h = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0].lower()
    return h[4:] if h.startswith("www.") else h


def skip_host(h):
    return any(h == s or h.endswith("." + s) for s in SKIP_HOSTS)


def site_root(url):
    """The product site a URL belongs to: docs.x.dev/page -> https://x.dev/."""
    scheme = "http" if url.startswith("http://") else "https"
    host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0].lower()
    labels = host.split(".")
    while len(labels) > 2 and labels[0] in SITE_SUBDOMAINS:
        labels = labels[1:]
    return f"{scheme}://{'.'.join(labels)}/"


def propose(title, stem, text):
    """Where a note without repo/homepage fields should point, and on what basis.

    Returns (proposal, basis): ({"repo": url}, "name-match" | "single-link"),
    ({"homepage": url}, "homepage"), ({"ambiguous": [...]}, None) or
    ({"untracked": True}, None). Never guesses between several candidates."""
    cands = repo_links(text)
    names = {norm(title), norm(stem)} - {""}
    exact = [c for c in cands if norm(c.split("/")[1]) in names]
    if len(exact) == 1:
        return {"repo": "https://github.com/" + exact[0]}, "name-match"
    if len(exact) > 1:
        return {"ambiguous": exact[:6]}, None
    if len(cands) == 1:
        return {"repo": "https://github.com/" + cands[0]}, "single-link"
    if len(cands) > 1:
        return {"ambiguous": cands[:6]}, None
    urls = []
    for u in ANY_URL.findall(text):
        u = u.rstrip(".,;:!?")
        if not skip_host(host_of(u)) and u not in urls:
            urls.append(u)
    t = norm(title)
    for u in urls:
        labels = [norm(x) for x in host_of(u).split(".")[:-1] if len(x) >= 3]
        if t and any(lab and (lab in t or t in lab) for lab in labels):
            return {"homepage": site_root(u)}, "homepage"
    if urls:
        return {"ambiguous": urls[:6]}, None
    return {"untracked": True}, None


def resolve(fm, title, stem, body, override=None):
    """The note's tracking target: kind repo | url | untracked | off, plus seed fields
    to write when the note has neither `repo` nor `homepage` yet."""
    out = {"seed": {}, "basis": None, "ambiguous": None}
    repo_url, homepage = fm.get("repo"), fm.get("homepage")
    if not repo_url and not homepage:
        if override:
            out["seed"] = {k: v for k, v in override.items()
                           if k in ("repo", "homepage", "watch") and v not in (None, "")}
            out["basis"] = "override"
        else:
            text = str(fm.get("source") or "") + "\n" + body
            prop, basis = propose(title, stem, text)
            if "repo" in prop or "homepage" in prop:
                out["seed"], out["basis"] = prop, basis
            elif "ambiguous" in prop:
                out["ambiguous"] = prop["ambiguous"]
        repo_url = out["seed"].get("repo")
        homepage = out["seed"].get("homepage")
    if out["seed"].get("watch") is False:
        out.update(kind="off", repo=None, repo_url=None, homepage=None, url=None)
        return out
    slug = gh_slug(repo_url)
    url = homepage or (repo_url if repo_url and not slug else None)
    out.update(kind="repo" if slug else ("url" if url else "untracked"),
               repo=slug, repo_url=("https://github.com/" + slug) if slug else repo_url,
               homepage=homepage, url=None if slug else url)
    return out


# ---------------------------------------------------------------- GitHub and URLs

class GitHub:
    """Read-only GitHub REST access: gh if installed, else HTTPS (token if set)."""

    def __init__(self):
        self.token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.gh = shutil.which("gh")
        self.mode = "gh" if self.gh else ("token" if self.token else "anonymous")
        self.blocked = False

    def get(self, path):
        """(status, data). status None = network failure; 429 = rate limited (and every
        later call is skipped, so one limit hit does not cost hundreds of failures)."""
        if self.blocked:
            return 429, None
        if self.gh:
            r = subprocess.run([self.gh, "api", path], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            if r.returncode == 0:
                try:
                    return 200, json.loads(r.stdout or "null")
                except ValueError:
                    return None, None
            msg = r.stderr + r.stdout
            m = re.search(r"HTTP (\d{3})", msg)
            st = int(m.group(1)) if m else None
        else:
            req = urllib.request.Request("https://api.github.com/" + path,
                                         headers={"Accept": "application/vnd.github+json",
                                                  "User-Agent": "brain-watch"})
            if self.token:
                req.add_header("Authorization", "Bearer " + self.token)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.status, json.loads(resp.read().decode("utf-8") or "null")
            except urllib.error.HTTPError as e:
                st = e.code
            except Exception:
                return None, None
        if st in (403, 429):
            self.blocked = True
            return 429, None
        return st, None

    def remaining(self):
        st, d = self.get("rate_limit")
        try:
            return int(d["resources"]["core"]["remaining"])
        except (TypeError, KeyError, ValueError):
            return None


def fetch_repo(gh, slug, want_commit=False):
    """GitHub facts for one repo. Keys: full_name, archived, disabled, pushed_at,
    license, latest, latest_date, latest_kind (release | tag | none), last_commit;
    or {"error": "not-found" | "rate-limit" | "network" | "http-NNN"}."""
    st, d = gh.get(f"repos/{slug}")
    if st in (404, 410, 451):
        return {"error": "not-found"}
    if st != 200 or not isinstance(d, dict):
        return {"error": "rate-limit" if st == 429 else ("network" if st is None else f"http-{st}")}
    f = {"full_name": gh_slug(d.get("full_name")) or slug, "archived": bool(d.get("archived")),
         "disabled": bool(d.get("disabled")), "pushed_at": day(d.get("pushed_at")),
         "license": (d.get("license") or {}).get("spdx_id")}
    full = f["full_name"]
    st, r = gh.get(f"repos/{full}/releases/latest")
    if st == 200 and isinstance(r, dict) and r.get("tag_name"):
        f.update(latest=r["tag_name"], latest_date=day(r.get("published_at")), latest_kind="release")
    elif st == 404:
        st, t = gh.get(f"repos/{full}/tags?per_page=1")
        if st == 200 and isinstance(t, list):
            if t:
                f.update(latest=t[0].get("name"), latest_kind="tag")
            else:
                f.update(latest_kind="none")
    if want_commit and not f["archived"]:
        st, c = gh.get(f"repos/{full}/commits?per_page=1")
        if st == 200 and isinstance(c, list) and c:
            f["last_commit"] = day(((c[0].get("commit") or {}).get("committer") or {}).get("date"))
    return f


def classify_status(status_code, network_error=False):
    """alive / dead / unverified. Only an explicit 404 or 410 is dead: a block, a server
    error or a network failure is never proof that a product is gone."""
    if network_error or status_code is None:
        return "unverified"
    if status_code in (404, 410):
        return "dead"
    if 200 <= status_code < 400:
        return "alive"
    return "unverified"


def check_url(url, timeout=15.0):
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return classify_status(resp.status)
    except urllib.error.HTTPError as e:
        if e.code in (403, 405):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                            timeout=timeout) as resp:
                    return classify_status(resp.status)
            except urllib.error.HTTPError as e2:
                return classify_status(e2.code)
            except Exception:
                return classify_status(None, network_error=True)
        return classify_status(e.code)
    except Exception:
        return classify_status(None, network_error=True)


# ---------------------------------------------------------------- snapshot and flags

def load_snapshot(root):
    p = Path(root) / SNAPSHOT
    d = read_json(p) if p.exists() else {}
    d.setdefault("repos", {})
    d.setdefault("urls", {})
    return d


def snapshot_key(key, terms):
    """The key a repo slug or URL is stored under in the snapshot, which is committed and
    may be published: the key itself, or, when it contains a private term, a hash keyed
    with the private terms, so a reader without them cannot test a guessed name. Editing
    the terms changes the hash: those entries then start from no baseline, once."""
    if not terms or not private_hit(key, terms):
        return key
    secret = "\n".join(sorted(terms)).encode("utf-8")
    return "private:" + hmac.new(secret, key.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def public_entry(entry, terms):
    """A snapshot entry without the values that contain a private term (a renamed repo's
    full_name, say). A dropped release tag takes its kind and date along, so the next
    run does not see a "first release"."""
    out = {k: v for k, v in entry.items() if not (isinstance(v, str) and private_hit(v, terms))}
    if "latest" in entry and "latest" not in out:
        out.pop("latest_kind", None)
        out.pop("latest_date", None)
    return out


def repo_baseline(snap, slug, full=None, terms=()):
    """The snapshot entry of a repo: by its slug, else by its current full name; each
    under its stored key (hashed when private), else as written by an older run."""
    repos = snap["repos"]
    for k in (slug, full):
        if k:
            hit = repos.get(snapshot_key(k.lower(), terms)) or repos.get(k.lower())
            if hit:
                return hit
    return None


def url_baseline(snap, url, terms=()):
    return snap["urls"].get(snapshot_key(url, terms)) or snap["urls"].get(url)


def version(tag):
    m = re.search(r"(\d+)\.(\d+)", tag or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def bump(old, new):
    """Size of the step old -> new: first | major | minor | patch | other.
    Calendar versions (a year as the major number) count only a new year."""
    if not old:
        return "first"
    a, b = version(old), version(new)
    if a is None or b is None:
        return "other"
    if a[0] >= 1900 or b[0] >= 1900:
        return "major" if b[0] > a[0] else "patch"
    if b[0] > a[0]:
        return "major"
    if b[0] == a[0] and b[1] > a[1]:
        return "minor"
    return "patch"


def flags_for(n, f, base, today):
    """What changed enough to deserve a deep check, as [flag, detail] pairs."""
    ps, out = n.get("project_status"), []
    if n["kind"] == "repo":
        if f.get("error") == "not-found":
            if ps not in QUIET:
                out.append(["gone", f"{n['repo']} answers 404"])
            return out
        if f.get("error"):
            return out
        b = base or {}
        if f["full_name"].lower() != n["repo"].lower():
            out.append(["renamed", f"{n['repo']} -> {f['full_name']}"])
        if f.get("archived") and not b.get("archived") and ps not in QUIET:
            out.append(["archived", "archived on GitHub"])
        if f.get("disabled") and not b.get("disabled") and ps not in QUIET:
            out.append(["disabled", "disabled on GitHub"])
        if base and "license" in base and base.get("license") != f.get("license"):
            out.append(["licence", f"{base.get('license') or 'none'} -> {f.get('license') or 'none'}"])
        if (base and base.get("latest_kind") and f.get("latest_kind") and f.get("latest")
                and f["latest"] != base.get("latest")):
            old = base.get("latest") if base.get("latest_kind") != "none" else None
            step = bump(old, f["latest"])
            if step in ("major", "minor") or (step == "first" and f["latest_kind"] == "release"):
                out.append(["release", f"{old or 'none'} -> {f['latest']} ({step})"])
        pushed = f.get("pushed_at")
        if (pushed and not f.get("archived") and ps not in SLEEPY
                and days_between(pushed, today) > STALE_DAYS):
            was = (base and base.get("pushed_at") and base.get("checked")
                   and days_between(base["pushed_at"], base["checked"]) > STALE_DAYS)
            if not was:
                out.append(["stale", f"no push since {pushed}"])
        lc, sc = f.get("last_commit"), n.get("status_checked")
        if ps in REVIVABLE and lc and sc and lc > sc and not f.get("archived"):
            out.append(["revived", f"commit on {lc}, after the {sc} check"])
    elif n["kind"] == "url":
        if f.get("status") == "dead" and (base or {}).get("status") != "dead" and ps not in ("dead", "sunset"):
            out.append(["unreachable", f"{n['url']} answers 404/410"])
    return out


def select(notes, today, budget, due_days):
    """Mark the deep-pass set: every flagged note, then up to `budget` notes that are due
    (never checked, or last checked `due_days` or more ago): never-checked first, then
    notes without a repo (the cheap pass sees nothing for them), then the oldest."""
    for n in notes:
        n["deep"] = ("flagged: " + ", ".join(k for k, _ in n["flags"])) if n["flags"] else None
    pool = [n for n in notes if not n["deep"] and n["kind"] in ("repo", "url")
            and (not n["status_checked"] or days_between(n["status_checked"], today) >= due_days)]
    pool.sort(key=lambda n: (n["status_checked"] is not None, n["kind"] != "url",
                             n["status_checked"] or "", n["path"]))
    for n in pool[:max(budget, 0)]:
        n["deep"] = "never checked" if not n["status_checked"] else f"due (last check {n['status_checked']})"
    picked = [n for n in notes if n["flags"]] + pool[:max(budget, 0)]
    for i, n in enumerate(picked):
        n["deep_rank"] = i


# ---------------------------------------------------------------- scan

def run_scan(root, today, budget=40, due_days=90, overrides=None, gh=None, url_check=check_url,
             offline=False, workers=8):
    overrides = overrides or {}
    snap = load_snapshot(root)
    notes, aggregators = [], []
    for rel in note_paths(root):
        text, _, _ = load(Path(root) / rel)
        fm_text, body = split_fm(text)
        fm = parse_fm(fm_text)
        title, stem = str(fm.get("title") or Path(rel).stem), Path(rel).stem
        callout = has_callout(body)
        if fm.get("watch") is False:
            continue
        if fm.get("type") != "tool" and not callout:
            if fm.get("status-checked"):
                aggregators.append({"path": rel, "title": title, "links": wikilink_targets(body)})
            continue
        ps = fm.get("project-status")
        n = {"path": rel, "title": title, "stem": stem, "type": fm.get("type"),
             "note_date": day(fm.get("date")), "summary": fm.get("summary"),
             "status_checked": day(fm.get("status-checked")),
             "project_status": str(ps).strip().lower() if ps else None,
             "has_fm": fm_text is not None, "has_callout": callout,
             **resolve(fm, title, stem, body, overrides.get(rel))}
        notes.append(n)

    slugs = {}
    for n in notes:
        if n["kind"] == "repo":
            slugs.setdefault(n["repo"].lower(), n["repo"])
    want = {n["repo"].lower() for n in notes if n["kind"] == "repo" and n["project_status"] in REVIVABLE}
    urls = sorted({n["url"] for n in notes if n["kind"] == "url"})
    facts, github = {}, {"mode": "offline", "remaining": None}
    if offline:
        facts = {k: {"error": "offline"} for k in list(slugs) + urls}
    else:
        gh = gh or GitHub()
        rem = gh.remaining()
        github = {"mode": gh.mode, "remaining": rem}
        order = sorted(slugs)
        allow = len(order) if rem is None else max(0, (rem - 25) // 3)
        todo = order[:allow]
        with ThreadPoolExecutor(workers) as ex:
            for k, f in zip(todo, ex.map(lambda k: fetch_repo(gh, slugs[k], k in want), todo)):
                facts[k] = f
        for k in order[allow:]:
            facts[k] = {"error": "skipped-rate-limit"}
        with ThreadPoolExecutor(workers) as ex:
            for u, st in zip(urls, ex.map(url_check, urls)):
                facts[u] = {"status": st}

    terms = private_terms(root)
    for n in notes:
        if n["kind"] == "repo":
            f = facts.get(n["repo"].lower(), {"error": "not-fetched"})
            base = repo_baseline(snap, n["repo"], f.get("full_name"), terms)
        elif n["kind"] == "url":
            f = facts.get(n["url"], {"error": "not-fetched"})
            base = url_baseline(snap, n["url"], terms)
        else:
            f, base = {}, None
        n["facts"] = f
        n["flags"] = flags_for(n, f, base, today) if n["kind"] in ("repo", "url") else []
    select(notes, today, budget, due_days)
    return {"today": today, "budget": budget, "due_days": due_days, "github": github,
            "notes": notes, "aggregators": aggregators}


def summary_line(scan):
    ns = scan["notes"]
    c = lambda pred: sum(1 for n in ns if pred(n))
    return (f"{len(ns)} notes in scope: {c(lambda n: n['kind'] == 'repo')} repo, "
            f"{c(lambda n: n['kind'] == 'url')} url, {c(lambda n: n['kind'] == 'untracked')} untracked; "
            f"{c(lambda n: n['flags'])} flagged, {c(lambda n: n['deep'])} for the deep pass, "
            f"{c(lambda n: n['seed'])} to seed, {c(lambda n: n['ambiguous'])} ambiguous")


# ---------------------------------------------------------------- deep-pass outline

def slug(name):
    return re.sub(r"[^A-Za-z0-9_]", "", str(name).replace(" ", "_"))


def result_key(n):
    return slug(n["stem"]) or ("note_" + hashlib.sha1(n["path"].encode("utf-8")).hexdigest()[:8])


def redact(value, terms):
    """value with every private term (and its slug forms) replaced by [private]."""
    if isinstance(value, str):
        for t in terms:
            for form in sorted(term_forms(t), key=len, reverse=True):
                value = re.sub(r"(?<![^\W_])" + re.escape(form) + r"(?![^\W_])", "[private]", value, flags=re.I)
        return value
    if isinstance(value, list):
        return [redact(v, terms) for v in value]
    if isinstance(value, dict):
        return {k: redact(v, terms) for k, v in value.items()}
    return value


def build_outline(scan, workspace, root="."):
    """The deep-pass workspace. Private terms are redacted from what the agents get."""
    ws = Path(workspace)
    (ws / "results").mkdir(parents=True, exist_ok=True)
    terms = private_terms(root)
    items = []
    for n in scan["notes"]:
        if not n.get("deep") or private_hit(n["title"] + " " + n["path"], terms):
            continue                       # a note named after a private term is not researched
        f = {k: v for k, v in (n.get("facts") or {}).items() if v not in (None, "")}
        items.append({
            "name": n["title"], "note": n["path"], "note_date": n["note_date"],
            "note_summary": n["summary"],
            "repo": n["repo_url"] or "none (closed product or service)",
            "homepage": n.get("homepage") or n.get("url"),
            "previous_status": n["project_status"] or "never checked",
            "previous_check": n["status_checked"],
            "why_now": n["deep"],
            "flags": [f"{k}: {v}" for k, v in n["flags"]],
            "cheap_pass_facts": f or "n/a",
            "result_file": result_key(n) + ".json",
        })
    items = [redact(it, terms) for it in items]
    outline = {"topic": f"brain-watch status check {scan['today']}", "created": scan["today"],
               "purpose": "Re-check liveness, licence, releases and successor of tool notes; "
                          "say what in each note is now wrong.",
               "items": items,
               "execution": {"batch_size": 4, "items_per_agent": 8,
                             "output_dir": (ws / "results").as_posix()}}
    with open(ws / "outline.yaml", "w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(outline, fh, allow_unicode=True, sort_keys=False, width=200)
    shutil.copyfile(SKILL_DIR / "fields.yaml", ws / "fields.yaml")
    return len(items)


# ---------------------------------------------------------------- digest

SENT = re.compile(r"(?<=[a-z0-9\)\]'\"%])\.\s+(?=[A-Z(\[`])")


def find(d, k):
    if isinstance(d, dict):
        if k in d:
            return d[k]
        for v in d.values():
            r = find(v, k)
            if r is not None:
                return r
    return None


def clean(s):
    if s is None:
        return ""
    if isinstance(s, list):
        s = "; ".join(map(str, s))
    s = str(s).replace("\n- ", "; ").replace("\n", " ").strip()
    unc = "[uncertain]" in s
    s = re.sub(r"\s*\[uncertain\]\s*", " ", s).strip()
    s = re.sub(r"(?<!\\)\$", r"\\$", s)
    return (s + " (not confirmed)") if unc and not s.endswith("(not confirmed)") else s


def first(s, maxlen=230, n=1):
    """The first n sentences (at least ~40 characters), cut to maxlen at a word."""
    s = clean(s)
    parts = SENT.split(s)
    while n < len(parts) and len(". ".join(parts[:n])) < 40:
        n += 1
    out = ". ".join(parts[:n]).strip()
    if len(parts) > n and not out.endswith("."):
        out += "."
    if len(out) > maxlen:
        cut = out[:maxlen]
        for sep in ("; ", ", ", " "):
            k = cut.rfind(sep)
            if k > maxlen * 0.5:
                cut = cut[:k]
                break
        out = cut.rstrip(" ,;:") + "…"
    return out


def date_of(s):
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(s or ""))
    return m.group(0) if m else first(s, 60)


def negative(s):
    """True when a field says "no / unchanged / n/a / nothing"."""
    s = re.sub(r"^(repo|product|package)\s*:\s*", "", clean(s).lower())
    if not s or s.startswith(("n/a", "nothing", "none")):
        return True
    if s.startswith("no releases"):
        return False
    return bool(re.match(r"^(no|unchanged|product name unchanged|same)\b", s))


def material(changes):
    s = clean(changes).lower()
    return bool(s) and not s.startswith(("nothing material", "nothing", "no material", "none", "n/a", "no change"))


# ---------------------------------------------------------------- safe markdown
#
# The deep-pass results come from web pages and release notes, and the status box is
# published. Quartz renders raw HTML (rehype-raw), and its Obsidian plugin scans the text
# *after* entities are decoded for ==highlight== and ![[embed|alias]], which it rebuilds
# as raw HTML. So `&lt;` in the source would come back as `<` there. safe_md() escapes
# < > and character references, and also breaks up the markup those passes look for.

SAFE_URL = re.compile(r"https?://[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
                      r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*(?::\d{1,5})?"
                      r"(?:[/?#](?:[A-Za-z0-9._~!&*+,;=:@/?#-]|%[0-9A-Fa-f]{2})*)?")
MD_LINK = re.compile(r"(!?)\[([^\[\]\n]*)\]\(\s*<?([^\s<>()]*)>?(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)")
URL_CHAR = r"(?:(?!&(?:lt|gt);)[^\s<>\"'`\x00-\x03])"          # &lt; ends a URL, as < does
BARE_URL = re.compile(rf"https?://{URL_CHAR}+|(?<![\w.\\])www\.{URL_CHAR}+", re.I)
KEPT_LINK = re.compile(r"(?<![!\\])\[\[([^\[\]|#^\\\n]+)\]\]")


def safe_url(u):
    """u when it is a plain http(s) URL: a host name, an optional port, and a path, query
    and fragment of URL characters only (no quotes, brackets, parentheses, backslashes,
    spaces, $ or character references). Else None."""
    u = str(u or "").strip()
    ok = len(u) <= 2048 and SAFE_URL.fullmatch(u) and not re.search(r"&#?[A-Za-z0-9]+;", u)
    return u if ok else None


def safe_md(s, keep=()):
    """One line of Markdown that shows untrusted text as text.

    Escapes < and > and any character reference (`&lt;` already written stays as it is,
    so a second pass changes nothing). A link survives only to a URL that safe_url()
    accepts; an image becomes a link, or its alt text. A bare URL is kept whole when it
    passes the check and has no ==; else it is text, which GFM may still auto-link, but
    only as http(s). [[wikilinks]] survive only to a note title in `keep`, never as an
    embed or a link label. ==, %%, #tags and a leading link definition are broken up."""
    s = re.sub(r"[\x00-\x03]", "", str(s if s is not None else ""))
    s = re.sub(r"\s*[\r\n]+\s*", " ", s)
    held = []

    def hold(x):
        held.append(x)
        return f"\x00{len(held) - 1}\x00"

    def link(m):
        url = safe_url(m.group(3))
        if not url:
            return m.group(2)
        if not m.group(2).strip():
            return url                                         # a bare URL: see bare()
        return f"\x01{m.group(2)}\x02{hold(url)[1:-1]}\x03"   # the label is made safe below

    def bare(m):
        # A held URL is not broken up below, so one with == in it stays text: as text
        # next to more text, Quartz would pair it into a raw-HTML highlight.
        u = m.group(0)
        core = u.rstrip(".,;:!?*_~)]")
        if "==" not in core and safe_url(core if core.lower().startswith("http") else "http://" + core):
            return hold(core) + u[len(core):]
        return u

    def put(m):
        # Put a held URL or [[wikilink]] back. Nothing may touch a wikilink: after ! or \
        # it would be an embed, before ( or [ the label of a link.
        x, before, after = held[int(m.group(1))], m.string[:m.start()], m.string[m.end():]
        if not x.startswith("["):
            return x
        return (" " if before.endswith(("!", "\\")) else "") + x + (" " if after[:1] in ("(", "[", "\x00") else "")

    keep = set(keep)
    s = KEPT_LINK.sub(lambda m: hold(m.group(0)) if m.group(1) in keep else m.group(0), s)
    s = MD_LINK.sub(link, s)
    s = BARE_URL.sub(bare, s)
    s = re.sub(r"&(?!(?:amp|lt|gt);)(?=#?[A-Za-z0-9]+;)", "&amp;", s)
    s = s.replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"(\\?\[)(?=\\?\[)", r"\1 ", s)      # [[x]], ![[x]] (also as [\[x]])
    s = re.sub(r"(\\?=)(?=\\?=)", r"\1 ", s)        # ==highlight==
    s = re.sub(r"%(?=%)", "% ", s)                  # %%comment%% (cut before parsing)
    s = re.sub(r"(^| )#(?=[^\s#])", NBSP + "#", s)       # #tag: Quartz wants a plain space first
    s = re.sub(r"!(?=\[)", r"!\\", s)               # ![image](...)
    s = s.replace("](", "]\\(")                     # any other inline link
    s = re.sub(r"^(\s*)\[(?=[^\]]*\]:)", r"\1\\[", s)  # [ref]: definition
    s = re.sub(r"(?<!\\)((?:\\\\)*)\$", r"\1\\$", s)   # $…$ would be LaTeX
    s = s.replace("!\x01", "! \x01")                # what was cut out may leave ! before a link
    s = re.sub(r"\x01([^\x01-\x03]*)\x02(\d+)\x03", lambda m: f"[{m.group(1)}]({held[int(m.group(2))]})", s)
    return re.sub(r"\x00(\d+)\x00", put, s)


def link_titles(s, titles, self_name):
    done = {self_name}
    for t in titles:
        if t in done or len(t) < 4:
            continue
        pat = re.compile(r"(?<![\w\[/-])" + re.escape(t) + r"(?![\w\]-])")
        if pat.search(s):
            s = pat.sub(lambda m: "[[" + t + "]]", s, count=1)
            done.add(t)
    return s


def status_lines(n, r, titles, o=None):
    """(liveness, lines, changes) for one note's status box."""
    o = o or {}
    lv = clean(r.get("liveness")).split()[0].strip(".,;:").lower() if clean(r.get("liveness")) else ""
    lines = [f"**Verdict:** {first(r.get('liveness_evidence'), 260)}"]
    if n["kind"] != "repo":
        lines.append(f"**Latest release:** {first(r.get('last_release'), 130)} · "
                     f"**last dated update:** {date_of(r.get('last_commit'))} · "
                     f"**licence:** {first(r.get('license'), 120)}")
    else:
        lines.append(f"**Last release:** {first(r.get('last_release'), 110)} · "
                     f"**last commit:** {date_of(r.get('last_commit'))} · "
                     f"**licence:** {first(r.get('license'), 120)}")
    m = re.search(r"https?://\S+", str(r.get("repo_url") or ""))
    url = safe_url(m.group(0).rstrip(').,;')) if m else None
    forge = url and re.search(r"github\.com|gitlab\.com|codeberg\.org|huggingface\.co", url)
    lab = "Repo" if (forge and n["kind"] == "repo") else "Source"
    repo_line = (f"**{lab}:** {url}" if url
                 else f"**Source:** {first(r.get('repo_url'), 140)}")
    mv = first(r.get("moved_or_renamed"), 260, 2)
    if not negative(r.get("moved_or_renamed")) and not (
            "unchanged" in mv.lower() and not re.search(r"renam|moved to|rebrand|->|→", mv.lower())):
        repo_line += f" — **moved/renamed:** {mv}"
    lines.append(repo_line)
    if not negative(r.get("archived_or_deprecated")):
        lines.append(f"**Retired:** {first(r.get('archived_or_deprecated'), 200)}")
    if not clean(r.get("successor_or_replacement")).lower().startswith("n/a"):
        su = (clean(o["successor_or_replacement"]) if "successor_or_replacement" in o
              else first(r.get("successor_or_replacement"), 300, 2))
        lab2 = "Use instead" if lv in ("dead", "stale", "sunset", "slowing") else "Successor / fallback"
        lines.append(f"**{lab2}:** {link_titles(su, titles, n['stem'])}")
    changes = ""
    if "changes_since_note" in o:
        changes = clean(o["changes_since_note"])
    else:
        parts = SENT.split(clean(r.get("changes_since_note")))
        if parts and parts[0].lower().startswith("nothing material"):
            parts = parts[1:]
        while len(parts) > 1 and len(parts[0]) < 25:
            parts = parts[1:]
        if parts and parts[0].strip():
            changes = first(". ".join(parts), 320, 2)
    if changes:
        lines.append(f"**Changed since this note:** {changes}")
    return lv, lines, changes


# brain-export/scripts/privacy_sweep.py mirrors private_terms(), term_forms(), private_hit()
# and redact() (as mask()); change both together. Its tests compare the two.
def private_terms(root):
    """Terms from the "Always cut" section of content/_privacy.md and of the git-ignored
    content/_privacy.local.md (for names whose mere presence in the repository is a leak)."""
    terms = []
    for name in ("_privacy.md", "_privacy.local.md"):
        p = Path(root) / "content" / name
        if not p.exists():
            continue
        text = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S)
        sec = re.search(r"^##\s+Always cut[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
        if not sec:
            continue
        for line in sec.group(1).splitlines():
            m = re.match(r"\s*[-*]\s+(.+)", line)
            if not m:
                continue
            item = m.group(1).strip()
            q = re.match(r'"([^"]+)"|“([^”]+)”', item)
            term = (q.group(1) or q.group(2)) if q else re.split(r"\s+[—–-]\s+", item)[0].strip()
            if len(term) >= 2 and term not in terms:
                terms.append(term)
    return terms


def fold(s):
    """s without diacritics: ł → l, then NFKD with the combining marks dropped
    ("Żółw Łąka" → "Zolw Laka"), as names are often written in slugs and URLs."""
    s = unicodedata.normalize("NFKD", s.replace("ł", "l").replace("Ł", "L"))
    return "".join(c for c in s if not unicodedata.combining(c))


def term_forms(term):
    """A term as written and as it shows up in slugs and URLs: "Acme Labs" also matches
    acmelabs, acme-labs and acme_labs, and "Łąka Wiśnia" also lakawisnia, laka-wisnia.
    A folded form shorter than 4 letters is left out: "Wąs" would match "was"."""
    words = re.split(r"[\s_-]+", term.strip())
    forms = {term.strip(), "".join(words), "-".join(words), "_".join(words)}
    if len(re.sub(r"\W", "", fold(term))) >= 4:
        forms |= {fold(f) for f in forms}
    return forms - {""}


def private_hit(text, terms):
    return any(re.search(r"(?<![^\W_])" + re.escape(form) + r"(?![^\W_])", text, re.I)
               for t in terms for form in term_forms(t))


def build_digest(root, scan, workspace):
    ws = Path(workspace)
    flat, bad = {}, []
    for p in sorted((ws / "results").glob("*.json")):
        try:
            d = read_json(p)
        except (ValueError, OSError):
            bad.append(p.name)
            continue
        flat[p.stem] = {k: find(d, k) for k in FIELDS}
    ovr = read_json(ws / "overrides.json") if (ws / "overrides.json").exists() else {}
    terms = private_terms(root)
    titles = sorted({n["stem"] for n in scan["notes"]}, key=len, reverse=True)
    out = {"notes": {}, "held": [], "missing": [], "bad": bad}
    for n in scan["notes"]:
        if not n.get("deep"):
            continue
        key = result_key(n)
        r, o = flat.get(key), ovr.get(key, {})
        if "lines" in o:
            lv, lines, changes = o.get("liveness", ""), list(o["lines"]), clean(o.get("changes_since_note"))
        elif r:
            lv, lines, changes = status_lines(n, {**r, **o}, titles, o)
        else:
            out["missing"].append(n["path"])
            continue
        raw = [str(x) for x in lines] + [str(changes)]
        lines, changes = [safe_md(x, titles) for x in lines], safe_md(changes, titles)   # as written
        if lv not in VOCAB:
            out["held"].append({"path": n["path"], "reason": f"liveness {lv or '(empty)'!r} is not one of {', '.join(VOCAB)}"})
            continue
        full = (n.get("facts") or {}).get("full_name")
        new_repo = ("https://github.com/" + full) if full and any(k == "renamed" for k, _ in n["flags"]) else None
        # Both forms: a link label survives escaping as plain text, a space may become NBSP.
        if private_hit(" ".join(raw + lines + [changes, new_repo or ""]), terms):
            out["held"].append({"path": n["path"], "reason": "a line matched a private term"})
            continue
        entry = {"liveness": lv, "lines": lines, "changes": changes, "enhance": material(changes)}
        if new_repo:
            entry["repo"] = new_repo
        out["notes"][n["path"]] = entry
    return out


# ---------------------------------------------------------------- apply

def strip_old(lines):
    out, i = [], 0
    while i < len(lines):
        if MARK.match(lines[i]):
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                i += 1
            while i < len(lines) and not lines[i].strip() and out and not out[-1].strip():
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return out


def insert_callout(body, block):
    """Put the status box right under the first H1 outside code fences (else at the top
    of the body), replacing any earlier "Status check YYYY-MM-DD" box."""
    lines = strip_old(body.split("\n"))
    fence, idx = False, None
    for i, line in enumerate(lines):
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
            continue
        if not fence and line.startswith("# "):
            idx = i + 1
            break
    if idx is None:
        idx = 0
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        head, lead = lines[:idx], []
    else:
        head, lead = lines[:idx], [""]
    rest = lines[idx:]
    while rest and not rest[0].strip():
        rest = rest[1:]
    return "\n".join(head + lead + block + [""] + (rest if rest else []))


def render_box(today, lv, lines, keep=()):
    """The status box. Each line goes through safe_md() again: digest.json may have been
    edited (translated) since the digest wrote it."""
    lines = [safe_md(x, keep) for x in lines]
    return [f"> [!{CALLOUT[lv]}] Status check {today} — {lv}"] + [f"> {x}" if x else ">" for x in lines]


def apply_changes(root, scan, digest=None, dry=False):
    """Write seeds, status boxes and frontmatter. Returns what changed (or would)."""
    today, entries = scan["today"], (digest or {}).get("notes", {})
    terms = private_terms(root)
    titles = {n["stem"] for n in scan["notes"]}
    done = {"seeded": [], "status": [], "skipped": [], "held": []}
    for n in scan["notes"]:
        entry, seed = entries.get(n["path"]), n.get("seed") or {}
        if seed and private_hit(" ".join(str(v) for v in seed.values()), terms):
            done["held"].append(n["path"])
            seed = {}
        # digest.json may have been edited (translated) since the digest checked it
        if entry and (entry.get("liveness") not in CALLOUT
                      or private_hit(" ".join(str(x) for x in entry.get("lines") or []), terms)):
            if n["path"] not in done["held"]:
                done["held"].append(n["path"])
            entries, entry = {k: v for k, v in entries.items() if k != n["path"]}, None   # still flagged next run
        if not entry and not seed:
            continue
        p = Path(root) / n["path"]
        text, crlf, bom = load(p)
        fm, body = split_fm(text)
        if fm is None:
            done["skipped"].append(n["path"])
            continue
        new_fm, new_body = fm, body
        seeded = False
        for k in ("repo", "homepage", "watch"):
            if k in seed and not re.search(rf"^{k}:", new_fm, re.M):
                new_fm = set_fm(new_fm, k, fm_value(seed[k]))
                seeded = True
        if entry:
            new_fm = set_fm(new_fm, "status-checked", today)
            new_fm = set_fm(new_fm, "project-status", entry["liveness"])
            if safe_url(entry.get("repo")) and not private_hit(entry["repo"], terms):
                new_fm = set_fm(new_fm, "repo", fm_value(entry["repo"]))
            new_body = insert_callout(body, render_box(today, entry["liveness"], entry["lines"], titles))
        out = f"---\n{new_fm}\n---\n" + new_body
        if out == text:
            continue
        if seeded:
            done["seeded"].append(n["path"])
        if entry:
            done["status"].append(n["path"])
        if not dry:
            save(p, out, crlf, bom)
    if not dry:
        write_snapshot(root, scan, researched=entries)
    return done


def write_snapshot(root, scan, researched=()):
    """The cheap-pass facts as the next run's baseline. Entries no note points at any
    more are dropped. A repo or URL keeps its previous entry when it could not be read,
    or when it was flagged but no note on it was researched this run: otherwise the
    next run would compare with the new facts and the flag would be lost.

    The snapshot is committed, so a key that contains a private term is stored hashed
    (snapshot_key) and a value that contains one is left out (public_entry)."""
    old, today = load_snapshot(root), scan["today"]
    terms = private_terms(root)
    sk = lambda k: snapshot_key(k, terms)
    researched = set(researched)
    fresh = {}
    for n in scan["notes"]:
        key = n["repo"].lower() if n["kind"] == "repo" else n.get("url")
        if key and (not n["flags"] or n["path"] in researched):
            fresh[key] = True
        elif key:
            fresh.setdefault(key, False)
    repos, urls = {}, {}
    for n in scan["notes"]:
        f = n.get("facts") or {}
        if n["kind"] == "repo":
            readable = not f.get("error") or f.get("error") == "not-found"
            prev = repo_baseline(old, n["repo"], f.get("full_name"), terms)
            if readable and (fresh[n["repo"].lower()] or prev is None):
                key = (f.get("full_name") or n["repo"]).lower()
                repos[sk(key)] = public_entry({**f, "checked": today}, terms)  # keep None: "no licence" is a fact
            elif prev is not None:
                key = n["repo"].lower() if repo_baseline(old, n["repo"], None, terms) else f["full_name"].lower()
                repos[sk(key)] = public_entry(prev, terms)
        elif n["kind"] == "url":
            prev = url_baseline(old, n["url"], terms)
            if f.get("status") in ("alive", "dead") and (fresh[n["url"]] or prev is None):
                urls[sk(n["url"])] = {"status": f["status"], "checked": today}
            elif prev is not None:
                urls[sk(n["url"])] = public_entry(prev, terms)
            elif f.get("status"):
                urls[sk(n["url"])] = {"status": f["status"], "checked": today}
    write_json(Path(root) / SNAPSHOT, {"updated": today, "repos": repos, "urls": urls})


# ---------------------------------------------------------------- report

def esc(s, keep=(), terms=()):
    """Untrusted text (GitHub tags, deep-pass results, links) for one report line. The
    private terms are checked on the text before it is escaped, since escaping can split
    one ("Team #2" gets a no-break space)."""
    if terms and private_hit(str(s if s is not None else ""), terms):
        return "(withheld: a private term)"
    return safe_md(s, keep)


def cell(s, terms=()):
    return esc(s, (), terms).replace("|", "/")


def build_report(root, scan, digest=None, dry=False):
    today, notes = scan["today"], scan["notes"]
    terms = private_terms(root)
    text = lambda s, keep=(): esc(s, keep, terms)      # checked raw, then escaped
    col = lambda s: cell(s, terms)
    stems = {}
    for n in notes:
        stems[n["stem"]] = stems.get(n["stem"], 0) + 1

    def wl(n, table=False):
        if stems[n["stem"]] == 1:
            return f"[[{n['stem']}]]"
        bar = "\\|" if table else "|"           # a bare | would split a table cell
        return f"[[{n['path'][len('content/'):-3]}{bar}{n['stem']}]]"

    entries = (digest or {}).get("notes", {})
    flagged = [n for n in notes if n["flags"]]
    deep = sorted((n for n in notes if n["deep"]), key=lambda n: n.get("deep_rank", 0))
    researched = [n for n in deep if n["path"] in entries]
    errors = [n for n in notes if (n.get("facts") or {}).get("error")]
    unverified = [n for n in notes if (n.get("facts") or {}).get("status") == "unverified"]
    secret = lambda n: private_hit(" ".join(str(v) for v in n["seed"].values()), terms)
    seeded = [n for n in notes if n["seed"] and not secret(n)]
    held_seeds = [n for n in notes if n["seed"] and secret(n)]
    ambiguous = [n for n in notes if n["ambiguous"]]
    untracked = [n for n in notes if n["kind"] == "untracked" and not n["ambiguous"]]

    L = ["---", f'title: "Watch Report — {today}"', f"date: {today}", "type: basic-note",
         'tags: ["report", "watch", "tools"]', "agent-created: true",
         f'summary: "/b:watch {"dry run" if dry else "run"} on {today}: {len(flagged)} flagged, '
         f'{len(researched) if not dry else len(deep)} {"to research" if dry else "researched"}."',
         "---", "", f"# Watch Report — {today}", ""]
    gh = scan.get("github") or {}
    L.append(f"{'**Dry run**: nothing in the vault was written. ' if dry else ''}"
             f"{summary_line(scan)}. GitHub access: {gh.get('mode')}"
             f"{', ' + str(gh.get('remaining')) + ' requests left before the run' if gh.get('remaining') is not None else ''}.")
    L.append("")

    L += ["## Flags", ""]
    if flagged:
        L += ["| Note | Flag | Detail |", "|---|---|---|"]
        for n in flagged:
            for k, v in n["flags"]:
                L.append(f"| {wl(n, True)} | {k} | {col(v)} |")
    else:
        L.append("Nothing changed in any tracked repository or homepage since the last snapshot.")
    L.append("")

    if dry:
        L += ["## Would research", ""]
        if deep:
            L += ["| Note | Why | Status now |", "|---|---|---|"]
            for n in deep:
                L.append(f"| {wl(n, True)} | {col(n['deep'])} | {n['project_status'] or '-'} |")
        else:
            L.append("Nothing is flagged or due.")
        L.append("")
    else:
        L += ["## Researched", ""]
        if researched:
            L += ["| Note | Why | Status |", "|---|---|---|"]
            for n in researched:
                e = entries[n["path"]]
                was = n["project_status"] or "never checked"
                lv = col(e["liveness"])
                st = lv if was == e["liveness"] else f"{was} → **{lv}**"
                L.append(f"| {wl(n, True)} | {col(n['deep'])} | {st} |")
        else:
            L.append("No note needed a deep check this run.")
        missing = (digest or {}).get("missing", [])
        if missing:
            L += ["", "No result came back for: " + ", ".join(f"`{p}`" for p in missing) + "."]
        L.append("")

        enh = [n for n in researched if entries[n["path"]].get("enhance")]
        L += ["## Notes to refresh (`/b:enhance`)", ""]
        if enh:
            L.append("The note body is now wrong in the way the status box says. Nothing was changed outside the box.")
            L.append("")
            for n in enh:
                L.append(f"- `/b:enhance {wl(n)}` — {text(first(entries[n['path']]['changes'], 220), stems)}")
        else:
            L.append("None.")
        L.append("")

        cur = [n for n in researched if entries[n["path"]]["liveness"] in ("stale", "dead", "sunset")
               and entries[n["path"]]["liveness"] != n["project_status"]]
        L += ["## Curate candidates (`/b:curate`)", ""]
        if cur:
            L.append("Newly stale, dead or sunset. Nothing was moved: run `/b:curate` to decide.")
            L.append("")
            for n in cur:
                L.append(f"- {wl(n)} — {text(entries[n['path']]['liveness'])}")
        else:
            L.append("None.")
        L.append("")

    changed = {n["stem"] for n in flagged if any(k in ("gone", "archived", "disabled", "renamed", "licence", "unreachable") for k, _ in n["flags"])}
    changed |= {n["stem"] for n in researched if entries[n["path"]]["liveness"] != n["project_status"]}
    aggs = [(a, sorted(set(a["links"]) & changed)) for a in scan.get("aggregators", [])]
    aggs = [(a, hit) for a, hit in aggs if hit]
    L += ["## Aggregators to refresh", ""]
    if aggs:
        for a, hit in aggs:
            L.append(f"- [[{Path(a['path']).stem}]] links " + ", ".join(f"[[{h}]]" for h in hit))
    else:
        L.append("None.")
    L.append("")

    L += ["## Frontmatter seeded" + (" (would be)" if dry else ""), ""]
    if seeded:
        def written(n):
            """The value apply writes: a confirmed rename wins over the seed."""
            seed = n["seed"].get("repo") or n["seed"].get("homepage") or "watch: false"
            moved = entries.get(n["path"], {}).get("repo")
            if moved and moved != seed and not private_hit(moved, terms):
                return f"{moved} (moved from {seed})"
            return seed

        # A researched note's link was just checked by the deep pass.
        check = [n for n in seeded if n["basis"] == "single-link" and n["path"] not in entries]
        L.append(f"{len(seeded)} notes {'would get' if dry else 'got'} `repo:` / `homepage:` for the first time. "
                 "A wrong value is fixed by editing the field; set `watch: false` to stop tracking a note.")
        if check:
            L += ["", "Taken from the only GitHub link in the note (check these):", ""]
            for n in check:
                L.append(f"- {wl(n)} → {text(written(n))}")
        L += ["", "<details><summary>All seeded notes</summary>", ""]
        for n in seeded:
            L.append(f"- {wl(n)} → {text(written(n))} ({n['basis']})")
        L += ["", "</details>"]
    else:
        L.append("None.")
    L.append("")

    L += ["## Notes that need a link", ""]
    if ambiguous or untracked:
        L.append("Add `repo:` or `homepage:` to the note (or `watch: false`).")
        L.append("")
        for n in ambiguous:
            cands = ["(a private link)" if private_hit(c, terms) else text(c) for c in n["ambiguous"]]
            why = "several candidates" if len(cands) > 1 else "one link, but its site is not named after the note"
            L.append(f"- {wl(n)} — {why}: " + ", ".join(cands))
        for n in untracked:
            L.append(f"- {wl(n)} — no repo or product link in the note")
    else:
        L.append("None.")
    L.append("")

    L += ["## Not checked", ""]
    if errors or unverified:
        for n in errors:
            L.append(f"- {wl(n)} — {n['facts']['error']}")
        for n in unverified:
            L.append(f"- {wl(n)} — {text(n['url'])} did not answer clearly (blocked, server error or network); not counted as dead")
    else:
        L.append("None.")
    L.append("")

    held = (digest or {}).get("held", [])
    if held or held_seeds or (digest or {}).get("bad"):
        L += ["## Held back", ""]
        for h in held:
            L.append(f"- `{h['path']}` — {h['reason']}; its status box was not written")
        for n in held_seeds:
            L.append(f"- `{n['path']}` — the proposed link matched a private term; no `repo:` / `homepage:` was written")
        for b in (digest or {}).get("bad", []):
            name = re.sub(r"[^\w.() -]", "_", b)      # an agent named the file: no markup
            L.append(f"- `results/{name}` — not valid JSON")
        L.append("")

    guarded = []
    for line in L:
        guarded.append("(line withheld: it matched a private term)" if private_hit(line, terms) else line)
    return "\n".join(guarded).rstrip("\n") + "\n"


# ---------------------------------------------------------------- CLI

def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="watch.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=".", help="vault root (default: current directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="cheap pass -> scan.json")
    s.add_argument("--out", required=True)
    s.add_argument("--today", default=dt.date.today().isoformat())
    s.add_argument("--deep-budget", type=int, default=40)
    s.add_argument("--due-days", type=int, default=90)
    s.add_argument("--seed", help="JSON {note path: {repo|homepage|watch}} used instead of guessing")
    s.add_argument("--offline", action="store_true", help="no network: resolve and seed only")
    o = sub.add_parser("outline", help="deep-pass workspace from scan.json")
    o.add_argument("scan")
    o.add_argument("workspace")
    d = sub.add_parser("digest", help="deep-pass results -> digest.json")
    d.add_argument("scan")
    d.add_argument("workspace")
    d.add_argument("--out", required=True)
    p = sub.add_parser("apply", help="write status boxes, frontmatter, snapshot")
    p.add_argument("scan")
    p.add_argument("--digest")
    p.add_argument("--dry", action="store_true")
    r = sub.add_parser("report", help="markdown report")
    r.add_argument("scan")
    r.add_argument("--digest")
    r.add_argument("--out", required=True)
    r.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    root = a.root

    if a.cmd == "scan":
        seed = read_json(a.seed) if a.seed else None
        scan = run_scan(root, a.today, a.deep_budget, a.due_days, seed, offline=a.offline)
        write_json(a.out, scan)
        print(summary_line(scan))
    elif a.cmd == "outline":
        print(build_outline(read_json(a.scan), a.workspace, root), "items in", Path(a.workspace) / "outline.yaml")
    elif a.cmd == "digest":
        dg = build_digest(root, read_json(a.scan), a.workspace)
        write_json(a.out, dg)
        print(f"{len(dg['notes'])} status boxes, {len(dg['held'])} held back, "
              f"{len(dg['missing'])} without a result, {len(dg['bad'])} unreadable")
    elif a.cmd == "apply":
        done = apply_changes(root, read_json(a.scan), read_json(a.digest) if a.digest else None, a.dry)
        verb = "would change" if a.dry else "changed"
        print(f"{verb}: {len(done['seeded'])} seeded, {len(done['status'])} status boxes"
              + (f", {len(done['skipped'])} skipped (no frontmatter)" if done["skipped"] else "")
              + ("" if a.dry else f"; snapshot: {SNAPSHOT}"))
        for k in ("status", "seeded"):
            for path in done[k]:
                print(f"  {k}: {path}")
    elif a.cmd == "report":
        text = build_report(root, read_json(a.scan), read_json(a.digest) if a.digest else None, a.dry)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("report:", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
