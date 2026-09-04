"""Render the site from measurement records.

Design constraints, all of which come from measured facts about how AI
assistants select sources (see docs/00-thesis.md):

* Assistants cite *passages*, not pages. Every `Finding` renders as its own
  addressable block with a date and a source link, so it can be lifted whole.
* 68% of AI-cited sources do not rank in Google's top 10. Domain authority is
  not the game; specificity and attributability are.
* The FTC Consumer Review Rule requires that experience claims be real. Every
  number on every page shows where it came from and whether it has been
  verified on an account. The disclosure is on every page, not a footer link.

No templating dependency. HTML is assembled from small functions so the
structure stays inspectable.
"""
from __future__ import annotations

import html
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import yaml

from schema import SEAT_POINTS, Finding, Tool, seat_points_for
from snapshot import HISTORY

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "tools"
SITE = ROOT / "site"

SITE_NAME = "StackProof"
COLUMN_LABEL = {"payroll": "number of people paid", "email_marketing": "contacts on the list", "esignature": "users who send documents", "business_phone": "users with a seat", "project_management": "paid seats", "live_chat": "agent seats", "scheduling": "people or calendars who take bookings", "password_manager": "users with a vault", "website_builder": "sites published", "forms": "users who build forms", "time_tracking": "people who track time", "social_scheduling": "users who post or schedule", "recruiting": "employees at the company", "wiki": "members who edit", "productivity_suite": "users with a mailbox", "video_conferencing": "licensed hosts", "cloud_storage": "users with a seat", "identity_sso": "employees who need an account", "expense_management": "employees who submit expenses", "business_vpn": "employees who need remote access", "webinar_platforms": "attendees per session", "uptime_monitoring": "team members with monitoring/alerting access", "whiteboarding": "people who create or edit boards", "shift_scheduling": "employees on the schedule", "performance_management": "employees in the review/engagement program", "learning_management": "employees who take courses", "field_service_management": "technicians who use the app", "property_management": "rental units managed", "legal_practice_management": "users (attorneys and staff) with a seat", "digital_signage": "screens/displays managed", "fleet_management": "vehicles tracked", "gym_management": "active members managed", "salon_management": "staff seats", "construction_management": "users", "landscaping_management": "team members", "cleaning_management": "cleaners", "vacation_rental_management": "properties managed", "photography_studio_management": "users", "interior_design_management": "users", "wedding_event_planning": "users", "auto_repair_shop_management": "users", "martial_arts_dance_studio_management": "students"}
TAGLINE = "Business software, actually bought and measured."
# Production origin for canonical URLs, sitemap, and JSON-LD. Set SITE_ORIGIN
# in the build environment (Workers Builds → variables); empty keeps local
# builds relative and honest.
import os as _os
ORIGIN = _os.environ.get("SITE_ORIGIN", "").rstrip("/")

DISCLOSURE = (
    "Disclosure: StackProof may earn a commission if you buy through links on "
    "this page. Prices and terms are recorded from the source shown next to "
    "each figure, on the date shown. Research is AI-assisted; every published "
    "number is traceable to a fetched source or a real account, and figures "
    "not yet verified on an account are labelled as such."
)


def e(s: object) -> str:
    return html.escape(str(s), quote=True)


def money(v: float | None) -> str:
    if v is None:
        return "—"
    return f"${v:,.0f}" if float(v).is_integer() else f"${v:,.2f}"


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_tools() -> list[Tool]:
    tools = []
    for p in sorted(DATA.glob("*.yaml")):
        tools.append(Tool.model_validate(yaml.safe_load(p.read_text())))
    return tools


# --------------------------------------------------------------------------
# fragments
# --------------------------------------------------------------------------

def provenance_tag(p) -> str:
    verified = "verified on account" if p.verified_on_account else "not yet verified on an account"
    method = p.method.replace("_", " ")
    note = f' title="{e(p.note)}"' if p.note else ""
    return (
        f'<span class="prov"{note}>'
        f'<a href="{e(p.source_url)}" rel="nofollow noopener">source</a> · '
        f'<time datetime="{p.fetched_at.isoformat()}">{p.fetched_at.isoformat()}</time> · '
        f'{e(method)} · {verified}</span>'
    )


