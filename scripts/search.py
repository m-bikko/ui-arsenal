#!/usr/bin/env python3
"""Search the ui-arsenal source registry.

    search.py "liquid glass"              # keyword search over curated sources
    search.py "shader" --dim 3d           # filter by dimension (2d|3d)
    search.py --tag orb --tag webgl       # filter by tag (repeatable, AND)
    search.py --method llms-full          # only sources reachable that way
    search.py --show voiceorbs            # full record incl. every access method
    search.py --list                      # one line per curated source
    search.py "shader" --live             # ALSO search the 354+ live shadcn registries
    search.py --live-only "kanban"        # search only the live index
    search.py --tags                      # print the tag vocabulary

Python 3 stdlib only.
"""

from __future__ import annotations

import argparse
import math
import re
import sys

from common import C, load_sources, shadcn_registries


def haystack(src: dict) -> str:
    parts = [
        src.get("id", ""), src.get("name", ""), src.get("why", ""),
        src.get("kind", ""), src.get("caveat", ""), src.get("note_for_agent", ""),
        " ".join(src.get("tags", [])), " ".join(src.get("stack", [])),
        " ".join(src.get("dimension", [])),
        " ".join(a.get("method", "") for a in src.get("access", [])),
    ]
    return " ".join(parts).lower()


def idf(terms: list[str], sources: list[dict]) -> dict[str, float]:
    """Down-weight terms that appear almost everywhere.

    Without this, "react aria" ranks every React source above the one actually
    about React Aria: `react` sits in 80% of entries' `stack` and drowns out the
    term that carries the meaning.
    """
    n = max(len(sources), 1)
    weights = {}
    for t in terms:
        df = sum(1 for s in sources if t in haystack(s))
        weights[t] = math.log((n + 1) / (df + 1)) + 0.25
    return weights


def matches(term: str, field: str) -> int:
    """2 = whole word, 1 = prefix or substring, 0 = no match.

    The prefix rule makes "accessibility" find the tag `accessible` and
    "animations" find `animation`, without pulling in a stemmer.
    """
    if re.search(rf"\b{re.escape(term)}\b", field):
        return 2
    if term in field:
        return 1
    if len(term) >= 5:
        stem = term[:5]
        if re.search(rf"\b{re.escape(stem)}", field):
            return 1
    return 0


def score(src: dict, terms: list[str], w: dict[str, float]) -> float:
    hay = haystack(src)
    name = (src.get("id", "") + " " + src.get("name", "")).lower()
    tags = " ".join(src.get("tags", [])).lower()
    total = 0.0
    hits = 0
    for t in terms:
        if not t:
            continue
        sub = 0
        sub += 10 * matches(t, name) // 2
        sub += 6 * matches(t, tags) // 2
        sub += 2 * matches(t, hay) // 2
        if sub:
            hits += 1
        total += sub * w.get(t, 1.0)
    # A source matching two distinct query terms beats one matching a single
    # common term many times over.
    real = [t for t in terms if t]
    if len(real) > 1:
        total *= 1 + 0.6 * (hits - 1)
    return total


def fmt_line(src: dict) -> str:
    dims = "/".join(src.get("dimension", []))
    methods = ",".join(dict.fromkeys(a["method"] for a in src.get("access", [])))
    flags = []
    if src.get("ai_prompt"):
        flags.append("ai-prompt")
    if src.get("config_ui"):
        flags.append("configurator")
    flag = f" {C['y']}[{' '.join(flags)}]{C['x']}" if flags else ""
    return (f"{C['b']}{src['id']:<22}{C['x']} {C['dim']}{dims:<5}{C['x']} "
            f"{src['url']}\n    {C['c']}{methods}{C['x']}{flag}\n    {src.get('why','')[:150]}")


def show(src: dict) -> None:
    print(f"{C['b']}{src['name']}{C['x']}  ({src['id']})")
    print(f"  url        {src['url']}")
    print(f"  kind       {src.get('kind')}   dimension: {'/'.join(src.get('dimension', []))}")
    print(f"  tags       {', '.join(src.get('tags', []))}")
    print(f"  stack      {', '.join(src.get('stack', []))}")
    print(f"  license    {src.get('license')}   cost: {src.get('cost')}")
    print(f"  ai prompt  {src.get('ai_prompt')}   live configurator: {src.get('config_ui')}")
    print(f"  verified   {src.get('verified')}")
    print(f"\n  {C['b']}Why{C['x']}\n    {src.get('why','')}")
    if src.get("caveat"):
        print(f"\n  {C['r']}Caveat{C['x']}\n    {src['caveat']}")
    if src.get("note_for_agent"):
        print(f"\n  {C['y']}Note for agent{C['x']}\n    {src['note_for_agent']}")
    print(f"\n  {C['b']}Access methods{C['x']} (first is preferred)")
    for i, a in enumerate(src.get("access", []), 1):
        print(f"    {i}. {C['c']}{a['method']}{C['x']}")
        if a.get("cmd"):
            print(f"       $ {a['cmd']}")
        if a.get("note"):
            print(f"       {C['dim']}{a['note']}{C['x']}")


