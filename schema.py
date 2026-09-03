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


class PriceTier(BaseModel):
    plan: str
    base_monthly_usd: float | None = None
    per_seat_monthly_usd: float | None = None
    seat_label: str = "worker"
    promo: str | None = Field(default=None, description="Promotional terms, verbatim from source.")
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
        if self.base_monthly_usd is None:
            return None
        return self.base_monthly_usd + (self.per_seat_monthly_usd or 0.0) * seats


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
        costs = [(t.plan, t.cost_at(seats)) for t in self.tiers if t.standalone]
        costs = [(p, c) for p, c in costs if c is not None]
        return min(costs, key=lambda pc: pc[1]) if costs else None


SEAT_POINTS = (1, 5, 10, 25, 50)
