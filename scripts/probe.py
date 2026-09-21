#!/usr/bin/env python3
"""Probe a site and report which access methods actually work.

    probe.py https://newsite.dev
    probe.py https://newsite.dev --json     # emits a ready `access` block

Checks, in the order the skill prefers them:
  llms-full.txt -> llms.txt -> shadcn registry (directory + /registry.json probes)
  -> .md twin -> linked GitHub repo -> headless reachability -> bot-wall detection

Run this before adding any source. add_source.py calls it for you.

Python 3 stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

from common import C, get_json, http_get, origin, registry_base, shadcn_registries

# A 200 that is really a challenge page. These are the interstitials' own wording
# and script hooks — NOT the bare words "cloudflare" or "captcha", which appear in
# plenty of legitimate pages (a "deployed on Cloudflare" footer, a feature list
# mentioning captcha). Matching those produced false browse-headed flags, which is
# worse than missing a wall: it tells future agents not to try a site that works.
BOT_WALL = re.compile(
    rb"just a moment\.\.\.|attention required!\s*\|\s*cloudflare"
    rb"|checking your browser before accessing"
    rb"|enable javascript and cookies to continue"
    rb"|sorry, you have been blocked"
    rb"|cf-browser-verification|cf_chl_opt|__cf_chl_|/cdn-cgi/challenge-platform",
    re.I)

# Challenge pages are small and have no real navigation. A big document that
# happens to match is almost certainly a real page talking about bot walls.
BOT_WALL_MAX_BYTES = 120_000


BROWSE_BIN = pathlib.Path.home() / ".claude/skills/gstack/browse/dist/browse"


def browse_status(url: str, timeout: int = 60) -> int | None:
    """HTTP status gstack's headless Chromium sees. None when browse is absent."""
    if not BROWSE_BIN.is_file() or not os.access(BROWSE_BIN, os.X_OK):
        return None
    try:
        r = subprocess.run([str(BROWSE_BIN), "goto", url],
                           capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    m = re.search(r"\((\d{3})\)\s*$", (r.stdout or "").strip())
    return int(m.group(1)) if m else None


# Hosts shared by thousands of unrelated projects. A URL here identifies a repo or
# a package, NOT a site whose origin belongs to this source. Probing the origin
# would attribute the host's own /llms.txt (github.com really serves one) and any
# registry that happens to list a github.com homepage to whatever we are probing.
CODE_HOSTS = {"github.com", "gitlab.com", "bitbucket.org", "codeberg.org"}
PKG_HOSTS = {"npmjs.com", "www.npmjs.com", "pub.dev", "crates.io", "pypi.org"}


def host_of(url: str) -> str:
    return origin(url).split("//", 1)[-1].lower()


def probe_repo_url(url: str, out: dict, log) -> bool:
    """Resolve a code-host or package-host URL directly. Returns True when handled."""
    host, path = host_of(url), url.split("//", 1)[-1].split("/", 1)
    parts = (path[1] if len(path) > 1 else "").strip("/").split("/")

    if host in CODE_HOSTS and len(parts) >= 2 and parts[0] and parts[1]:
        slug = f"{parts[0]}/{parts[1].removesuffix('.git')}"
        meta = get_json(f"https://api.github.com/repos/{slug}", timeout=20) \
            if host == "github.com" else None
        lic = (meta.get("license") or {}).get("spdx_id") if meta else None
        note = (f"⭐{meta['stargazers_count']}, license {lic or 'none'}, "
                f"last push {(meta.get('pushed_at') or '')[:10]}") if meta else "repo URL"
        log("repo url", 200 if meta else 0, f"{host}/{slug}")
        out["access"].append({"method": "git-clone",
                              "cmd": f"git clone --depth 1 https://{host}/{slug}",
                              "note": note})
        if host == "github.com":
            out["access"].append({
                "method": "gh-api",
                "cmd": f"curl -sSL 'https://api.github.com/repos/{slug}/contents/'",
                "note": "Enumerate files without cloning. `gh api` for 5000 req/h.",
            })
            out.setdefault("github", slug)
            if lic:
                out.setdefault("license", lic)
        return True

    if host in PKG_HOSTS and len(parts) >= 1 and parts[-1]:
        name = parts[-1]
        if host == "pub.dev":
            meta = get_json(f"https://pub.dev/api/packages/{name}", timeout=20)
            ver = ((meta or {}).get("latest") or {}).get("version")
            if ver:
                log("pub.dev", 200, f"{name} {ver}")
                out["access"].append({"method": "npm",
                                      "cmd": f"flutter pub add {name}",
                                      "note": f"Dart/Flutter package, latest {ver}."})
                return True
        else:
            meta = get_json(f"https://registry.npmjs.org/{name}", timeout=20)
            if isinstance(meta, dict) and "versions" in meta:
                ver = (meta.get("dist-tags") or {}).get("latest", "?")
                log("npm", 200, f"{name}@{ver}")
                out["access"].append({"method": "npm", "cmd": f"npm i {name}",
                                      "note": f"Published package, latest {ver}."})
                return True
    return False


def probe(url: str, no_browse: bool = False, npm_hint: str | None = None) -> dict:
    site = origin(url)
    out: dict = {"site": site, "checks": [], "access": [], "caveats": []}

    def log(label: str, status: int, extra: str = "") -> None:
        out["checks"].append({"check": label, "status": status, "note": extra})

    # A repo or package URL is not a site. Resolve it and stop — probing the shared
    # origin would record another project's llms.txt and registry as this one's.
    if host_of(url) in CODE_HOSTS | PKG_HOSTS:
        out["site"] = url
        if probe_repo_url(url, out, log):
            return out
        log("repo url", 0, "could not resolve owner/repo or package name")
        out["access"].append({"method": "manual", "cmd": "",
                              "note": f"Unresolved {host_of(url)} URL — open it by hand."})
        return out

    status, body = http_get(site, timeout=25)
    log("homepage", status)
    challenged = (status == 200
                  and len(body) < BOT_WALL_MAX_BYTES
                  and BOT_WALL.search(body))

    # Some walls are client-specific: urllib with a browser UA sails through while
    # curl and headless Chromium get 403 (uiverse.io does exactly this). The only
    # way to know is to ask the browser we would actually use. Skipped silently
    # when gstack browse is not installed.
    headless_blocked = False
    if not challenged and status == 200 and not no_browse:
        hstatus = browse_status(site)
        if hstatus is not None:
            log("headless browse", hstatus)
            if hstatus in (0, 403, 429, 503):
                headless_blocked = True
                out["headless_status"] = hstatus

    walled = status in (403, 429, 503) or challenged or headless_blocked
    if walled:
        if headless_blocked:
            reason = (f"plain HTTP gets 200 but headless Chromium gets "
                      f"{out['headless_status']} — the wall is client-specific")
        elif challenged:
            reason = "homepage returns 200 but the body is a challenge interstitial"
        else:
            reason = f"homepage returns {status} to plain HTTP"
        out["caveats"].append(
            f"Bot wall: {reason}. Use a GitHub mirror, an npm package, or "
            "`browse --headed`. A 429 can be plain rate limiting — re-check once "
            "before trusting this.")
        out["access"].append({
            "method": "browse-headed",
            "cmd": f"browse --headed goto {site}",
            "note": "Bot-protected: blocks curl and headless. Do not retry `$B goto`.",
        })

    # 1. llms.txt family
    for path, method in (("/llms-full.txt", "llms-full"), ("/llms.txt", "llms-txt")):
        st, b = http_get(site + path, timeout=30)
        log(path, st, f"{len(b)} bytes" if st == 200 else "")
        if st == 200 and b and not BOT_WALL.search(b[:2000]):
            out["access"].append({
                "method": method,
                "cmd": f"curl -sSL {site}{path}",
                "note": ("Full source dump of every component in one file."
                         if method == "llms-full" else "Index + prose contract."),
            })

    # 2. shadcn registry — first the official directory, then common conventions.
    #    Match on exact host, never substring: six registries list a github.com
    #    homepage, and a substring test handed all of them to whichever came first.
    def bare(h: str) -> str:
        return h.lower().removeprefix("www.")

    host = bare(host_of(site))
    for r in shadcn_registries():
        if host and host not in CODE_HOSTS and bare(host_of(r.get("homepage") or "")) == host:
            base = registry_base(r["url"])
            log("shadcn directory", 200, r["name"])
            out["access"].append({
                "method": "shadcn-registry",
                "cmd": f"npx shadcn@latest add {r['name']}/<item>",
                "note": f"Listed in the official shadcn directory; resolves with no config. "
                        f"health={(r.get('health') or {}).get('score', '?')}",
            })
            out["access"].append({
                "method": "registry-json",
                "cmd": f"curl -sSL {base}/registry.json",
                "note": f"Item index. Full source per item: {base}/<item>.json",
            })
            break
    else:
        for base in (f"{site}/r", f"{site}/registry", site):
            d = get_json(f"{base}/registry.json", timeout=25)
            if d:
                n = len(d.get("items", d if isinstance(d, list) else []))
                log("registry.json", 200, f"{base} ({n} items)")
                out["access"].append({
                    "method": "registry-json",
                    "cmd": f"curl -sSL {base}/registry.json",
                    "note": f"{n} items. Full source per item: {base}/<item>.json",
                })
                break

    # 3. .md twin
    if url != site:
        st, b = http_get(url.rstrip("/") + ".md", timeout=20)
        log(".md twin", st)
        if st == 200 and b and b[:1].isascii():
            out["access"].append({
                "method": "md-suffix",
                "cmd": f"curl -sSL '{url.rstrip('/')}.md'",
                "note": "Append .md to page URLs for a markdown twin.",
            })

    # 4. GitHub repo linked from the homepage
    if status == 200 and body:
        repos = re.findall(rb'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', body[:400000])
        seen: list[str] = []
        for raw in repos:
            slug = raw.decode().rstrip(".git")
            if slug.count("/") == 1 and not slug.startswith(("sponsors/", "features/")) \
                    and slug not in seen:
                seen.append(slug)
        for slug in seen[:3]:
            meta = get_json(f"https://api.github.com/repos/{slug}", timeout=20)
            if meta and meta.get("stargazers_count") is not None:
                lic = (meta.get("license") or {}).get("spdx_id") or "none"
                log("github", 200, f"{slug} ⭐{meta['stargazers_count']} {lic}")
                out["access"].append({
                    "method": "git-clone",
                    "cmd": f"git clone --depth 1 https://github.com/{slug}",
                    "note": f"⭐{meta['stargazers_count']}, license {lic}, "
                            f"last push {(meta.get('pushed_at') or '')[:10]}",
                })
                out.setdefault("github", slug)
                out.setdefault("license", lic)
                break

    # 4b. npm package. Some sources are libraries, not snippet galleries, and
    #     installing beats copying source. Candidates come from an install command
    #     printed on the page or from the repo's package.json name — then every
    #     candidate is verified against the npm registry, so this stays a probe
    #     result rather than a hand-written guess.
    if status == 200 and body or npm_hint:
        cands: list[str] = [npm_hint] if npm_hint else []
        for m in re.finditer(rb"npm\s+(?:i|install|add)\s+(-[DS]\s+)?([@a-z0-9][\w.@/-]{1,60})",
                             body[:400000] if body else b'', re.I):
            cands.append(m.group(2).decode())
        if out.get("github"):
            pkg = get_json(
                f"https://raw.githubusercontent.com/{out['github']}/HEAD/package.json", 20)
            if isinstance(pkg, dict) and isinstance(pkg.get("name"), str):
                cands.append(pkg["name"])
        for name in list(dict.fromkeys(cands))[:6]:
            # valid npm names: "pkg", "pkg-name", "@scope/pkg". Anything else is
            # shell noise picked up from a code block.
            if not re.fullmatch(r"(@[a-z0-9._-]+/)?[a-z0-9._-]+", name, re.I):
                continue
            meta = get_json(f"https://registry.npmjs.org/{name.replace('/', '%2F')}", 20)
            if not isinstance(meta, dict) or "versions" not in meta:
                continue
            latest = (meta.get("dist-tags") or {}).get("latest", "?")
            log("npm", 200, f"{name}@{latest}")
            out["access"].append({
                "method": "npm",
                "cmd": f"npm i {name}",
                "note": f"Published package, latest {latest}. "
                        f"Installing beats copying source for a real library.",
            })
            break

    # 5. plain browsing, when nothing better exists. Never offered alongside a
    #    wall — telling an agent to try `$B goto` on a site we just watched block
    #    headless Chromium is exactly the wasted turn the registry exists to prevent.
    if not walled and status == 200 and not out["access"]:
        out["access"].append({
            "method": "browse",
            "cmd": f"$B goto {site}",
            "note": "No machine-readable index found. Render and read the DOM.",
        })
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url")
    p.add_argument("--json", action="store_true", help="emit a pasteable access block")
    p.add_argument("--npm", metavar="PKG",
                   help="npm package to check for this source; verified against "
                        "registry.npmjs.org before it is recorded")
    p.add_argument("--no-browse", action="store_true",
                   help="skip the headless cross-check (faster, misses client-specific walls)")
    args = p.parse_args()

    res = probe(args.url, no_browse=args.no_browse, npm_hint=args.npm)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    print(f"{C['b']}{res['site']}{C['x']}\n")
    print(f"{C['b']}checks{C['x']}")
    for c in res["checks"]:
        ok = c["status"] == 200
        mark = f"{C['g']}ok {C['x']}" if ok else f"{C['r']}{c['status']:<3}{C['x']}"
        print(f"  {mark} {c['check']:<22} {C['dim']}{c['note']}{C['x']}")
    print(f"\n{C['b']}access methods, best first{C['x']}")
    if not res["access"]:
        print(f"  {C['r']}none — manual only{C['x']}")
    for i, a in enumerate(res["access"], 1):
        print(f"  {i}. {C['c']}{a['method']}{C['x']}")
        print(f"     $ {a['cmd']}")
        if a.get("note"):
            print(f"     {C['dim']}{a['note']}{C['x']}")
    for cav in res["caveats"]:
        print(f"\n{C['y']}caveat{C['x']} {cav}")
    print(f"\n{C['dim']}add it: add_source.py --url {res['site']} --id <id> "
          f"--name '<Name>' --tags a,b --why '<one sentence>'{C['x']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