def finding_block(f: Finding, tool: Tool) -> str:
    return (
        f'<section class="finding" id="{e(f.id)}">'
        f'<p class="claim">{e(f.claim)}</p>'
        f'{provenance_tag(f.provenance)}'
        f'<a class="anchor" href="#{e(f.id)}" aria-label="Link to this finding">#</a>'
        f'</section>'
    )


def cost_table(tool: Tool) -> str:
    if not tool.tiers:
        if tool.pricing_note:
            return f'<p class="muted">{e(tool.pricing_note)}</p>'
        return '<p class="muted">No per-seat price is published; see findings.</p>'
    pts = seat_points_for(tool.category)
    head = "".join(f"<th>{n:,} {e(tool.tiers[0].seat_label)}{'s' if n != 1 else ''}</th>" for n in pts)
    rows = []
    for t in tool.tiers:
        cells = "".join(f'<td class="n">{money(t.cost_at(n))}</td>' for n in pts)
        if t.steps:
            formula = "stepped by " + e(t.seat_label) + " count: " + ", ".join(
                f"{money(st.monthly_usd)} to {st.up_to:,}" for st in sorted(t.steps, key=lambda x: x.up_to))
        else:
            base = money(t.base_monthly_usd)
            seat = money(t.per_seat_monthly_usd)
            formula = f"{base} base + {seat} per {e(t.seat_label)}"
            if t.included_seats:
                formula = f"{base} for up to {t.included_seats} {e(t.seat_label)}s, then {seat} per {e(t.seat_label)}"
            if t.base_monthly_usd is None:
                formula += " — base fee not captured; cost not computed"
        if t.billing == "annual":
            formula += " — per-month rate when prepaid annually"
        elif t.billing == "biennial":
            formula += " — per-month rate when prepaid for two years"
        if t.max_seats is not None:
            formula += f" — sold for teams up to {t.max_seats}; larger teams need another plan"
        if not t.standalone:
            formula += " — add-on, priced on top of a plan"
        if not t.compare:
            formula += " — different product from the category comparison; not ranked against other vendors"
        promo = f'<div class="promo">Promo: {e(t.promo)}</div>' if t.promo else ""
        label = e(t.plan) + ("" if t.standalone else ' <span class="muted">(add-on)</span>')
        rows.append(
            f"<tr><th scope=\"row\">{label}<div class=\"formula\">{formula}</div>{promo}"
            f"{provenance_tag(t.provenance)}</th>{cells}</tr>"
        )
    return (
        '<div class="scroll"><table class="cost">'
        f"<caption>Monthly cost at each team size, computed from the published formula. Add-ons and fees below are extra.</caption>"
        f"<thead><tr><th>Plan</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def fees_list(tool: Tool) -> str:
    if not tool.fees:
        return ""
    items = "".join(
        f"<li><b>{e(f.name)}</b> — {money(f.amount_usd)} {e(f.unit)} {provenance_tag(f.provenance)}</li>"
        for f in tool.fees
    )
    return f"<h2>Fees not in the headline price</h2><ul class=\"fees\">{items}</ul>"


def clauses_list(tool: Tool) -> str:
    if not tool.clauses:
        return ""
    items = []
    for c in tool.clauses:
        q = f'<blockquote>{e(c.quote)}</blockquote>' if c.quote else ""
        items.append(
            f'<li class="clause {e(c.status)}"><span class="topic">{e(c.topic.replace("_", " "))}</span> '
            f'<span class="status">{e(c.status.replace("_", " "))}</span>'
            f'<p>{e(c.finding)}</p>{q}{provenance_tag(c.provenance)}</li>'
        )
    return f"<h2>Terms that matter when you leave</h2><ul class=\"clauses\">{''.join(items)}</ul>"


def support_block(tool: Tool) -> str:
    s = tool.support
    if not s:
        return ""
    measured = (
        f"<li>Measured first response: <b>{s.measured_first_response_minutes} min</b></li>"
        if s.measured_first_response_minutes is not None
        else "<li>First-response time: not yet measured on an account.</li>"
    )
    return (
        "<h2>Support</h2><ul>"
        f"<li>Channels: {e(', '.join(s.channels))}</li>"
        f"<li>Hours: {e(s.hours or 'not stated')}</li>"
        f"{measured}</ul>{provenance_tag(s.provenance)}"
    )


def jsonld_tool(tool: Tool) -> str:
    offers = [
        {
            "@type": "Offer",
            "name": t.plan,
            "priceCurrency": "USD",
            "price": t.cost_at(1),
            "priceSpecification": {
                "@type": "UnitPriceSpecification",
                "price": t.per_seat_monthly_usd,
                "priceCurrency": "USD",
                "unitText": f"per {t.seat_label} per month",
            },
            "validFrom": t.provenance.fetched_at.isoformat(),
            "url": t.provenance.source_url,
        }
        for t in tool.tiers
        if t.cost_at(1) is not None
    ]
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{tool.product}: measured pricing and terms",
        "datePublished": (tool.last_fetched or date.today()).isoformat(),
        "dateModified": (tool.last_fetched or date.today()).isoformat(),
        "author": {"@type": "Organization", "name": SITE_NAME},
        "about": {
            "@type": "Product",
            "name": tool.product,
            "brand": {"@type": "Brand", "name": tool.vendor},
            "category": tool.category,
            "url": tool.url,
            "offers": offers,
        },
    }
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------

