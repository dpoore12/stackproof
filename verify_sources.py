"""Check that every citation still points at the page it claims to.

Run periodically (`python verify_sources.py`). Writes `data/source_check.json`.

Why this and not price re-verification: 278 vendors publish pricing in 278
different shapes, most behind marketing frameworks and a fair number behind
bot protection (Gusto answers an automated fetch with 403). Writing 278 price
parsers would produce a lot of confident wrong numbers. But every record here
rests on a `source_url`, and the promise the whole site makes is that the
number came from that page. A citation pointing at a 404, or silently
redirected to a generic marketing page, quietly voids that promise while the
site keeps rendering the figure as sourced.

That failure is not hypothetical. TokenLedger, this project's sibling, had a
`pricing_url` missing a trailing slash: the host answered **HTTP 200** and
served a completely different document with no prices on it, so every "source"
link under every DeepSeek price led somewhere that did not support the claim.
Nothing detected it, because nothing checked. Status codes alone would not
have caught it either — only comparing the URL we asked for against the URL we
landed on.

So this checks the two things that can be checked honestly across every
vendor at once:

    ok          the page still resolves where we said it does
    redirected  it resolves, but somewhere materially different — the case
                that silently invalidates a citation while looking healthy
    dead        4xx/410: the citation points at nothing
    blocked     403/429: bot protection, not link rot. Expected for some
                vendors and recorded as its own state so it never reads as
                a broken citation or gets "fixed" by editing a good URL.
    error       transport failure after a retry

It never edits records. It reports, so a person can decide whether a moved
page means the price moved too.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "tools"
REPORT = ROOT / "data" / "source_check.json"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT = 25
WORKERS = 12


# --------------------------------------------------------------------------
# collecting citations
# --------------------------------------------------------------------------

# How many times each URL is cited in total, across every record — a single
# vendor page typically backs several tiers, fees and findings at once. Kept
# alongside the slug map so a report can say how much of the dataset rests on
# a URL that moved, not just how many tools mention it.
CITATION_COUNT: dict[str, int] = defaultdict(int)


def citations() -> dict[str, list[str]]:
    """source_url -> the tool slugs that cite it."""
    CITATION_COUNT.clear()
    cited: dict[str, set[str]] = defaultdict(set)
    for path in sorted(DATA.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        slug = raw.get("slug", path.stem)

        def walk(node) -> None:
            if isinstance(node, dict):
                url = node.get("source_url")
                # A record that already says the fetch was impossible is not a
                # broken citation; it is a documented dead end, and re-reporting
                # it every run would bury the citations that did break.
                if url and node.get("method") != "not_available":
                    cited[url].add(slug)
                    CITATION_COUNT[url] += 1
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(raw)
    return {u: sorted(s) for u, s in cited.items()}


# --------------------------------------------------------------------------
# checking one URL
# --------------------------------------------------------------------------

@dataclass
class Check:
    url: str
    status: str
    http_status: int | None = None
    final_url: str | None = None
    cited_by: list[str] = field(default_factory=list)
    detail: str | None = None


def _normalise(u: str) -> tuple[str, str]:
    """(host, path) with the noise that isn't a real difference removed.

    An explicit default port counts as noise: some hosts answer a redirect
    naming `example.com:443`, which is the same origin written differently
    and must not be reported as a moved page.
    """
    p = urllib.parse.urlsplit(u)
    host = p.netloc.lower().removeprefix("www.")
    host = re.sub(r":(443|80)$", "", host)
    path = re.sub(r"/+$", "", p.path.lower()) or "/"
    return host, path


def _materially_different(requested: str, final: str) -> bool:
    """Did we land somewhere that no longer supports the citation?

    A trailing slash, http->https, or a www prefix is not a different page.
    A different host, or a path that changed, is: '/pricing' answering from
    '/' means the pricing page is gone and the citation now points at a
    homepage. Locale prefixes ('/en-us/pricing') are the common false
    positive and are treated as the same page.
    """
    rh, rp = _normalise(requested)
    fh, fp = _normalise(final)
    if rh != fh:
        return True
    if rp == fp:
        return False
    locale = re.compile(r"^/[a-z]{2}(-[a-z]{2})?(?=/)")
    return locale.sub("", rp) != locale.sub("", fp)


def check(url: str, cited_by: list[str], attempt: int = 0) -> Check:
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                      "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
    try:
        with opener.open(req, timeout=TIMEOUT) as r:
            final = r.geturl()
            if _materially_different(url, final):
                return Check(url, "redirected", r.status, final, cited_by,
                             detail=f"resolves to {final}")
            return Check(url, "ok", r.status, final, cited_by)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            return Check(url, "blocked", exc.code, None, cited_by,
                         detail="bot protection; needs a browser session or an account")
        if exc.code >= 500 and attempt == 0:
            return check(url, cited_by, attempt + 1)
        return Check(url, "dead" if exc.code < 500 else "error", exc.code, None, cited_by,
                     detail=f"HTTP {exc.code}")
    except Exception as exc:  # noqa: BLE001 - transport failures vary wildly across 278 hosts
        if attempt == 0:
            return check(url, cited_by, attempt + 1)
        return Check(url, "error", None, None, cited_by, detail=f"{type(exc).__name__}: {exc}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

ORDER = ["dead", "redirected", "error", "blocked", "ok"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, help="check only the first N URLs (for a smoke run)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)

    cited = citations()
    urls = sorted(cited)[: args.limit] if args.limit else sorted(cited)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda u: check(u, cited[u]), urls))

    counts = {s: sum(1 for r in results if r.status == s) for s in ORDER}
    payload = {
        "run_at": date.today().isoformat(),
        "urls_checked": len(results),
        "tools_affected": sum(len(r.cited_by) for r in results),
        "records_resting_on_these_urls": sum(CITATION_COUNT[r.url] for r in results),
        "counts": counts,
        "results": [asdict(r) for r in sorted(results, key=lambda r: (ORDER.index(r.status), r.url))],
    }

    if args.json:
        print(json.dumps(payload, indent=1))
    else:
        for status in ORDER:
            rows = [r for r in results if r.status == status]
            if not rows or status == "ok":
                continue
            print(f"\n{status.upper()} ({len(rows)})")
            for r in sorted(rows, key=lambda r: r.url):
                print(f"  {r.url}")
                print(f"    {r.detail or ''}  · cited by: {', '.join(r.cited_by[:6])}"
                      + (" …" if len(r.cited_by) > 6 else ""))
        print(f"\n{payload['run_at']}: " + ", ".join(f"{counts[s]} {s}" for s in ORDER if counts[s]))

    if not args.no_write and not args.limit:
        REPORT.write_text(json.dumps(payload, indent=1) + "\n")

    # Only link rot is actionable-and-ours. Bot protection is the vendor's
    # choice and already disclosed on the records it affects.
    return 1 if (counts["dead"] or counts["redirected"]) else 0


if __name__ == "__main__":
    sys.exit(main())
