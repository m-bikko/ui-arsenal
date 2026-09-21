"""Shared helpers for ui-arsenal scripts. Python 3 stdlib only."""

from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SOURCES_PATH = SKILL_DIR / "data" / "sources.json"

# Live index of every shadcn-compatible registry (354+ and growing).
SHADCN_INDEX = "https://ui.shadcn.com/r/registries.json"
CACHE_DIR = pathlib.Path(
    os.environ.get("UI_ARSENAL_CACHE", pathlib.Path.home() / ".cache" / "ui-arsenal")
)


def load_sources() -> dict:
    with SOURCES_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def save_sources(data: dict) -> None:
    tmp = SOURCES_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(SOURCES_PATH)


def http_get(url: str, timeout: int = 25) -> tuple[int, bytes]:
    """GET a URL. Returns (status, body). Never raises on HTTP errors."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() if exc.fp else b""
    except Exception as exc:  # noqa: BLE001 - network failures are data here
        return 0, str(exc).encode()


def http_status(url: str, timeout: int = 15) -> int:
    return http_get(url, timeout)[0]


def get_json(url: str, timeout: int = 30):
    status, body = http_get(url, timeout)
    if status != 200:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def shadcn_registries(max_age_h: int = 24) -> list[dict]:
    """The live shadcn registry directory, cached locally."""
    import time

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "registries.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < max_age_h * 3600:
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    data = get_json(SHADCN_INDEX)
    if data is None:
        if cache.exists():  # stale beats nothing
            return json.loads(cache.read_text(encoding="utf-8"))
        return []
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def registry_base(url_template: str) -> str:
    """'https://x.com/r/{name}.json' -> 'https://x.com/r'."""
    head = url_template.split("{name}")[0]
    return head.rstrip("/").rstrip("/")


def origin(url: str) -> str:
    parts = url.split("/")
    return "/".join(parts[:3]) if len(parts) >= 3 else url.rstrip("/")


C = {
    "b": "\033[1m", "dim": "\033[2m", "g": "\033[32m", "y": "\033[33m",
    "r": "\033[31m", "c": "\033[36m", "x": "\033[0m",
}
if not os.isatty(1) or os.environ.get("NO_COLOR"):
    C = {k: "" for k in C}
