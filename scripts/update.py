#!/usr/bin/env python3
"""Keep the skill current. Checks GitHub for a newer release and applies it.

    update.py                      # check (cached 24h), print status, exit
    update.py --auto --quiet       # what SKILL.md runs at the start of a session
    update.py --apply              # update now, whatever the cache says
    update.py --check --force      # ignore the cache, hit the network
    update.py --status             # local version, remote version, cache age
    update.py --off / --on         # disable / re-enable automatic updating

Design constraints, because this runs before real work:

  * Cheap. One cached HTTP GET per day, 6s timeout, and it exits 0 on any network
    failure. Being offline must never block the skill.
  * Non-destructive. `data/sources.json` is user state — sources added locally with
    add_source.py live there. Updates MERGE the registry (union by id, newer
    `verified` wins, local-only entries always survive) and never overwrite it.
  * Conservative about breaking changes. --auto applies minor and patch releases on
    its own; a major bump means the schema moved, so it reports and waits for a human.

Python 3 stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import pathlib
import shutil
import sys
import tarfile
import time
import urllib.request

from common import C, SKILL_DIR, CACHE_DIR, http_get

REPO = "m-bikko/ui-arsenal"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"
TARBALL = f"https://codeload.github.com/{REPO}/tar.gz/refs/heads/main"

VERSION_FILE = SKILL_DIR / "VERSION"
STATE = CACHE_DIR / "update.json"
OPT_OUT = SKILL_DIR / ".no-autoupdate"
CHECK_TTL = 24 * 3600
NET_TIMEOUT = 6

# Files the update owns. data/sources.json is deliberately absent — it is merged,
# never replaced. Anything else the user put in the skill directory is left alone.
OWNED = ("SKILL.md", "README.md", "LICENSE", "VERSION", "scripts", "references", "wiki")


def parse_version(text: str) -> tuple[int, ...]:
    parts = (text or "").strip().lstrip("v").split(".")
    out = []
    for p in parts[:3]:
        digits = "".join(c for c in p if c.isdigit())
        out.append(int(digits) if digits else 0)
    while len(out) < 3:
        out.append(0)
    return tuple(out)


def local_version() -> str:
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(d: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d, indent=2), encoding="utf-8")


def disabled() -> bool:
    return OPT_OUT.exists() or os.environ.get("UI_ARSENAL_NO_UPDATE") == "1"


def remote_version(timeout: int = NET_TIMEOUT) -> str | None:
    status, body = http_get(f"{RAW}/VERSION", timeout=timeout)
    if status != 200 or not body:
        return None
    text = body.decode("utf-8", "replace").strip()
    return text if text and text[0].isdigit() else None


def check(force: bool = False) -> dict:
    """Returns {local, remote, behind, bump, cached, error}. Never raises."""
    lv = local_version()
    st = load_state()
    age = time.time() - st.get("checked_at", 0)
    if not force and age < CHECK_TTL and st.get("remote"):
        rv = st["remote"]
        cached = True
    else:
        rv = remote_version()
        cached = False
        if rv:
            save_state({"checked_at": time.time(), "remote": rv, "local": lv})
        else:
            # Remember the failure so a flaky network does not retry every invocation.
            st["checked_at"] = time.time()
            save_state(st)
            return {"local": lv, "remote": None, "behind": False,
                    "bump": None, "cached": False, "error": "network"}
    lt, rt = parse_version(lv), parse_version(rv)
    bump = None
    if rt > lt:
        bump = "major" if rt[0] > lt[0] else ("minor" if rt[1] > lt[1] else "patch")
    return {"local": lv, "remote": rv, "behind": rt > lt,
            "bump": bump, "cached": cached, "error": None}


def merge_sources(local_path: pathlib.Path, incoming: dict) -> tuple[dict, dict]:
    """Union by id. Newer `verified` wins. Local-only entries always survive."""
    try:
        cur = json.loads(local_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return incoming, {"kept_local": 0, "updated": 0, "added": 0, "total": len(incoming["sources"])}

    by_id = {s["id"]: s for s in cur.get("sources", [])}
    stats = {"kept_local": 0, "updated": 0, "added": 0}
    upstream_ids = set()

    for up in incoming.get("sources", []):
        upstream_ids.add(up["id"])
        mine = by_id.get(up["id"])
        if mine is None:
            by_id[up["id"]] = up
            stats["added"] += 1
        elif (up.get("verified") or "") >= (mine.get("verified") or ""):
            by_id[up["id"]] = up
            stats["updated"] += 1
        # else: the local copy was verified more recently — keep it.

    stats["kept_local"] = len([i for i in by_id if i not in upstream_ids])
    merged = dict(incoming)
    merged["sources"] = sorted(by_id.values(), key=lambda s: s["id"])
    merged["updated"] = max(
        filter(None, [cur.get("updated"), incoming.get("updated")]), default="")
    stats["total"] = len(merged["sources"])
    return merged, stats


def git_managed() -> bool:
    return (SKILL_DIR / ".git").is_dir()


def apply_update(verbose: bool = True) -> bool:
    info = check(force=True)
    if info["error"]:
        if verbose:
            print(f"{C['y']}update check failed (offline?) — nothing done{C['x']}",
                  file=sys.stderr)
        return False
    if not info["behind"]:
        if verbose:
            print(f"{C['g']}already current: {info['local']}{C['x']}", file=sys.stderr)
        return False

    say = (lambda m: print(m, file=sys.stderr)) if verbose else (lambda m: None)
    say(f"{C['b']}updating {info['local']} -> {info['remote']} ({info['bump']}){C['x']}")

    try:
        req = urllib.request.Request(TARBALL, headers={"User-Agent": "ui-arsenal-update"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            blob = resp.read()
    except Exception as exc:  # noqa: BLE001 — network failure is a normal outcome here
        say(f"{C['r']}download failed: {exc}{C['x']}")
        return False

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = CACHE_DIR / f"backup-{info['local']}-{stamp}"
    tmp = CACHE_DIR / f"incoming-{stamp}"
    try:
        tmp.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
            members = [m for m in tar.getmembers()
                       if not (m.name.startswith("/") or ".." in m.name)]
            try:
                tar.extractall(tmp, members=members, filter="data")
            except TypeError:  # Python < 3.12 has no filter= argument
                tar.extractall(tmp, members=members)
        roots = [p for p in tmp.iterdir() if p.is_dir()]
        if not roots:
            say(f"{C['r']}tarball had no root directory{C['x']}")
            return False
        src = roots[0]

        # Merge the registry first — if this fails, nothing has been touched yet.
        incoming_sources = json.loads((src / "data" / "sources.json").read_text("utf-8"))
        merged, stats = merge_sources(SKILL_DIR / "data" / "sources.json", incoming_sources)

        backup.mkdir(parents=True, exist_ok=True)
        for name in (*OWNED, "data"):
            cur = SKILL_DIR / name
            if cur.exists():
                (shutil.copytree if cur.is_dir() else shutil.copy2)(cur, backup / name)

        for name in OWNED:
            incoming = src / name
            if not incoming.exists():
                continue
            target = SKILL_DIR / name
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            (shutil.copytree if incoming.is_dir() else shutil.copy2)(incoming, target)

        out = SKILL_DIR / "data" / "sources.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", "utf-8")

        for p in (SKILL_DIR / "scripts").glob("*.py"):
            p.chmod(p.stat().st_mode | 0o111)
        shutil.rmtree(SKILL_DIR / "scripts" / "__pycache__", ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        say(f"{C['r']}update failed: {exc}{C['x']}")
        say(f"{C['dim']}backup (if written): {backup}{C['x']}")
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    save_state({"checked_at": time.time(), "remote": info["remote"],
                "local": info["remote"], "last_update": stamp})
    say(f"{C['g']}updated to {info['remote']}{C['x']}  "
        f"{C['dim']}registry: {stats['total']} sources "
        f"({stats['added']} added, {stats['updated']} refreshed, "
        f"{stats['kept_local']} local-only kept){C['x']}")
    say(f"{C['dim']}backup: {backup}{C['x']}")
    if git_managed():
        say(f"{C['y']}note: this is a git checkout — files now differ from HEAD. "
            f"`git -C {SKILL_DIR} status` to see what moved.{C['x']}")
    return True


def cmd_auto(quiet: bool) -> int:
    """What SKILL.md runs. Silent unless something actually happened."""
    if disabled():
        return 0
    info = check()
    if info["error"] or not info["behind"]:
        return 0
    if info["bump"] == "major":
        print(f"{C['y']}ui-arsenal {info['local']} -> {info['remote']} is a MAJOR "
              f"release (schema may have moved). Not applied automatically.{C['x']}\n"
              f"{C['dim']}Review github.com/{REPO} then run: "
              f"python3 {SKILL_DIR}/scripts/update.py --apply{C['x']}", file=sys.stderr)
        return 0
    apply_update(verbose=not quiet)
    return 0  # never block the session on an update outcome


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--auto", action="store_true",
                   help="check and apply minor/patch updates; silent when current")
    p.add_argument("--check", action="store_true", help="check only, print result")
    p.add_argument("--apply", action="store_true", help="download and apply now")
    p.add_argument("--status", action="store_true", help="versions and cache age")
    p.add_argument("--force", action="store_true", help="ignore the 24h check cache")
    p.add_argument("--quiet", action="store_true", help="suppress progress output")
    p.add_argument("--off", action="store_true", help="disable automatic updating")
    p.add_argument("--on", action="store_true", help="re-enable automatic updating")
    args = p.parse_args()

    if args.off:
        OPT_OUT.write_text("automatic updates disabled; remove this file to re-enable\n")
        print(f"auto-update off ({OPT_OUT})")
        return 0
    if args.on:
        OPT_OUT.unlink(missing_ok=True)
        print("auto-update on")
        return 0

    if args.status:
        st = load_state()
        age = time.time() - st.get("checked_at", 0)
        print(f"  local       {local_version()}")
        print(f"  remote      {st.get('remote') or '(not checked yet)'}")
        print(f"  last check  {int(age/3600)}h ago" if st.get("checked_at") else
              "  last check  never")
        print(f"  auto-update {'OFF' if disabled() else 'on'}")
        print(f"  skill dir   {SKILL_DIR}")
        return 0

    if args.apply:
        return 0 if apply_update() else 1
    if args.auto:
        return cmd_auto(args.quiet)

    info = check(force=args.force)
    if info["error"]:
        print(f"{C['y']}could not reach GitHub — skipping{C['x']}")
        return 0
    if info["behind"]:
        print(f"{C['y']}update available: {info['local']} -> {info['remote']} "
              f"({info['bump']}){C['x']}")
        print(f"{C['dim']}apply: python3 {SKILL_DIR}/scripts/update.py --apply{C['x']}")
    else:
        src = "cached" if info["cached"] else "checked"
        print(f"{C['g']}current: {info['local']}{C['x']} {C['dim']}({src}){C['x']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
