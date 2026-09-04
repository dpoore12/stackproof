"""Measurement schema.

The site is rendered from these records, never from prose. That is not a
style choice — it is what makes every published sentence defensible:

* The FTC's Consumer Review Rule prohibits AI-generated content presented as
  authentic experience. Every number here carries the URL it came from, the
  date it was fetched, and whether it has been verified on a real account.
  A record cannot be constructed without that provenance.
* LLMs cite passages, not pages, and prefer short, dated, numeric,
  attributable statements. A `Finding` is exactly that shape, by type.

Nothing in this file knows about HTML.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Method = Literal[
    "live_fetch",               # we fetched the vendor page ourselves
    "vendor_page_via_search",   # vendor's own page, surfaced via search; direct fetch blocked
    "account_invoice",          # a real invoice on a real account
    "account_test",             # measured on a real account (setup time, export, support)
    "not_available",            # vendor does not publish it
]


class Provenance(BaseModel):
    """Where a number came from. Required on every measurable field."""

    source_url: str
    fetched_at: date
    method: Method
    note: str | None = None
    verified_on_account: bool = False

    @model_validator(mode="after")
    def _account_methods_imply_verified(self) -> "Provenance":
        if self.method in ("account_invoice", "account_test"):
            self.verified_on_account = True
        return self


class Step(BaseModel):
    """One rung of a stepped price list: `monthly_usd` applies up to `up_to` seats."""

    up_to: int
    monthly_usd: float


class PriceTier(BaseModel):
    plan: str
    base_monthly_usd: float | None = None
    per_seat_monthly_usd: float | None = None
    steps: list[Step] | None = Field(
        default=None,
        description="Stepped price list by seat/contact count, as email platforms "
        "price. When set, base/per-seat are ignored and cost_at() reads the "
        "smallest step that covers the requested count; beyond the last step "
        "the cost is unknown, never extrapolated.",
    )
    billing: Literal["monthly", "annual", "biennial"] = Field(
        default="monthly",
        description="Which price is recorded: the month-to-month rate or the "
        "per-month rate when prepaid annually, or biennial for a two-year "
        "prepay. Vendors headline the discounted one; it must be labelled.",
    )
    seat_label: str = "worker"
    promo: str | None = Field(default=None, description="Promotional terms, verbatim from source.")
    included_seats: int = Field(
        default=0,
        description="Seats covered by the base price. Per-seat pricing applies "
        "only beyond this (accounting: 'per organization, 3 users included, "
        "$3 per additional user').",
    )
    max_seats: int | None = Field(
        default=None,
        description="Largest team this tier is sold for. Beyond it the cost is "
        "unknown here (another plan is required), never extrapolated — a free "
        "plan capped at 10 employees must not price a 50-person team.",
    )
    compare: bool = Field(
        default=True,
        description="False for a plan that prices a different thing than the "
        "category compares — contractor-only payroll next to employee payroll. "
        "Still shown on the vendor's page; never ranked in the category table.",
    )
    standalone: bool = Field(
        default=True,
        description="False for add-ons priced on top of another plan. Add-ons are "
        "shown in the cost table but never compete for 'cheapest plan' — an "
        "add-on's $35 is not a payroll price.",
    )
    provenance: Provenance

    def cost_at(self, seats: int) -> float | None:
        """Monthly cost at `seats`.

        `None` base means *not captured*, and the cost is unknown — it is
        never computed from the per-seat rate alone, because that would
        publish an understated number. A vendor with genuinely no base fee
        records `base_monthly_usd: 0`.
        """
        if self.max_seats is not None and seats > self.max_seats:
            return None
        if self.steps:
            for st in sorted(self.steps, key=lambda x: x.up_to):
                if seats <= st.up_to:
                    return st.monthly_usd
            return None
        if self.base_monthly_usd is None:
            return None
        extra = max(0, seats - self.included_seats)
        return self.base_monthly_usd + (self.per_seat_monthly_usd or 0.0) * extra


class Fee(BaseModel):
    """An extra charge that is not in the headline price."""

    name: str
    amount_usd: float
    unit: str
    provenance: Provenance


ClauseTopic = Literal[
    "cancellation",
    "auto_renew",
    "data_export",
    "data_retention",
    "price_change",
    "refund",
    "billing_timing",
    "accuracy_guarantee",
]


class Clause(BaseModel):
    """A contract or policy term, and whether the vendor actually states it.

    `not_stated` is a real and publishable result: "the vendor's published
    terms do not specify X" is exactly the kind of thing a buyer needs and
    nobody else checks.
    """

    topic: ClauseTopic
    status: Literal["stated", "not_stated", "needs_account"]
    finding: str = Field(description="One self-contained sentence.")
    quote: str | None = None
    provenance: Provenance


class Support(BaseModel):
    channels: list[str]
    hours: str | None = None
    measured_first_response_minutes: int | None = None
    provenance: Provenance


class Affiliate(BaseModel):
    program: str
    url: str | None = None
    commission: str | None = None
    cookie_days: int | None = None
    recurring_months: int | None = None
    status: Literal["not_applied", "applied", "accepted", "rejected"] = "not_applied"


class Finding(BaseModel):
    """A single citable passage.

    Shape rules, enforced below: one sentence-ish, contains a number or a
    date, and carries provenance. This is the unit an LLM lifts.
    """

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    claim: str
    provenance: Provenance

    @model_validator(mode="after")
    def _must_be_specific(self) -> "Finding":
        has_number = any(ch.isdigit() for ch in self.claim)
        if not has_number:
            raise ValueError(f"finding {self.id!r} carries no number or date; it is not citable")
        if len(self.claim) > 320:
            raise ValueError(f"finding {self.id!r} is too long to be lifted as a passage")
        return self


class Tool(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    vendor: str
    product: str
    category: str
    url: str
    tiers: list[PriceTier] = []
    fees: list[Fee] = []
    clauses: list[Clause] = []
    support: Support | None = None
    free_trial: str | None = None
    pricing_note: str | None = Field(
        default=None,
        description="Shown in place of a computed cost when no tier can be "
        "priced — e.g. the vendor publishes prices behind a script the fetch "
        "could not read. Distinguishes 'not captured' from 'not published'.",
    )
    affiliate: Affiliate | None = None
    findings: list[Finding] = []

    @property
    def last_fetched(self) -> date | None:
        dates = [t.provenance.fetched_at for t in self.tiers]
        dates += [f.provenance.fetched_at for f in self.fees]
        dates += [c.provenance.fetched_at for c in self.clauses]
        dates += [f.provenance.fetched_at for f in self.findings]
        if self.support:
            dates.append(self.support.provenance.fetched_at)
        return max(dates) if dates else None

    @property
    def any_verified_on_account(self) -> bool:
        provs = [t.provenance for t in self.tiers] + [f.provenance for f in self.findings]
        return any(p.verified_on_account for p in provs)

    def cheapest_tier_cost_at(self, seats: int) -> tuple[str, float] | None:
        costs = [(t.plan, t.cost_at(seats)) for t in self.tiers if t.standalone and t.compare]
        costs = [(p, c) for p, c in costs if c is not None]
        return min(costs, key=lambda pc: pc[1]) if costs else None


SEAT_POINTS = (1, 5, 10, 25, 50)

# Team sizes worth comparing differ by category: payroll is priced per worker,
# email marketing per contact on the list.
CATEGORY_SEAT_POINTS: dict[str, tuple[int, ...]] = {
    "payroll": (1, 5, 10, 25, 50),
    "email_marketing": (500, 1000, 2500, 5000, 10000, 25000),
    "accounting": (1, 3, 5, 10, 25),
    "crm": (1, 3, 5, 10, 25),
    "helpdesk": (1, 3, 5, 10, 25),
    "esignature": (1, 3, 5, 10, 25),
    "business_phone": (1, 3, 5, 10, 25),
    "project_management": (1, 3, 5, 10, 25),
    "live_chat": (1, 3, 5, 10, 25),
    "scheduling": (1, 3, 5, 10, 25),
    "password_manager": (1, 3, 5, 10, 25),
    "website_builder": (1, 2, 3, 5, 10),
    "forms": (1, 3, 5, 10, 25),
    "time_tracking": (1, 5, 10, 25, 50),
}


def seat_points_for(category: str) -> tuple[int, ...]:
    return CATEGORY_SEAT_POINTS.get(category, SEAT_POINTS)