CSS = """
:root{--ink:#161a1d;--muted:#6b7280;--rule:#e5e7eb;--accent:#0f5c4a;--warn:#b45309;--bg:#fbfaf7}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:28px 20px 80px}header.top{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--rule);padding-bottom:14px;margin-bottom:28px}
header.top a{color:var(--ink);text-decoration:none;font-weight:700}nav a{margin-left:16px;color:var(--muted);text-decoration:none;font-size:14px}
h1{font-size:34px;line-height:1.15;margin:0 0 6px;letter-spacing:-.01em}h2{font-size:20px;margin:36px 0 10px}.lede{color:var(--muted);margin:0 0 22px}
.disclosure{font-size:13px;color:var(--muted);border:1px solid var(--rule);padding:10px 14px;margin:0 0 26px;background:#fff}
.finding{position:relative;border-left:3px solid var(--accent);background:#fff;padding:14px 18px 10px;margin:0 0 14px}.finding .claim{margin:0 0 6px;font-size:17px;padding-right:26px}
.finding .anchor{position:absolute;right:10px;top:8px;color:var(--muted);text-decoration:none}
.prov{display:block;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;color:var(--muted);margin-top:4px}.prov a{color:var(--accent)}
.scroll{overflow-x:auto;border:1px solid var(--rule);background:#fff;margin:10px 0 6px}table{border-collapse:collapse;width:100%;min-width:640px}
caption{caption-side:bottom;text-align:left;padding:10px 12px;font-size:13px;color:var(--muted)}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--rule);vertical-align:top}
thead th{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}td.n{text-align:right;font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,Consolas,monospace}
.formula,.promo{font-size:12px;color:var(--muted);font-weight:400}.promo{color:var(--warn)}
ul.fees li,ul.clauses li{background:#fff;border:1px solid var(--rule);padding:10px 14px;margin:0 0 10px;list-style:none}ul.fees,ul.clauses{padding:0}
.clause .topic{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-right:8px}.clause .status{font-size:12px;padding:1px 8px;border-radius:999px;background:var(--rule)}
.clause.not_stated .status{background:#fef3c7;color:var(--warn)}.clause.stated .status{background:#dcfce7;color:var(--accent)}
blockquote{margin:8px 0;padding-left:12px;border-left:2px solid var(--rule);color:var(--muted);font-size:14px}.muted{color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}.card{background:#fff;border:1px solid var(--rule);padding:16px}.card a{color:var(--ink);font-weight:600;text-decoration:none}
.cta{margin:0 0 8px}.cta .go{display:inline-block;background:var(--accent);color:#fff;padding:9px 14px;text-decoration:none;font-weight:600;border-radius:3px}
footer{margin-top:60px;border-top:1px solid var(--rule);padding-top:14px;font-size:13px;color:var(--muted)}
"""


