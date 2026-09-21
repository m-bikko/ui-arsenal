#!/usr/bin/env python3
"""Add a source to data/sources.json. Probes the URL and fills `access` for you.

    add_source.py --url https://newsite.dev \
                  --id newsite --name "New Site" \
                  --tags shader,background,webgl --dim 2d,3d --stack react,next \
                  --why "One sentence on what this gives you that others do not."

    add_source.py --url https://newsite.dev --id newsite --name "New Site" \
                  --tags x --why "..." --dry-run      # print, do not write

    add_source.py --reverify                          # re-probe EVERY source,
                                                      # report drift, bump dates

Rules enforced here so the registry stays trustworthy:
  * `id` must be unique and kebab-case
  * `why` is required and must not be boilerplate — it is what makes the
    registry searchable and what a future agent reads to choose
  * `access` comes from a live probe, never from memory
  * `verified` is stamped with today's date

Python 3 stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys

from common import C, load_sources, save_sources
from probe import probe

TODAY = dt.date.today().isoformat()


def build(args) -> dict:
    res = probe(args.url, npm_hint=args.npm)
    entry = {
        "id": args.id,
        "name": args.name,
        "url": args.url.rstrip("/"),
        "kind": args.kind,
        "why": args.why,
        "dimension": [d.strip() for d in args.dim.split(",") if d.strip()],
        "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
        "stack": [s.strip() for s in args.stack.split(",") if s.strip()],
        "license": args.license or res.get("license") or "unknown",
        "cost": args.cost,
        "ai_prompt": args.ai_prompt,
        "config_ui": args.config_ui,
        "access": res["access"],
        "verified": TODAY,
    }
    if res["caveats"]:
        entry["caveat"] = " ".join(res["caveats"])
    if args.caveat:
        entry["caveat"] = (entry.get("caveat", "") + " " + args.caveat).strip()
    return entry


def cmd_add(args) -> int:
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.id):
        print(f"{C['r']}id must be kebab-case: {args.id}{C['x']}", file=sys.stderr)
        return 1
    if len(args.why.split()) < 6:
        print(f"{C['r']}--why must be a real sentence (>=6 words). "
              f"It is the field future agents read to pick a source.{C['x']}", file=sys.stderr)
        return 1

    data = load_sources()
    if any(s["id"] == args.id for s in data["sources"]):
        print(f"{C['r']}id '{args.id}' already exists. "
              f"Edit it in data/sources.json or pick another id.{C['x']}", file=sys.stderr)
        return 1

    print(f"{C['dim']}probing {args.url} ...{C['x']}", file=sys.stderr)
    entry = build(args)

    if not entry["access"]:
        print(f"{C['y']}probe found no automatable access method. "
              f"Adding with manual access.{C['x']}", file=sys.stderr)
        entry["access"] = [{"method": "manual", "cmd": "",
                            "note": "No machine path found; the user must copy by hand."}]

    import json
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    if args.dry_run:
        print(f"\n{C['y']}--dry-run: nothing written{C['x']}", file=sys.stderr)
        return 0

    data["sources"].append(entry)
    data["updated"] = TODAY
    save_sources(data)
    print(f"\n{C['g']}added '{args.id}' ({len(data['sources'])} sources total){C['x']}",
          file=sys.stderr)
    print(f"{C['dim']}next: mention it in SKILL.md's routing table if it is a "
          f"first-choice source for some need.{C['x']}", file=sys.stderr)
    return 0


def cmd_reverify(args) -> int:
    data = load_sources()
    changed = 0
    for s in data["sources"]:
        print(f"{C['dim']}probing {s['id']} ...{C['x']}", file=sys.stderr)
        res = probe(s["url"])
        old = {a["method"] for a in s.get("access", [])}
        new = {a["method"] for a in res["access"]}
        gone, added = old - new, new - old
        if gone or added:
            changed += 1
            print(f"{C['y']}{s['id']}{C['x']}")
            if gone:
                print(f"    {C['r']}- {', '.join(sorted(gone))}{C['x']} "
                      f"{C['dim']}(probe could not confirm; verify by hand before deleting){C['x']}")
            if added:
                print(f"    {C['g']}+ {', '.join(sorted(added))}{C['x']}")
        else:
            print(f"{C['g']}{s['id']}{C['x']} unchanged")
            if not args.dry_run:
                s["verified"] = TODAY
    if not args.dry_run:
        data["updated"] = TODAY
        save_sources(data)
    print(f"\n{changed} source(s) drifted. "
          f"{'nothing written (--dry-run)' if args.dry_run else 'dates bumped for unchanged ones'}",
          file=sys.stderr)
    print(f"{C['dim']}A probe miss is not proof a method is dead — sites rate-limit. "
          f"Re-run the single command before removing anything.{C['x']}", file=sys.stderr)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reverify", action="store_true", help="re-probe every existing source")
    p.add_argument("--url"); p.add_argument("--id"); p.add_argument("--name")
    p.add_argument("--why", default="")
    p.add_argument("--tags", default="")
    p.add_argument("--dim", default="2d")
    p.add_argument("--stack", default="react,next")
    p.add_argument("--kind", default="gallery",
                   choices=["gallery", "registry", "meta-index", "repo", "tool", "awesome-list"])
    p.add_argument("--license"); p.add_argument("--cost", default="free")
    p.add_argument("--caveat")
    p.add_argument("--npm", metavar="PKG",
                   help="npm package for this source; probe verifies it exists")
    p.add_argument("--ai-prompt", action="store_true")
    p.add_argument("--config-ui", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.reverify:
        return cmd_reverify(args)
    missing = [f for f in ("url", "id", "name") if not getattr(args, f)]
    if missing or not args.why:
        p.error("need --url --id --name --why (or --reverify). missing: "
                + ", ".join(missing + ([] if args.why else ["why"])))
    return cmd_add(args)


if __name__ == "__main__":
    sys.exit(main())
