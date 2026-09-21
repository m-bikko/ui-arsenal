#!/usr/bin/env python3
"""Pull machine-readable content out of a source without a browser.

    fetch.py llms voiceorbs                 # llms-full.txt, else llms.txt
    fetch.py llms https://magicui.design    # works on a bare URL too
    fetch.py index react-bits               # list every item in the registry
    fetch.py index react-bits --grep blob   # filter the item list
    fetch.py item react-bits Threads-TS-TW  # ONE item: deps + full file contents
    fetch.py item https://ui-layouts.com/r scroll-animation
    fetch.py md 'https://21st.dev/@author/components/slug'   # 21st .md twin

`index` and `item` speak the shadcn registry protocol, which every one of the
354+ registries implements: <base>/registry.json lists items, <base>/<item>.json
returns the item with each file's full source inlined. That means you can read
real, current source code without installing anything.

Python 3 stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys

from common import C, get_json, http_get, load_sources, origin, registry_base, shadcn_registries


def resolve_base(token: str) -> str | None:
    """Turn 'react-bits' / '@react-bits' / a URL into a registry base URL."""
    if token.startswith("http"):
        return token.rstrip("/")
    name = token if token.startswith("@") else "@" + token
    for r in shadcn_registries():
        if r["name"] == name:
            return registry_base(r["url"])
    for s in load_sources()["sources"]:
        if s["id"] == token.lstrip("@"):
            for a in s.get("access", []):
                if a["method"] in ("registry-json", "shadcn-registry") and "curl" in (a.get("cmd") or ""):
                    url = a["cmd"].split()[-1]
                    if url.startswith("http"):
                        return url.rsplit("/", 1)[0]
    return None


def resolve_site(token: str) -> str | None:
    if token.startswith("http"):
        return origin(token)
    for s in load_sources()["sources"]:
        if s["id"] == token:
            return origin(s["url"])
    for r in shadcn_registries():
        if r["name"].lstrip("@") == token.lstrip("@"):
            return origin(r["homepage"])
    return None


def cmd_llms(args) -> int:
    site = resolve_site(args.target)
    if not site:
        print(f"cannot resolve '{args.target}' to a site", file=sys.stderr)
        return 1
    for path in (["/llms.txt"] if args.short else ["/llms-full.txt", "/llms.txt"]):
        status, body = http_get(site + path, timeout=60)
        if status == 200 and body:
            sys.stderr.write(f"{C['g']}200 {site}{path} ({len(body)} bytes){C['x']}\n")
            sys.stdout.write(body.decode("utf-8", "replace"))
            return 0
        sys.stderr.write(f"{C['dim']}{status} {site}{path}{C['x']}\n")
    sys.stderr.write(f"{C['y']}No llms.txt. Try: fetch.py index {args.target}, "
                     f"or the git-clone / browse method from `search.py --show`.{C['x']}\n")
    return 1


def cmd_index(args) -> int:
    base = resolve_base(args.target)
    if not base:
        print(f"cannot resolve '{args.target}' to a registry base", file=sys.stderr)
        return 1
    data = None
    for path in ("/registry.json", "/index.json"):
        data = get_json(base + path, timeout=60)
        if data:
            sys.stderr.write(f"{C['g']}{base}{path}{C['x']}\n")
            break
    if not data:
        sys.stderr.write(f"{C['y']}no registry index at {base}. "
                         f"Check `search.py --show {args.target}` for another method.{C['x']}\n")
        return 1
    items = data.get("items", data if isinstance(data, list) else [])
    rows = []
    for it in items:
        name = it.get("name", "?")
        if args.grep and args.grep.lower() not in json.dumps(it).lower():
            continue
        deps = ",".join(it.get("dependencies", []) or [])
        rows.append((name, it.get("type", "").replace("registry:", ""), deps,
                     (it.get("description") or "")[:70]))
    sys.stderr.write(f"{C['dim']}{len(rows)} of {len(items)} items{C['x']}\n")
    for name, typ, deps, desc in rows[: args.n]:
        print(f"{C['b']}{name:<34}{C['x']} {typ:<10} {C['dim']}{deps[:34]:<34}{C['x']} {desc}")
    if len(rows) > args.n:
        sys.stderr.write(f"{C['dim']}... {len(rows) - args.n} more (raise -n or use --grep){C['x']}\n")
    return 0


def cmd_item(args) -> int:
    base = resolve_base(args.target)
    if not base:
        print(f"cannot resolve '{args.target}'", file=sys.stderr)
        return 1
    data = get_json(f"{base}/{args.item}.json", timeout=60)
    if not data:
        sys.stderr.write(f"{C['r']}not found: {base}/{args.item}.json{C['x']}\n"
                         f"{C['dim']}list valid names with: fetch.py index {args.target}{C['x']}\n")
        return 1
    if args.raw:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    print(f"{C['b']}{data.get('name')}{C['x']}  type={data.get('type')}")
    if data.get("description"):
        print(f"  {data['description']}")
    deps = data.get("dependencies") or []
    dev = data.get("devDependencies") or []
    reg = data.get("registryDependencies") or []
    if deps:
        print(f"\n  {C['y']}npm deps{C['x']}        {' '.join(deps)}")
    if dev:
        print(f"  {C['y']}npm devDeps{C['x']}     {' '.join(dev)}")
    if reg:
        print(f"  {C['y']}registry deps{C['x']}   {' '.join(reg)}")
    print(f"\n  {C['b']}install{C['x']}  npx shadcn@latest add "
          f"{args.target if args.target.startswith('@') else '@' + args.target}/{args.item}")
    for f in data.get("files", []):
        print(f"\n{C['c']}{'=' * 72}{C['x']}\n{C['c']}FILE: {f.get('path')}{C['x']} "
              f"{C['dim']}({f.get('type','')}){C['x']}\n{C['c']}{'=' * 72}{C['x']}")
        print(f.get("content", "<no inline content>"))
    return 0


def cmd_md(args) -> int:
    url = args.target.split("?")[0].rstrip("/")
    if not url.endswith(".md"):
        url += ".md"
    status, body = http_get(url, timeout=45)
    if status != 200:
        sys.stderr.write(f"{C['r']}{status} {url}{C['x']}\n"
                         f"{C['dim']}The .md twin trick is 21st.dev-specific.{C['x']}\n")
        return 1
    sys.stdout.write(body.decode("utf-8", "replace"))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("llms", help="dump llms-full.txt (fallback llms.txt)")
    a.add_argument("target"); a.add_argument("--short", action="store_true")
    a.set_defaults(fn=cmd_llms)

    b = sub.add_parser("index", help="list items in a shadcn registry")
    b.add_argument("target"); b.add_argument("--grep"); b.add_argument("-n", type=int, default=60)
    b.set_defaults(fn=cmd_index)

    c = sub.add_parser("item", help="print one registry item with full source")
    c.add_argument("target"); c.add_argument("item"); c.add_argument("--raw", action="store_true")
    c.set_defaults(fn=cmd_item)

    d = sub.add_parser("md", help="fetch a 21st.dev markdown twin")
    d.add_argument("target"); d.set_defaults(fn=cmd_md)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