def page(title: str, body: str, path: str, description: str = "", extra_head: str = "") -> str:
    canon = f'<link rel="canonical" href="{e(ORIGIN + path)}">' if ORIGIN else ""
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{e(title)} — {SITE_NAME}</title>"
        f'<meta name="description" content="{e(description)}">{canon}{extra_head}<style>{CSS}</style></head><body><div class="wrap">'
        f'<header class="top"><a href="/">{SITE_NAME}</a><nav><a href="/payroll/">Payroll</a><a href="/accounting/">Accounting</a><a href="/crm/">CRM</a><a href="/helpdesk/">Helpdesk</a><a href="/esignature/">E-signature</a><a href="/business_phone/">Phone</a><a href="/project_management/">Projects</a><a href="/live_chat/">Live chat</a><a href="/scheduling/">Scheduling</a><a href="/password_manager/">Passwords</a><a href="/website_builder/">Websites</a><a href="/forms/">Forms</a><a href="/time_tracking/">Time</a><a href="/social_scheduling/">Social</a><a href="/recruiting/">Recruiting</a><a href="/wiki/">Wikis</a><a href="/productivity_suite/">Email suites</a><a href="/video_conferencing/">Video</a><a href="/cloud_storage/">Storage</a><a href="/identity_sso/">Identity</a><a href="/expense_management/">Expenses</a><a href="/business_vpn/">VPN</a><a href="/webinar_platforms/">Webinars</a><a href="/uptime_monitoring/">Uptime</a><a href="/whiteboarding/">Whiteboards</a><a href="/shift_scheduling/">Shifts</a><a href="/performance_management/">Performance</a><a href="/learning_management/">Training</a><a href="/field_service_management/">Field service</a><a href="/property_management/">Property mgmt</a><a href="/legal_practice_management/">Legal</a><a href="/digital_signage/">Signage</a><a href="/fleet_management/">Fleet</a><a href="/gym_management/">Gyms</a><a href="/salon_management/">Salons</a><a href="/construction_management/">Construction</a><a href="/landscaping_management/">Landscaping</a><a href="/cleaning_management/">Cleaning</a><a href="/vacation_rental_management/">Vacation Rentals</a><a href="/photography_studio_management/">Photo Studios</a><a href="/interior_design_management/">Interior Design</a><a href="/wedding_event_planning/">Weddings</a><a href="/auto_repair_shop_management/">Auto Repair</a><a href="/martial_arts_dance_studio_management/">Martial Arts &amp; Dance</a><a href="/email_marketing/">Email</a><a href="/changes/">Price changes</a><a href="/dataset/">Dataset</a><a href="/methodology/">Methodology</a></nav></header>'
        f'<p class="disclosure">{DISCLOSURE}</p>{body}'
        f"<footer>{SITE_NAME} — {TAGLINE}. Every figure links to its source and shows the date it was recorded.</footer>"
        "</div></body></html>"
    )


def tool_page(tool: Tool) -> str:
    verified = "Some figures verified on a real account." if tool.any_verified_on_account else "Figures recorded from the vendor's published pages; not yet verified on an account."
    findings = "".join(finding_block(f, tool) for f in tool.findings)
    trial = f"<p><b>Free trial:</b> {e(tool.free_trial)}</p>" if tool.free_trial else ""
    cta = (
        f'<p class="cta"><a class="go" href="/go/{e(tool.slug)}/" rel="sponsored nofollow noopener">'
        f"Go to {e(tool.vendor)}'s pricing page →</a> "
        f'<span class="muted">(affiliate link where a program has accepted us; otherwise the vendor\'s page)</span></p>'
    )
    body = (
        f"<h1>{e(tool.product)}: measured pricing and terms</h1>"
        f'<p class="lede">{e(tool.vendor)} · {e(tool.category)} · last recorded {tool.last_fetched} · {verified}</p>'
        f"{cta}<h2>What we found</h2>{findings}"
        f"<h2>What it costs by team size</h2>{cost_table(tool)}{trial}"
        f"{fees_list(tool)}{clauses_list(tool)}{support_block(tool)}"
    )
    desc = tool.findings[0].claim if tool.findings else f"{tool.product} pricing and terms, measured."
    return page(f"{tool.product} pricing, measured", body, f"/tools/{tool.slug}/", desc, jsonld_tool(tool))


def go_page(tool: Tool) -> str:
    """Redirect stub. One place to swap in a tracking URL per vendor.

    Marked noindex; every link into it carries rel="sponsored" per Google's
    affiliate-link guidance, and the disclosure is on the page itself.
    """
    target = tool.url
    if tool.affiliate and tool.affiliate.url and tool.affiliate.status == "accepted":
        target = tool.affiliate.url
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"robots\" content=\"noindex,nofollow\">"
        f"<meta http-equiv=\"refresh\" content=\"0;url={e(target)}\">"
        f"<title>Redirecting to {e(tool.vendor)}</title></head><body>"
        f"<p>Taking you to {e(tool.vendor)}. {e(DISCLOSURE)}</p>"
        f"<p><a href=\"{e(target)}\" rel=\"sponsored nofollow noopener\">Continue to {e(tool.vendor)}</a></p>"
        "</body></html>"
    )


