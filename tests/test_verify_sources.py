"""What the citation checker must get right.

The check exists because a citation can rot while looking perfectly healthy:
this project's sibling had a pricing URL that answered HTTP 200 and served a
different document entirely, so every "source" link under a price led
somewhere that did not support it. Status codes alone would not have caught
that — only comparing the URL asked for against the URL landed on.

Which makes the redirect comparison the load-bearing logic, and false
positives its real failure mode: a checker that cries wolf on every trailing
slash gets ignored, and then a genuine move gets ignored with it.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import verify_sources as V  # noqa: E402


def test_cosmetic_differences_are_not_a_moved_page():
    same = [
        ("https://x.com/pricing", "https://x.com/pricing/"),        # trailing slash
        ("http://x.com/pricing", "https://x.com/pricing"),          # scheme upgrade
        ("https://www.x.com/pricing", "https://x.com/pricing"),     # www
        ("https://x.com/pricing", "https://x.com/Pricing"),         # case
        # An explicit default port is the same origin spelled out; innago.com
        # answers exactly this way and was the checker's only false positive.
        ("https://www.innago.com/pricing/", "https://innago.com:443/pricing/"),
        # A locale prefix is the same page, localised.
        ("https://x.com/pricing", "https://x.com/en-us/pricing"),
    ]
    for req, final in same:
        assert not V._materially_different(req, final), f"false positive: {req} -> {final}"


def test_a_different_host_or_path_is_a_moved_page():
    moved = [
        # Real finds. The first two are the same acquirer absorbing two
        # products; a vendor rebrand usually means the price moved too.
        ("https://golmn.com/pricing/", "https://granum.com/lmn/pricing/"),
        ("https://www.zolasuite.com/pricing/", "http://caretlegal.com/pricing/"),
        ("https://www.talentlms.com/pricing", "https://www.talentlms.com/prices"),
        # The failure this whole check exists for: a pricing page answering
        # from the homepage, with a 200 and no error anywhere.
        ("https://x.com/pricing", "https://x.com/"),
    ]
    for req, final in moved:
        assert V._materially_different(req, final), f"missed a move: {req} -> {final}"


def test_documented_dead_ends_are_not_recounted_as_broken_citations():
    """A record already saying the fetch was impossible is not link rot.

    Re-reporting those every run would bury the citations that actually broke.
    """
    cited = V.citations()
    for url, slugs in cited.items():
        assert url and slugs, "a citation was collected with no URL or no citing tool"
    # gusto.com/pricing is recorded with method: not_available (it 403s), so it
    # must not appear as a citation to check; the comparison page it actually
    # cites must.
    assert "https://gusto.com/pricing" not in cited
    assert any("gusto" in s for slugs in cited.values() for s in slugs)


def test_every_checked_url_is_http():
    for url in V.citations():
        assert url.startswith("http"), f"not a fetchable citation: {url}"