def search_live(terms: list[str], limit: int) -> None:
    regs = shadcn_registries()
    if not regs:
        print(f"{C['r']}live index unavailable (offline?){C['x']}", file=sys.stderr)
        return
    hits = []
    for r in regs:
        hay = f"{r.get('name','')} {r.get('description','')} {r.get('homepage','')}".lower()
        s = sum(4 if t in (r.get("name") or "").lower() else (1 if t in hay else 0) for t in terms)
        if s:
            health = (r.get("health") or {}).get("score") or 0
            hits.append((s, health, r))
    hits.sort(key=lambda x: (-x[0], -x[1]))
    print(f"\n{C['b']}live shadcn registry directory{C['x']} "
          f"{C['dim']}({len(regs)} registries, {len(hits)} matches){C['x']}")
    for _, health, r in hits[:limit]:
        st = (r.get("health") or {}).get("status", "?")
        mark = C["g"] if st == "healthy" else C["y"]
        print(f"  {mark}{health:5.1f}{C['x']} {r['name']:<24} {r['homepage']}")
        print(f"        {C['dim']}{(r.get('description') or '')[:130]}{C['x']}")
        print(f"        $ npx shadcn@latest add {r['name']}/<item>   "
              f"{C['dim']}| index: {r['url'].replace('{name}', 'registry')}{C['x']}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("query", nargs="*", help="free-text terms")
    p.add_argument("--tag", action="append", default=[], help="require this tag (repeatable)")
    p.add_argument("--dim", choices=["2d", "3d"], help="require this dimension")
    p.add_argument("--stack", help="require this stack (react, vue, vanilla, ...)")
    p.add_argument("--method", help="require this access method (llms-full, shadcn-registry, ...)")
    p.add_argument("--ai-prompt", action="store_true", help="only sources that publish AI prompts")
    p.add_argument("--config-ui", action="store_true", help="only sources with a live configurator")
    p.add_argument("--show", metavar="ID", help="print one source in full")
    p.add_argument("--list", action="store_true", help="list every curated source")
    p.add_argument("--tags", action="store_true", help="print the tag vocabulary")
    p.add_argument("--live", action="store_true", help="also search the live shadcn directory")
    p.add_argument("--live-only", action="store_true", help="search only the live directory")
    p.add_argument("-n", type=int, default=12, help="max results (default 12)")
    args = p.parse_args()

    data = load_sources()
    sources = data["sources"]
    terms = [t.lower() for t in " ".join(args.query).split()]

    if args.tags:
        vocab: dict[str, int] = {}
        for s in sources:
            for t in s.get("tags", []):
                vocab[t] = vocab.get(t, 0) + 1
        for t, n in sorted(vocab.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {n:3}  {t}")
        return 0

    if args.show:
        for s in sources:
            if s["id"] == args.show:
                show(s)
                return 0
        print(f"no source with id '{args.show}'. try --list", file=sys.stderr)
        return 1

    if args.live_only:
        search_live(terms or [""], args.n)
        return 0

    pool = sources
    if args.tag:
        pool = [s for s in pool if all(t in s.get("tags", []) for t in args.tag)]
    if args.dim:
        pool = [s for s in pool if args.dim in s.get("dimension", [])]
    if args.stack:
        pool = [s for s in pool if args.stack in s.get("stack", [])]
    if args.method:
        pool = [s for s in pool if any(a["method"] == args.method for a in s.get("access", []))]
    if args.ai_prompt:
        pool = [s for s in pool if s.get("ai_prompt")]
    if args.config_ui:
        pool = [s for s in pool if s.get("config_ui")]

    if args.list or not terms:
        ranked = pool
    else:
        w = idf(terms, data["sources"])
        scored = [(score(s, terms, w), s) for s in pool]
        ranked = [s for sc, s in sorted(scored, key=lambda x: -x[0]) if sc > 0]
        if not ranked:
            print(f"{C['y']}no curated source matched. "
                  f"Falling back to the live directory.{C['x']}", file=sys.stderr)
            search_live(terms, args.n)
            return 0

    shown = min(len(ranked), args.n)
    more = f", showing {shown}" if shown < len(ranked) else ""
    print(f"{C['dim']}curated sources: {len(ranked)} matched{more} "
          f"(registry updated {data['updated']}){C['x']}\n")
    for s in ranked[: args.n]:
        print(fmt_line(s))
        print()

    if args.live:
        search_live(terms or [""], args.n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