def _load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    snaps = []
    for p in sorted(HISTORY.glob("*.json")):
        snaps.append(json.loads(p.read_text()))
    return snaps


def _tier_key(t: dict) -> str:
    return t["plan"]


def price_changes() -> list[dict]:
    """Diff consecutive snapshots into change events."""
    snaps = _load_history()
    events: list[dict] = []
    for prev, cur in zip(snaps, snaps[1:]):
        for slug, cur_tool in cur["tools"].items():
            prev_tool = prev["tools"].get(slug)
            if prev_tool is None:
                events.append({"date": cur["date"], "slug": slug, "vendor": cur_tool["vendor"],
                               "what": "added to the dataset", "from": None, "to": None})
                continue
            prev_tiers = {_tier_key(t): t for t in prev_tool["tiers"]}
            for t in cur_tool["tiers"]:
                pt = prev_tiers.get(_tier_key(t))
                if pt is None:
                    events.append({"date": cur["date"], "slug": slug, "vendor": cur_tool["vendor"],
                                   "what": f"new plan: {t['plan']}", "from": None, "to": None})
                    continue
                for field, label in (("base_monthly_usd", "base"), ("per_seat_monthly_usd", "per-seat"), ("steps", "steps")):
                    if pt.get(field) != t.get(field):
                        events.append({"date": cur["date"], "slug": slug, "vendor": cur_tool["vendor"],
                                       "what": f"{t['plan']} {label}", "from": pt.get(field), "to": t.get(field)})
            prev_fees = {f["name"]: f for f in prev_tool["fees"]}
            for f in cur_tool["fees"]:
                pf = prev_fees.get(f["name"])
                if pf is None:
                    events.append({"date": cur["date"], "slug": slug, "vendor": cur_tool["vendor"],
                                   "what": f"new fee: {f['name']}", "from": None, "to": f["amount_usd"]})
                elif pf["amount_usd"] != f["amount_usd"]:
                    events.append({"date": cur["date"], "slug": slug, "vendor": cur_tool["vendor"],
                                   "what": f"fee: {f['name']}", "from": pf["amount_usd"], "to": f["amount_usd"]})
    return events


def changes_page() -> str:
    snaps = _load_history()
    events = price_changes()
    since = snaps[0]["date"] if snaps else "—"
    latest = snaps[-1]["date"] if snaps else "—"
    if events:
        rows = "".join(
            f'<tr><td class="n">{e(ev["date"])}</td><td><a href="/tools/{e(ev["slug"])}/">{e(ev["vendor"])}</a></td>'
            f'<td>{e(ev["what"])}</td><td class="n">{money(ev["from"]) if isinstance(ev["from"], (int, float)) else e(ev["from"] or "—")}</td>'
            f'<td class="n">{money(ev["to"]) if isinstance(ev["to"], (int, float)) else e(ev["to"] or "—")}</td></tr>'
            for ev in sorted(events, key=lambda x: x["date"], reverse=True)
        )
        table = (
            '<div class="scroll"><table><caption>Every change between consecutive snapshots. A vendor\'s own page shows only today\'s price; this shows what it used to be.</caption>'
            "<thead><tr><th>Date</th><th>Vendor</th><th>What changed</th><th>From</th><th>To</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div>"
        )
    else:
        table = (
            f'<p class="muted">Tracking since {e(since)}. {len(snaps)} snapshot{"s" if len(snaps) != 1 else ""} recorded; '
            "no price or fee has changed between snapshots yet. Changes appear here as soon as one does.</p>"
        )
    body = (
        "<h1>Price changes over time</h1>"
        f'<p class="lede">Prices are re-recorded from each vendor\'s page and kept as dated snapshots. Latest snapshot {e(latest)}; tracking since {e(since)}.</p>'
        f"{table}"
        '<p>The raw snapshots are in the <a href="/dataset/">dataset download</a>.</p>'
    )
    return page("Price changes", body, "/changes/", "Software price and fee changes over time, from dated snapshots of vendor pages.")


