"""The tests encode the two rules the business depends on.

1. Nothing publishable exists without provenance and a date. If a record can
   be built that violates that, the FTC argument collapses.
2. The site is rendered from data. If a tool is in data/, it is on the site,
   in the category table, and every finding is an addressable block.
"""
import re
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build as B  # noqa: E402
from schema import SEAT_POINTS, Finding, PriceTier, Provenance, Tool  # noqa: E402

DATA = ROOT / "data" / "tools"


def _records():
    return [(p, yaml.safe_load(p.read_text())) for p in sorted(DATA.glob("*.yaml"))]


def test_every_record_validates():
    for p, raw in _records():
        Tool.model_validate(raw)


def test_every_finding_has_url_date_and_number():
    for p, raw in _records():
        t = Tool.model_validate(raw)
        assert t.findings, f"{p.name} has no findings"
        for f in t.findings:
            assert f.provenance.source_url.startswith("http"), f.id
            assert isinstance(f.provenance.fetched_at, date), f.id
            assert re.search(r"\d", f.claim), f.id


def test_finding_without_number_is_rejected():
    prov = Provenance(source_url="https://x.test", fetched_at=date(2026, 9, 3), method="live_fetch")
    with pytest.raises(ValidationError):
        Finding(id="vague", claim="This vendor is quite good.", provenance=prov)


def test_account_methods_force_verified_flag():
    p = Provenance(source_url="https://x.test", fetched_at=date(2026, 9, 3), method="account_invoice")
    assert p.verified_on_account is True


def test_cost_math():
    prov = Provenance(source_url="https://x.test", fetched_at=date(2026, 9, 3), method="live_fetch")
    t = PriceTier(plan="p", base_monthly_usd=49, per_seat_monthly_usd=6, provenance=prov)
    assert t.cost_at(1) == 55
    assert t.cost_at(10) == 109
    empty = PriceTier(plan="q", provenance=prov)
    assert empty.cost_at(10) is None


def test_onpay_ten_worker_figure_matches_published_finding():
    t = Tool.model_validate(yaml.safe_load((DATA / "onpay.yaml").read_text()))
    plan, cost = t.cheapest_tier_cost_at(10)
    assert plan == "Payroll Essentials"
    assert cost == 109
    assert any("$109" in f.claim for f in t.findings)


def test_addons_never_win_cheapest_plan():
    """Regression: an add-on priced on top of a plan is not a plan price.

    OnPay's HR add-on is $15 + $2/worker. Left as a plain tier it would make
    the comparison table show OnPay at $35 for 10 workers instead of $109.
    """
    prov = Provenance(source_url="https://x.test", fetched_at=date(2026, 9, 3), method="live_fetch")
    t = Tool(
        slug="x", vendor="X", product="X", category="payroll", url="https://x.test",
        tiers=[
            PriceTier(plan="Core", base_monthly_usd=49, per_seat_monthly_usd=6, provenance=prov),
            PriceTier(plan="Addon", standalone=False, base_monthly_usd=15, per_seat_monthly_usd=2, provenance=prov),
        ],
        findings=[Finding(id="f1", claim="Costs $109 at 10 seats.", provenance=prov)],
    )
    assert t.cheapest_tier_cost_at(10) == ("Core", 109)


def test_uncaptured_base_never_publishes_a_cost():
    """A null base means unknown, not zero. Patriot's base was not extractable;
    its cost must render as unknown rather than as the per-seat rate alone."""
    t = Tool.model_validate(yaml.safe_load((DATA / "patriot.yaml").read_text()))
    assert t.cheapest_tier_cost_at(10) is None


def test_build_renders_every_tool_and_finding(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "SITE", tmp_path / "site")
    paths = B.build()
    tools = B.load_tools()
    for t in tools:
        assert f"/tools/{t.slug}/" in paths
        html = (tmp_path / "site" / "tools" / t.slug / "index.html").read_text()
        for f in t.findings:
            assert f'id="{f.id}"' in html
            assert f.provenance.fetched_at.isoformat() in html
        assert "Disclosure:" in html
        assert "application/ld+json" in html
    cat = (tmp_path / "site" / "payroll" / "index.html").read_text()
    for t in tools:
        if t.category == "payroll":
            assert t.product in cat
    for n in SEAT_POINTS:
        assert f"<th>{n}</th>" in cat
    assert (tmp_path / "site" / "sitemap.xml").exists()
    assert (tmp_path / "site" / "robots.txt").exists()


def test_unverified_figures_are_labelled(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "SITE", tmp_path / "site")
    B.build()
    html = (tmp_path / "site" / "tools" / "gusto" / "index.html").read_text()
    assert "not yet verified on an account" in html
    assert "vendor page via search" in html