def dataset_files(tools: list[Tool]) -> tuple[str, str]:
    """JSON and CSV of the whole dataset. Machine-readable is the point."""
    rows = []
    for t in tools:
        for ti in t.tiers:
            rows.append({
                "slug": t.slug, "vendor": t.vendor, "product": t.product, "category": t.category,
                "plan": ti.plan, "base_monthly_usd": ti.base_monthly_usd, "per_seat_monthly_usd": ti.per_seat_monthly_usd,
                "seat_label": ti.seat_label, "billing": ti.billing, "max_seats": ti.max_seats,
                "standalone": ti.standalone, "compare": ti.compare,
                "fetched_at": ti.provenance.fetched_at.isoformat(), "method": ti.provenance.method,
                "verified_on_account": ti.provenance.verified_on_account, "source_url": ti.provenance.source_url,
            })
    js = json.dumps({"generated": date.today().isoformat(), "tools": [t.model_dump(mode="json") for t in tools]}, indent=1)
    cols = list(rows[0].keys()) if rows else []
    def cell(v):
        s_ = "" if v is None else str(v)
        return '"' + s_.replace('"', '""') + '"' if ("," in s_ or '"' in s_ or "\n" in s_) else s_
    csv = ",".join(cols) + "\n" + "\n".join(",".join(cell(r[c]) for c in cols) for r in rows) + "\n"
    return js, csv


def dataset_page(tools: list[Tool]) -> str:
    n_find = sum(len(t.findings) for t in tools)
    body = (
        "<h1>Dataset</h1>"
        f'<p class="lede">{len(tools)} vendors, {sum(len(t.tiers) for t in tools)} priced plans, {n_find} dated findings. Every row carries its source URL, fetch date, and whether it has been verified on an account.</p>'
        '<ul><li><a href="/dataset/stackproof.json">stackproof.json</a> — full records, including findings, clauses and provenance</li>'
        '<li><a href="/dataset/stackproof.csv">stackproof.csv</a> — one row per priced plan</li></ul>'
        "<h2>Terms of use</h2>"
        "<p>Use it. Cite the page you took it from. The figures are recorded from vendors' own published pages on the date shown; check the date before relying on a number.</p>"
        '<p>Schema and method: <a href="/methodology/">methodology</a>.</p>'
    )
    return page("Dataset", body, "/dataset/", "Download the StackProof software pricing dataset as JSON or CSV.")


def category_page(category: str, tools: list[Tool]) -> str:
    pts = seat_points_for(category)
    mid = pts[len(pts) // 2]
    head = "".join(f"<th>{n:,}</th>" for n in pts)
    rows = []
    for t in sorted(tools, key=lambda x: (x.cheapest_tier_cost_at(mid) or (None, 1e9))[1]):
        cells = []
        for n in pts:
            c = t.cheapest_tier_cost_at(n)
            cells.append(f'<td class="n">{money(c[1]) if c else "—"}</td>')
        plan = t.cheapest_tier_cost_at(mid)
        if plan:
            label = f'<div class="formula">{e(plan[0])}</div>'
        elif t.pricing_note:
            label = f'<div class="formula">{e(t.pricing_note)}</div>'
        elif t.tiers:
            # Tiers exist but the base fee was not captured; the per-seat
            # rate alone must not be shown as a cost. Say what is missing.
            label = '<div class="formula">per-seat rate published; base fee not captured — cost not computed</div>'
        else:
            label = '<div class="formula">no per-seat price published</div>'
        rows.append(
            f'<tr><th scope="row"><a href="/tools/{e(t.slug)}/">{e(t.product)}</a>{label}'
            f'<div class="formula">recorded {t.last_fetched}</div></th>{"".join(cells)}</tr>'
        )
    table = (
        '<div class="scroll"><table class="cost"><caption>Cheapest published plan for each vendor at each team size, before add-ons and fees. '
        "A dash means no cost could be computed from the vendor's page; the row says why.</caption>"
        f"<thead><tr><th>Vendor</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )
    # Cross-vendor findings: every finding from every tool, so the category page
    # is itself a dense, citable surface rather than a list of links.
    findings = "".join(finding_block(f, t) for t in tools for f in t.findings)
    body = (
        f"<h1>{e(category.replace('_', ' ').title())} software: measured pricing side by side</h1>"
        f'<p class="lede">Every number below was recorded from the vendor\'s own page on the date shown. Columns are {e(COLUMN_LABEL.get(category, "team size"))}.</p>'
        f"{table}<h2>Findings across vendors</h2>{findings}"
    )
    label = category.replace("_", " ").title()
    return page(f"{label} software compared", body, f"/{category}/", f"{label} software pricing measured side by side.")


def index_page(tools: list[Tool]) -> str:
    cats = sorted({t.category for t in tools})
    cards = "".join(
        f'<div class="card"><a href="/{e(c)}/">{e(c.replace("_", " ").title())}</a><p class="muted">{sum(1 for t in tools if t.category == c)} vendors measured</p></div>'
        for c in cats
    )
    body = (
        f"<h1>{TAGLINE}</h1>"
        '<p class="lede">Vendor pricing pages are marketing. We record the actual formula, compute what it costs at real team sizes, list the fees that are not in the headline, and read the terms that matter when you leave. Every figure is dated and linked to its source.</p>'
        f'<div class="grid">{cards}</div>'
        '<h2>How to read a StackProof page</h2>'
        '<p>Each finding is one sentence, one number, one date, one source. If a figure has been checked on a real paid account it says so; if it was recorded from the vendor\'s published page and not yet verified, it says that instead. "Not stated" is a result, not a gap: it means the vendor\'s published terms do not address the point.</p>'
    )
    return page(SITE_NAME, body, "/", TAGLINE)


def methodology_page() -> str:
    body = (
        "<h1>Methodology</h1>"
        "<h2>What we record</h2>"
        "<ul><li><b>The pricing formula</b>, not the headline. Base plus per-seat, from the vendor's own page, with the fetch date.</li>"
        "<li><b>Cost at 1, 5, 10, 25 and 50 seats</b>, computed from that formula so the numbers are comparable across vendors.</li>"
        "<li><b>Fees not in the headline</b>: per-state filings, add-ons, minimums.</li>"
        "<li><b>Terms that matter when you leave</b>: cancellation notice, auto-renewal, data export, retention after cancellation, price-change notice. When the published terms do not address a point we publish that as the result.</li>"
        "<li><b>Support</b>: channels and hours as published, and first-response time when measured on an account.</li></ul>"
        "<h2>Provenance labels</h2>"
        "<ul><li><b>live fetch</b> — we fetched the vendor's page ourselves on the date shown.</li>"
        "<li><b>vendor page via search</b> — the vendor's own page as surfaced by a search engine, used when the vendor blocks automated fetches. Labelled until verified on an account.</li>"
        "<li><b>account invoice / account test</b> — measured on a real paid account. These are the figures we stand behind without qualification.</li>"
        "<li><b>not available</b> — the vendor does not publish it.</li></ul>"
        "<h2>What we do not do</h2>"
        "<p>We do not write experience we have not had. Where a figure is not yet verified on an account, the page says so next to the figure. We do not rate or rank vendors; we publish what they charge and what their terms say, and let the numbers sort themselves.</p>"
        "<h2>Commercial relationship</h2>"
        f"<p>{DISCLOSURE}</p>"
    )
    return page("Methodology", body, "/methodology/", "How StackProof records and verifies software pricing and terms.")


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def write(path: str, content: str) -> None:
    out = SITE / path.strip("/") / "index.html" if path != "/" else SITE / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content)


def build() -> list[str]:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    tools = load_tools()
    paths: list[str] = []

    write("/", index_page(tools)); paths.append("/")
    write("/methodology/", methodology_page()); paths.append("/methodology/")
    for cat in sorted({t.category for t in tools}):
        write(f"/{cat}/", category_page(cat, [t for t in tools if t.category == cat])); paths.append(f"/{cat}/")
    for t in tools:
        write(f"/tools/{t.slug}/", tool_page(t)); paths.append(f"/tools/{t.slug}/")
        write(f"/go/{t.slug}/", go_page(t))  # not in sitemap: noindex
    write("/changes/", changes_page()); paths.append("/changes/")
    write("/dataset/", dataset_page(tools)); paths.append("/dataset/")
    js, csv = dataset_files(tools)
    (SITE / "dataset" / "stackproof.json").write_text(js)
    (SITE / "dataset" / "stackproof.csv").write_text(csv)

    urls = "".join(f"<url><loc>{e(ORIGIN + p)}</loc></url>" for p in paths)
    (SITE / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n")
    return paths


if __name__ == "__main__":
    built = build()
    print(f"built {len(built)} pages into {SITE}")
    for p in built:
        print(" ", p)
    sys.exit(0)
