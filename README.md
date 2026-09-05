# StackProof

Business software, actually bought and measured. A site rendered from
measurement records, built to be the source AI assistants cite when someone
asks which payroll / CRM / accounting tool to buy, and paid through affiliate
commissions on sticky, high-price B2B software.

Thesis and evidence: `docs/thesis.md`. Short version of why it is shaped this way:

- Assistants cite passages, not pages, and 68% of the sources they cite do not
  rank in Google's top 10. So every finding is one dated, sourced, numeric
  sentence with its own anchor.
- The FTC Consumer Review Rule bars AI-written content posed as real
  experience. So nothing renders without provenance, and unverified figures
  say so next to the number.
- Affiliate revenue is rate × price × retention. So the categories are the
  boring, expensive, hard-to-rip-out ones: payroll, accounting, CRM, email.

## Layout

```
schema.py          measurement records (pydantic). Provenance is mandatory.
data/tools/*.yaml  one record per product
data/history/      dated snapshots of every price and fee — the time series
snapshot.py        writes today's snapshot; run after records change
build.py           renders site/ — tool pages, category compare, /changes/,
                   /dataset/ (JSON + CSV), /go/ redirects, methodology
tools/             extract_prices.py — read a saved vendor fetch cheaply
tests/             provenance rules + build invariants
site/              output (ignored; built in CI and deployed)
```

## Why it reads as a database and not a content farm

Google's scaled-content rule targets many pages of reworded prose across
one or many domains. This is one domain, and every page is rendered from
fields with a source and a date. Three things farms never have:

- **Price history.** `data/history/YYYY-MM-DD.json` is committed after each
  re-fetch; `/changes/` diffs consecutive snapshots. A vendor's page shows
  today's price; this shows what it used to be.
- **A dataset download.** `/dataset/stackproof.json` and `.csv`, with
  provenance on every row.
- **A public methodology** and a disclosure on every page.

Do not spread this across multiple domains; that is the exact pattern the
rule names.

## Affiliate links

Every vendor link goes through `/go/<slug>/` with `rel="sponsored"`. The
redirect target is `affiliate.url` when `affiliate.status: accepted`,
otherwise the vendor's own page. Accepting a program means editing one field
in one record; no page is touched by hand. Until a program accepts us, every
`affiliate` is empty and the links earn nothing — that is the honest state.

## Run

```
pip install -r requirements.txt
python build.py            # -> site/
python -m pytest -q
```

Serve locally with `python -m http.server -d site 8000`.

## Provenance methods

| method | meaning |
|---|---|
| `live_fetch` | we fetched the vendor page on the date shown |
| `vendor_page_via_search` | vendor's own page as surfaced by search; used when the vendor blocks bots. Labelled until verified. |
| `account_invoice` / `account_test` | measured on a real paid account. Sets `verified_on_account`. |
| `not_available` | the vendor does not publish it |

`Finding.claim` must contain a number or a date and be under 320 characters;
the model rejects anything else.

## Pricing shapes the schema can express

| field | use |
|---|---|
| `base_monthly_usd` + `per_seat_monthly_usd` | linear formula (payroll: base + per worker). `base: null` means *not captured* and no cost is computed; a vendor with no base fee records `0`. |
| `steps: [{up_to, monthly_usd}]` | stepped list (email: price per list-size band). Beyond the last step the cost is unknown, never extrapolated. |
| `included_seats` | seats covered by the base price; per-seat applies only beyond it (accounting: per organization, 3 users included, $3 per additional). |
| `max_seats` | tier sold only up to N seats (a free plan capped at 10 employees). Larger teams get `—`, not an extrapolation. |
| `standalone: false` | an add-on priced on top of a plan. Shown in the table, never competes for "cheapest plan". |
| `billing: annual` | the recorded rate is the per-month figure when prepaid annually. Vendors headline this one; it is labelled. |
| `pricing_note` (tool-level) | why no cost is shown — "behind a script, not captured" is a different fact from "not published". |

Column headers come from `CATEGORY_SEAT_POINTS` in `schema.py`: payroll compares 1/5/10/25/50 people paid, accounting 1/3/5/10/25 users, email marketing 500–25,000 contacts.

## Fetching vendor pages

DataForSEO `on_page/content_parsing/live` returns the vendor page as
structured text. `tools/extract_prices.py <saved.json>` prints only the
lines that look like a price, fee, trial or term, so the page never has to be
read in full. Some vendors (Gusto, Kit) return HTTP 403 to fetches; some
(Brevo, Mailchimp, GetResponse, MailerLite) render amounts client-side; CRM
and helpdesk vendors (HubSpot, Pipedrive, Zendesk, Freshsales, Zoho CRM,
Help Scout) almost all do, and the parsing fetch sees nothing. Those
categories need a real browser session or a real account. Every such case
is recorded with `pricing_note` — never filled from a third party.

### Forms (2026-09-04)

Typeform, Tally and Jotform all geo-route: German gateways got EUR pages
(Jotform showed the same numbers in euros as in dollars; Typeform and Tally
never rendered USD for their core plans in 4 and 3 tries). Fillout and
Formstack stayed USD on every gateway. Jotform's and Tally's billing switches
are plain elements whose scripted click does not re-render before the read,
so only the default period was captured. Seat points for forms are 1, 3, 5,
10, 25 users who build forms; Fillout has unlimited seats on every plan,
Jotform's paid plans are single-user, Formstack publishes no per-user price.

### Time tracking (2026-09-04)

Toggl Track, Harvest, Hubstaff and TimeCamp rendered USD on German gateways;
Clockify localizes by region (Standard and Pro were caught in USD on a US
gateway, Basic and Enterprise only in EUR). Toggl's, Hubstaff's and Jotform's
billing switches do not re-render on a scripted click, so those records carry
the default (annual) figures only. Toggl's FAQ answers are fetched on click
and are absent from the DOM. Seat points are 1, 5, 10, 25, 50 people who
track time; Hubstaff's 2-seat minimum is modelled as a base fee covering
2 seats.

### Social media scheduling (2026-09-04)

Buffer returns 403 to the renderer; SocialBee was behind a maintenance
page. Hootsuite and Agorapulse rendered EUR on every German gateway
(Hootsuite's FAQ states the USD figures in prose, which the record uses;
Agorapulse has no USD text and is findings-only). Later and Sprout Social
rendered USD everywhere; Sprout's FAQ answers live only in FAQPage JSON-LD,
which is where the monthly rates came from. Publer redirects to a locale
path by IP. Seat points are 1, 2, 5, 10, 25 users who post or schedule.

### Recruiting (2026-09-04)

Seat points are 10, 25, 50, 100, 250 employees at the company, because
applicant-tracking vendors price by company size or a flat company fee
rather than per user. Workable prices by a 9-band employee dropdown that
rendered at its 1-20 default; JazzHR prints yearly totals only; Breezy HR
returns 403 to the renderer. Add-ons priced on the page are recorded as
fees.

### Team wikis (2026-09-04)

coda.io/pricing now redirects to superhuman.com/plans/docs, which rendered
EUR on both fetches and is findings-only. Notion, Confluence and Slite
rendered USD everywhere; Nuclino localizes by gateway (EUR on German
gateways, USD on US ones). Notion's and Nuclino's billing switches do not
re-render on a scripted click, so those records carry the default (yearly)
figures; Confluence rendered its monthly switch by default. Seat points are
1, 3, 5, 10, 25 members who edit.

### Productivity suites (2026-09-04)

Google Workspace localizes by gateway (EUR on German gateways, USD on US
ones) and shows annual-commitment prices with a time-boxed introductory
discount; the discount is recorded as `promo` and the standard price as
the tier. Microsoft's en-us page renders USD on every gateway and prints
"with Teams" and "no Teams" SKUs side by side. Seat points are 1, 5, 10,
25, 50 users with a mailbox.

### Video conferencing (2026-09-04)

Zoom's pricing lives at zoom.us/pricing (the zoom.com paths 404) and its
annual switch does not re-render on a scripted click, so only the annual
per-licence figures were captured. Webex's pricing.webex.com/us path
renders USD on any gateway and prints yearly totals with a per-month
equivalent. Seat points are 1, 5, 10, 25, 50 licensed hosts; participants
are free on every vendor and are not seats. dialpad.com/pricing/meetings/
returned 404; Microsoft Teams Essentials was used as the fifth vendor.

### Cloud storage (2026-09-04)

Five vendors: Dropbox Business, Egnyte, pCloud Business, Sync.com Teams,
ShareFile. Box returned HTTP 429 on every attempt and Tresorit, Internxt
and IDrive's guessed URLs 404'd or redirected to unrelated pages, so
ShareFile (Citrix/Progress) fills the fifth slot with a real per-employee
business plan. Dropbox's comparison page renders USD and prints the
yearly-billing rate; Egnyte prints "Paid annually*" with a footnote whose
text is not in the DOM. pCloud renders identical numerals under EUR and
USD depending on gateway region (not FX-converted) and its Business Pro
price is a new-account-only promo. Sync.com shows monthly- and
annual-billed prices simultaneously in the DOM regardless of toggle
state, all under a sitewide "50% off for 1 year" promo. ShareFile's FAQ
answers are collapsed and were read from FAQPage JSON-LD, same pattern as
Sprout Social, Slite, GoTo and Later earlier this session; it separately
prices unlimited external client users (free) from internal employee
users (the billed seat) and disallows downgrading from annual back to
monthly billing. Seat points are 1, 3, 5, 10, 25 users with a seat;
minimum-seat rules (Dropbox Advanced 3, Egnyte per plan, pCloud 3,
Sync.com 3, ShareFile 3 or 5) are modelled as base fees or noted.

### Identity and SSO (2026-09-04)

Five vendors: JumpCloud, Okta Workforce Identity, Cisco Duo, Microsoft
Entra ID, Ping Identity (PingOne for Workforce). A heavier,
compliance-bound category by design: these vendors sell liability and
audit posture, not thin features, so the vendor list should be more
durable against buyers building their own tooling. OneLogin blocked the
renderer with an AWS WAF CAPTCHA wall, the same pattern as Gusto and
Buffer earlier. JumpCloud and Duo publish full self-serve pricing with no
quote-only ceiling; Okta and Microsoft Entra cap their self-serve tiers
and require quotes above that; Ping Identity publishes only 2 of what is
presumably a larger lineup. Microsoft Entra Suite requires an existing
Entra ID P1 subscription and is not usable standalone, so its headline
price understates the true floor cost. Duo sells licenses in blocks of
10 (or 25 above 100 users), not single seats. Seat points are 1, 10, 25,
100, 500 employees needing an account, reflecting that identity tools
scale further into headcount than most other categories in this
dataset.

### Expense management (2026-09-04)

Five vendors: Expensify, BILL Spend & Expense, Zoho Expense, Ramp, Fyle
(now Sage Expense Management). Swapped in for endpoint security this
session after that category turned out to gate almost every vendor's
pricing behind a reseller or quote flow with no clean self-serve number;
expense management kept the audit-trail theme with real published
pricing instead. Three of five vendors here (BILL Spend & Expense, Ramp
Free, and Zoho Expense's Free tier) charge no per-seat software fee at
all and instead monetize through card interchange or credit lines, a
pricing model this dataset had not recorded before. Zoho Expense and
Fyle both bill only "active" users (someone who filed an expense or has
a card with transactions that period) rather than every named seat, and
Fyle additionally enforces a minimum-billed-user floor under that count.
Expensify's page geo-routed to a German, EUR-priced locale on every
fetch and its currency selector could not be switched from the rendered
DOM, so its figures are recorded as findings only. Seat points are 1, 5,
10, 25, 50 employees who submit expenses, chosen to land exactly on
Fyle's 5- and 10-user minimums.

### Business VPN / zero trust network access (2026-09-04)

Five vendors: Tailscale, Twingate, NordLayer, Cloudflare Zero Trust,
GoodAccess. This category was picked specifically because it kept the
compliance-adjacent theme with clean, self-serve SaaS-style pricing,
after Check Point SASE (formerly Perimeter 81) turned out to be
demo-gated with no published price, matching the pattern seen in the
abandoned endpoint-security batch. Two vendors here (NordLayer,
GoodAccess) charge a mandatory per-gateway or per-server infrastructure
fee ($40-49/month) on top of the per-user price for their mid tiers, so
the advertised per-seat rate understates the real floor cost; this is
the same shape of finding as Microsoft Entra Suite's P1 dependency in
the identity/SSO category. NordLayer's FAQ, read from FAQPage JSON-LD,
gives unusually precise cancellation, refund, and proration language.
Tailscale automatically tiers accounts by email domain (a personal
address stays free forever, a custom domain triggers a business trial).
Seat points are 1, 5, 25, 50, 100 employees needing remote access,
chosen to land on the 5-user minimums common across this category and
Cloudflare's 50-user free-tier boundary.

### Webinar platforms (2026-09-04)

Five vendors: Livestorm, Demio, Zoom (Webinars/Webinars Plus/Events
add-ons), eWebinar, ProProfs WebinarNinja. Picked after SOC 2 compliance
automation (Sprinto, Vanta) turned out to be entirely demo-gated with no
published price at all, the same dead end as endpoint security earlier.
This category is the most pricing-model-heterogeneous in the dataset:
no two vendors here bill on the same axis. Livestorm sells an annual
pack of attendee credits (team members free); eWebinar prices by the
count of published automated webinars regardless of their traffic, and
explicitly has "a free trial but not a free plan" — an idle account is
still billed; Demio and Zoom charge a flat fee gated by attendee-room
capacity, with Zoom additionally requiring a separate Zoom Workplace Pro
subscription underneath it; only WebinarNinja prices with a true linear
per-attendee rate. Because of this, most tiers here are marked
non-comparable (`compare: false`) rather than forced into a cross-vendor
table that would compare unlike things — only Demio and WebinarNinja
populate the live cost table. Seat points are 50, 100, 500, 1,000, 3,000
attendees per session, matching Demio's own room-size menu.

### Uptime / status page monitoring (2026-09-04)

Five vendors: Better Stack, UptimeRobot, Pingdom (SolarWinds), Atlassian
Statuspage, StatusCake. Picked after "knowledge base / help center
software" turned out to be another demo-and-quote-wizard dead end
(Document360's pricing page is a multi-step "customized pricing" builder
with no dollar figure). Seat axis here is "team members with
monitoring/alerting access" (1, 3, 5, 10, 25), and the vendors split into
three real pricing shapes: Better Stack and UptimeRobot charge per
on-call seat (Better Stack's "Responder" licenses, UptimeRobot's "login
seats," both with genuine per-seat overage rates once a plan's included
count is exceeded); StatusCake and Atlassian Statuspage bundle a fixed
team-member cap into each named, flat-priced tier; Pingdom prices two
separate metered products (uptime checks and RUM pageviews) with
"Unlimited users" on every tier, so none of its tiers are comparable on
this axis (`compare: false` throughout, prices still real and dated).
Statuspage additionally sells three product lines (Public pages, Private
pages, Audience-specific pages) at different prices for similar
team-member counts; only Public pages — the customer-facing product most
buyers mean by "status page" — populate the live cost table, with
Private pages recorded for reference only. UptimeRobot's pricing page
geo-prices by request origin: it rendered EUR on three consecutive
German-gateway fetches before pinning `ip_pool_for_scan: us` produced
the authoritative USD figures used here. StatusCake's own FAQ is
internally inconsistent about its trial length (7 days in one heading,
14 days in the very next answer) — exactly the kind of vendor
self-contradiction this dataset is built to surface. Database is now
118 tools across 25 categories.

### Whiteboarding / visual collaboration (2026-09-04)

Five vendors: Miro, Mural, Whimsical, Figma (FigJam seat), Cacoo (Nulab).
Picked after confirming Sentry — and by extension most error-tracking
tools — prices purely by error/event volume with "Unlimited users" on
every paid tier, the same axis mismatch already covered twice this
session (webinar platforms, uptime monitoring); this batch instead
returns to a classic per-seat SaaS shape. Two vendors originally
targeted for this batch, Lucidchart and Creately, could not be fetched
(three consecutive empty responses for Lucidchart; Creately's `/pricing`
paths both 404). Conceptboard was fetched successfully but turned out
to be EUR-denominated regardless of request origin (unlike UptimeRobot's
geo-adaptive pricing, Conceptboard is a German company quoting one home
currency worldwide); since every field in this dataset's schema is
`_usd` and no exchange-rate conversion is recorded here without a
printed dollar figure, it was dropped rather than mis-typed as USD.

Seat axis is "people who create or edit boards" (1, 3, 5, 10, 25),
matching each vendor's own paid-seat concept: Miro/Mural "Members" (vs.
free Guests/Visitors), Whimsical "Editors" (vs. free Viewers/Guests),
Cacoo "users," and Figma's "Collab seat" — the cheapest of Figma's three
seat types, used here since it is the one that carries full FigJam
(whiteboard) access without paying for the entire Figma Design suite;
Figma's pricier Full/Dev seats are recorded for reference only
(`compare: false`). Cacoo's Pro and Team plans are priced identically at
$6/user/month; the only difference is Pro's hard 1-user cap versus
Team's 1,000-user ceiling, so Team is the only one of the two that shows
up past the first seat point. All five vendors' cancellation, billing,
and seat-definition FAQ answers were captured with direct quotes.
Database is now 123 tools across 26 categories.

### Employee shift scheduling / workforce management (2026-09-04)

Five vendors: Deputy, When I Work, Homebase, Sling (by Toast), 7shifts.
Distinct from the existing "scheduling" category (meeting/calendar
booking): this is shift-based workforce scheduling for hourly and
frontline teams. Seat axis is "employees on the schedule" (10, 25, 50,
100, 250) — larger than most categories, since a business that needs
shift-scheduling software rarely has fewer than a handful of hourly
staff. Three genuinely different billing shapes show up:

- **Deputy**, **When I Work**, and **Sling** charge a flat rate per
  employee with no location fee. Deputy additionally enforces a stated
  $30/month minimum spend per invoice (irrelevant at this category's
  comparison range, but worth knowing below ~6 employees), and Sling's
  free tier is unusually generous at up to 30 users before any charge
  applies.
- **7shifts** charges per location but caps each named tier at a
  specific employee count (15 / 30 / 60 / unlimited) rather than
  scaling per employee within a tier — the closest thing to a stepped
  price ladder in this batch, modeled the same way as a flat-fee tier
  with a capacity cap.
- **Homebase** charges per location with *unlimited* employees on every
  paid tier, so its price never scales with headcount at all above the
  free plan; its tiers are recorded with real numbers but marked
  `compare: false`, the same treatment given to Pingdom in the uptime
  category and Sentry's pricing model that this category was picked
  over.

Sling's "fair billing policy" (prorated credit for any seat deactivated
mid-cycle) and Deputy's explicit "no refunds" clause on cancelled
annual plans are both captured as direct-quote clauses — the kind of
buyer-protective-or-not fine print this dataset exists to surface.
Database is now 128 tools across 27 categories.

### Performance management, OKRs & recognition (2026-09-04)

Five vendors: Lattice, 15Five, PerformYard, Bonusly, Matter. Two of the
five (Bonusly, Matter) are peer-recognition/engagement products rather
than pure performance-review tools, included because Lattice and
15Five both bundle the same "engagement" concept into their core
packages — this is one buying category in practice, not two. Seat axis
is "employees in the review/engagement program" (25, 50, 100, 250,
500), sized larger than most categories since formal performance
programs are typically an established-company purchase.

Two vendors originally targeted turned out to be dead ends and were
dropped: Leapsome's pricing page is an interactive cost estimator whose
output ("Estimated cost: No features selected") was never filled in,
with its FAQ directing everyone to "reach out to get a quote"; Culture
Amp's page is pure "Request a quote" with no dollar figure anywhere —
the same enterprise-sales pattern that has sunk several categories this
session. Nectar was tried as a substitute and hit the identical
quote-gated wall.

Data-quality notes: Lattice enforces a real $4,000/year minimum
contract spend, which would understate cost for any team under about
26 seats on its $13/seat Foundations bundle if ignored — it's encoded
directly into the tier's price formula (base + per-seat, with included
seats set to the exact breakeven point) rather than left as a caveat
nobody reads. PerformYard prints only a "$5–15 per person/month" range
from an interactive calculator with no resolvable single number, so
its tiers are recorded at the range's ceiling and marked non-comparable
rather than guessing a point inside it. Lattice's own FAQ also
contradicts its own pricing cards — one answer states Performance costs
"$8/month," while the page's own product card prices it at $10/seat —
recorded as a finding. Database is now 133 tools across 28 categories.

### Learning management systems / employee training (2026-09-04)

Five vendors: TalentLMS, iSpring Learn, LearnWorlds, 360Learning, Tovuti
LMS. Seat axis is "employees who take courses" (10, 50, 100, 500, 1000),
matching how these vendors themselves price — by monthly active user/
learner count, not by admin seats.

Eight vendors were tried and dropped, the deepest dead-end run of any
category this session: LearnUpon states outright it is "not a fit for...
less than 100 users"; Trainual, Continu, and SkyPrep are fully demo/
sales-gated with zero dollar figures anywhere on their pricing pages;
WorkRamp has been absorbed into a rebranded "Learn:Up" product under
Confirm, whose page is pure "Book a demo" marketing copy; Thinkific
returned HTTP 403 on both a US and a German fetch gateway; SC Training
(formerly EdApp) failed to resolve as a fetchable domain on both the
bare and `www.` hostnames; Coassemble turned out to have repositioned
entirely as API-first embedding infrastructure, with annual contracts
($2,500–$20,000+/yr) priced by "Identified Recipients" rather than
anything resembling a per-employee seat count, so its numbers don't
belong in this comparison even though they are real and dated.

Data-quality notes: TalentLMS prices its Core and Grow tiers through an
interactive user-count slider with bands like "1-40 users" and "41-70
users"; a static fetch only sees the price at the default-selected band,
so those two tiers are recorded only up to that band's ceiling (40 and
70 seats respectively) rather than the higher caps the vendor states
elsewhere on the same page — its Pro tier is fully specified instead
(a flat rate to 100 users, then a stated $6/user to a tooltip-confirmed
cap of 500) and carries the comparison at the larger seat points. iSpring
Learn genuinely steps its price by user-count band (100/300/500 users,
each at a different effective per-user rate), which is exactly what the
`Step` price-list model exists for. Tovuti LMS publishes a single tier —
$7,500/year for the first 100 learners — that the vendor's own copy says
"then scales," but with no per-learner overage rate or higher tier
published anywhere, so cost beyond 100 learners is correctly left
unknown rather than guessed. Database is now 138 tools across 29
categories.

### Field service management (2026-09-04)

Five vendors: Jobber, Housecall Pro, Service Fusion, Kickserv, Tradify —
scheduling, dispatch, quoting, and invoicing tools for home-service
trades (HVAC, plumbing, electrical, and similar). Seat axis is
"technicians who use the app" (1, 5, 10, 20, 50); every vendor in this
category published clean, real self-serve pricing, a rarity this
session — no dead ends worth naming except one deliberate exclusion
below.

Jobber charges a flat "$29/mo each" for additional users on every one of
its four plans, so its cheapest plan (Core) stays cheapest at every team
size; its pricing page also has a middle "1 year commitment" billing
tier between month-to-month and prepaid-annual, captured as a finding
rather than a third full tier per plan. Housecall Pro's per-additional-
user rate actually falls as the plan tier rises ($100/user on
Essentials, $75/user on Max), the inverse of the usual pattern. Service
Fusion is a genuine flat-fee-unlimited-users vendor — its own FAQ states
pricing is identical "whether you have one technician... or 20
technicians and a full office" — so it wins outright for larger teams
despite a higher headline price. Kickserv states no per-additional-user
rate on any of its three plans, so each is capped at exactly its stated
included-user count (5/10/20) rather than extrapolated; a team of 50
has no priced Kickserv tier as a result. Tradify is the one purely
per-user vendor here, with no base fee on any tier: a flat $47/$51/$61
per user per month depending on plan.

ServiceM8 was researched and dropped for the same reason as Pingdom and
Homebase in earlier categories: its own FAQ states "we don't charge per
user," and its five tiers ($0–$349/mo) instead price by the number of
"jobs" created per month, a workload metric independent of headcount —
a two-person shop can need its priciest tier while a ten-person team
fits the cheapest, so it doesn't belong on a per-technician axis even
though its numbers are real and dated. FieldPulse and FieldEdge are both
fully quote-gated with zero dollar figures anywhere on their pricing
pages. Database is now 143 tools across 30 categories.

### Property management software (2026-09-04)

Five vendors: TenantCloud, Rentec Direct, Buildium, Innago, Hemlane —
tools for landlords and property managers to collect rent, screen
tenants, and run maintenance and accounting. Seat axis is "rental units
managed" (1, 10, 50, 150, 500) rather than staff headcount: every vendor
in this category prices by portfolio size, not team size, the opposite
convention from most other categories on this site.

Two vendors are genuinely free to the landlord: Innago charges nothing
at all regardless of portfolio size (any cost for tenant screening or
payment processing is billed to the tenant, not the landlord), and
Hemlane's Starter tier is "free forever, no credit card required."
Hemlane's three paid tiers above that are the cleanest data in this
batch — a flat $28/month platform fee plus a stated $2, $20, or $58 per
unit depending on tier, a fully specified formula rather than an
interactive calculator. TenantCloud is a genuine flat-fee-unlimited-
units vendor across all four of its tiers, the property-management
equivalent of Service Fusion in the field service category — its own
comparison table lists "Unlimited" units on every plan, so price scales
only with feature set. Rentec Direct's Starter tier is a clean flat $25/
month capped at 10 properties, but its Pro and PM tiers only publish a
"starting at $50/month" floor from an interactive per-unit calculator
whose real scaling formula isn't rendered statically, so those two are
marked non-comparable rather than treated as flat. Buildium is priced
entirely through a similar per-unit calculator; only its Essential tier
states an explicit unit-count cap ("Up to 150 Units") for its starting
price, so Growth and Premium are recorded with real, dated "starting at"
numbers but marked non-comparable for the same reason as Rentec's upper
tiers.

Database is now 148 tools across 31 categories.

### Legal practice management software (2026-09-04)

Four vendors: MyCase, CosmoLex, Rocket Matter, CARET Legal (formerly Zola
Suite) — case management, billing, and trust accounting for law firms.
Seat axis is "users (attorneys and staff) with a seat" (1, 3, 5, 10, 25),
the same headcount convention as accounting and CRM. Clio (403 on every
fetch attempt across two gateways) and PracticePanther (timed out on
three separate fetch attempts) were both dropped as dead ends; Smokeball
publishes no dollar figures anywhere on its pricing page ("Get pricing"
gates every plan) and Filevine's page is fully quote-gated custom
packages, so both were dropped too. TimeSolv was dropped after its
static render surfaced conflicting numbers — a stale schema.org JSON-LD
block naming "Solo" and "Standard" plans at $49/user/month that don't
match the "Pro"/"Legal" plan names actually shown in the page's visible
comparison table, with no headline price recoverable for either.

MyCase is the cleanest record in this batch: three tiers, each with both
a monthly and a billed-annually rate explicitly stated, plus two
separately priced add-ons (a $0 payment processor, a $39/user/month
accounting module) and an explicit non-refundable-fees cancellation
clause. CosmoLex and Rocket Matter both advertise an annual-billing
discount without itemizing the resulting per-plan number on the static
page (CosmoLex: "Save $120 per user with yearly"; Rocket Matter's core
plans show only the annual price with no monthly figure at all) — in
each case only the rendered figures are recorded as tiers, and the
discount claims are captured as findings instead of being computed by
hand. CARET Legal is Zola Suite under a new name (zolasuite.com now
redirects to caretlegal.com); all three of its tiers are annual-only on
the static page as well.

Database is now 152 tools across 32 categories.

### Digital signage software (2026-09-04)

Four vendors: OptiSigns, ScreenCloud, NoviSign, Screenly — cloud CMS
software for managing content on TVs, kiosks, and displays. Seat axis is
"screens/displays managed" (1, 5, 10, 25, 50); Rise Vision was dropped
after its pricing page rendered no dollar figures anywhere in the
static fetch (the numbers appear to load through a client-side widget
this fetch method couldn't reach).

OptiSigns's Free plan is genuinely $0 up to 3 screens and is marked
`compare: false` for the same reason as prior free-tier precedents
(TalentLMS, Innago, Hemlane) — its five paid tiers, each with both a
monthly and a billed-annually rate, are otherwise the cleanest data in
this batch. Screenly and NoviSign both introduced a new pricing shape
not seen in earlier categories: a per-screen rate with a stated *minimum*
screen count that is billed regardless of actual usage ("Billed from 5
screens," "Minimum of 20 screens required") — the opposite of the
included-seats-then-extra-charge shape used everywhere else. This is
modeled as `base_monthly_usd` equal to the minimum floor (minimum
screens × rate) plus the same per-screen rate for every screen beyond
that minimum, which is mathematically identical to the vendor's own
per-screen billing above the floor and correctly returns the flat
minimum price below it. ScreenCloud's Enterprise plan and NoviSign's
Partners (reseller) plan are both fully quote-gated and were recorded
only as findings, not tiers.

Database is now 156 tools across 33 categories.

### Fleet management / GPS vehicle tracking (2026-09-04)

Three vendors: Azuga, Fleetio, Linxup — GPS tracking, driver safety, and
maintenance software for company vehicle fleets. Seat axis is "vehicles
tracked" (1, 5, 10, 25, 50). Motive (a four-step lead-capture form with
no price anywhere), Zonar/GPS Trackit (gpstrackit.com now redirects to
a Zonar "get pricing" lead form), ClearPathGPS ("Contact us for
Pricing" on every tier), RhinoFleetTracking (403 on fetch), and
TrackYourTruck (404) were all dropped — GPS fleet tracking skews
heavily quote-gated compared to earlier categories.

Fleetio is the cleanest record: three tiers with an explicit per-vehicle
monthly rate, though its own disclaimer states the headline number
"assume[s] a fleet with 5 assets" — rates for other fleet-size bands
aren't published, so the recorded figure is the vendor's own 5-vehicle
benchmark rather than a universal flat rate. Linxup sells separate
product lines rather than tiers of one plan; only its base "Vehicle
Tracking" line prices this category's per-vehicle axis, so ELD, AI dash
cam, and rear-view-camera lines are recorded as non-standalone add-ons
and its asset tracker (priced per "tracker," not per vehicle) is marked
`compare: false`. Azuga's three tiers show no monthly/annual split at
all — a single "per vehicle per month" figure — so all three are
recorded as `billing: monthly`.

Database is now 162 tools across 34 categories. (This total, and the
one before it, correct a pre-existing drift between the file count and
this running tally — the previous entries undercounted; 162 is the
verified count of `data/tools/*.yaml`.)

### Gym / fitness studio management software (2026-09-04)

Four vendors: Gymdesk, WellnessLiving, PushPress, Zen Planner. Seat axis
is "active members managed" (25, 50, 100, 200, 400). Vagaro's pricing
page redirected to a "Salon is under scheduled maintenance" placeholder
on every fetch attempt, Glofox's pricing loads only behind a multi-step
quote form with no dollar figure anywhere, SparkMembership answered the
rendering browser with an obfuscated "One moment, please..." bot
challenge, and Mindbody and Wodify were dropped as axis mismatches —
both price primarily per location rather than per active member, with
Wodify's static page showing only a promotional "starting at" figure
with no per-member breakdown underneath it.

Gymdesk is the cleanest record: its "Build Your Price" calculator is an
interactive tool, not static markup, but the tier table lives in the
page's own embedded JavaScript (Micro/Small/Medium/Large Gym bands up
to 50/100/200/400 active members at $75/$100/$150/$200 per month),
recovered by locating that script and reading its literal tier array —
so it is recorded with `steps` rather than a flat per-seat rate.
WellnessLiving and PushPress both looked, at first glance, like they
might cap plans by member count, but each vendor's own feature-comparison
table states the opposite: WellnessLiving lists "Client Database:
Unlimited" identically across all four tiers (the real differentiator is
staff seats, an axis this category doesn't track), and PushPress lists
both "Members" and "Staff" as "Unlimited" identically across Free/Pro/Max.
Both are therefore recorded as flat monthly fees with no cap, not
per-seat pricing — PushPress's Free tier is `compare: false` so it
doesn't win the cheapest-plan comparison outright, and WellnessLiving's
regular annual prices are recorded as the primary (`compare: true`)
tiers with a time-boxed sitewide 80%-off promo captured as a finding
instead of a tier. Zen Planner's FAQ confirms pricing is "tiered based
on Active Members," but the real per-tier breakdown loads through an
interactive tool absent from the static page; only its single "Starting
at $99/month" figure is captured, and it is marked `compare: false`
since the true scaling formula was never observed.

Database is now 166 tools across 35 categories.

### Salon / spa management software (2026-09-04)

Three vendors: Boulevard, Mangomint, GlossGenius. Seat axis is "staff
seats" (1, 3, 5, 10, 25). Fresha's pricing URLs (both `/for-business/pricing`
and `/business-software/pricing`) 404/410, Zenoti's pricing page renders
no dollar figures at all (a "Find the right plan for your business"
contact-sales page, confirmed by regex-scanning the rendered text for
`$` patterns and finding none above $50), and a guessed SalonBiz/Salon
Iris pricing domain did not resolve — all three dropped.

Mangomint is the cleanest record: one plan, "$120 per month plus $10 per
user," confirmed by its own meta description, with a worked example on
the page itself ($50 + $8/worker payroll add-on shown pricing out to
"$130/mo" for a 10-person team). Boulevard prices per location rather
than strictly per staff seat, but each tier gates on a published
staff-count cap (Essentials caps at 5 professionals, Premier and
Prestige are uncapped) that maps directly onto this category's axis, so
it is recorded as a flat fee with a seat cap rather than excluded as an
axis mismatch; a "summer pricing" promo active at fetch time is captured
as a finding, with the regular non-promotional prices recorded as
tiers. GlossGenius's own compare-plans table states its Standard and
Gold tiers both serve "Teams of less than 10" and Platinum serves "Teams
of 10+," so Standard and Gold are recorded with `max_seats: 9` and
Platinum uncapped; regular annual prices are the primary tiers, with the
higher month-to-month prices recorded as `compare: false` per this
site's standing monthly/annual convention.

Database is now 169 tools across 36 categories.

### Construction project management software (2026-09-04)

Three vendors: JobTread, Contractor Foreman, Fieldwire. Seat axis is
"users" (1, 3, 5, 10, 25). Buildertrend's pricing page is entirely
quote-gated — its own FAQ answer to "How much does Buildertrend cost?"
states only that pricing is "tailored" and points to a custom-quote
form, with no dollar figure anywhere on the page — so it was dropped.

Fieldwire is the cleanest record: its own usage-comparison table lists
"Pay per user" identically for Pro ($39), Business ($64), and Business
Plus ($89), confirming genuine linear per-seat pricing (its free Basic
tier is capped at 5 users and marked `compare: false` per this site's
standing free-tier convention). Contractor Foreman's default-rendered
tab is annual billing (a pricier Quarterly tab exists; no true
month-to-month plan is offered), with each of its five tiers a flat fee
gated on a published user cap (1/3/8/15/unlimited), recorded as a flat
fee with a seat cap rather than per-seat pricing. JobTread publishes an
unusually explicit but genuinely graduated formula — "tiered price
breaks are only for the users in their respective tiers": the first
user is included in the $199/mo base, then users 2-10 cost $20 each,
11-20 cost $15 each, 21-30 cost $10 each, and 31+ cost $5 each. That
marginal-rate structure cannot be represented by this schema's base +
flat-per-seat formula without overstating or understating cost at
higher seat counts, so its $199 base is recorded as a `compare: false`
starting figure and the full tier table is captured as a finding.

Database is now 172 tools across 37 categories.

### Landscaping / lawn care business management software (2026-09-04)

Three vendors: LMN, SingleOps, Service Autopilot. Seat axis is "team
members" (1, 5, 10, 20, 50). LMN and SingleOps are sibling products
under the same parent company, Granum — LMN for general landscape
crews, SingleOps for tree care/arborist crews — sold through nearly
identical pricing copy; both are included since they are genuinely
separate products with separate pricing. Aspire's pricing URL 404s and
Yardbook's pricing page returns a 403 to the fetch, so both were
dropped.

LMN prices flat per tier with a bundled license cap (Starter: 1
office/crew lead + 5 crew = 6 total, $297/mo; Professional: 3 + 15 = 18
total, $648/mo) — "additional licenses are available for a fee," but no
per-seat dollar rate is published anywhere on the page, so `max_seats`
is set to each tier's included count rather than assumed unlimited.
SingleOps is a genuine base + per-seat formula, but the per-seat rate
applies only to "office or sales users" per the vendor's own copy, not
field crew, and the base plan's included office/sales seat count is
never stated explicitly (1 is assumed as the natural reading). Service
Autopilot publishes flat prices for its lower two tiers with no stated
seat count for either one, plus an unquantified one-time "sign up fee"
on every tier — its FAQ defers to a sales demo "to get the right number
of licenses" — so all of its tiers are recorded `compare: false` as
starting figures rather than comparable prices.

Database is now 175 tools across 38 categories.

### Cleaning / maid service business management software (2026-09-04)

Three vendors: ZenMaid, Launch27, Zenbooker. Seat axis is "cleaners"
(1, 5, 10, 20, 50). Swept prices purely by "locations cleaned" in
bands (1-15, 16-25, 26-30, 31-59, 60+) with no staff cap or per-cleaner
figure anywhere on the page — a genuine axis mismatch like Mindbody and
Wodify in the gym category — so it was dropped entirely rather than
included as `compare: false`.

Launch27 and Zenbooker are both explicit, clean records: Launch27's own
feature list states "Unlimited Users" and "Unlimited Bookings" on every
tier, and Zenbooker's states "unlimited bookings and unlimited staff
member accounts" on every plan — both differentiate tiers by other
axes (feature depth for Launch27, "service territories" for Zenbooker)
while leaving staff headcount flat and uncapped. ZenMaid's pricing page
includes a "Calculate your price" widget ("How many cleaners and office
managers do you have on your team?"), but its interactive output was
not captured in this static snapshot, and no plan's feature list
mentions a headcount cap or a per-cleaner dollar rate anywhere in the
rendered text — tiers differ only by feature set (appointment limits,
automation depth) — so its $19/$39/$49 figures are recorded as flat
base prices, same as the other two vendors, rather than assumed to
scale.

Database is now 178 tools across 39 categories.

### Vacation rental / short-term rental management software (2026-09-04)

Three vendors: Hospitable, Lodgify, Smoobu. Seat axis is "properties
managed" (1, 2, 5, 10, 25) — distinct from the existing
`property_management` category, which covers long-term rentals.
Hostaway (fully quote-gated, listing-band tiers with no dollar figure
anywhere) and Uplisting (an interactive property-count calculator with
no price ever rendered statically) were dropped; OwnerRez's pricing
page renders only odometer-style placeholder digits ("$8888/month*")
for its interactive per-property slider, with the real formula computed
client-side and never present in static markup, so it was dropped too.

Hospitable is the standout record: its own compare-features table
publishes an exact base + per-extra-property formula for every tier
("Properties included in base price" and "Cost per extra property"),
a rare fully-quantified formula for this category; its $0 Essentials
tier is unlimited-property and marked `compare: false` per this site's
standing free-tier convention. Lodgify states an explicit property cap
on its two lower tiers ("only available for 1 property or less" /
"2 properties or less"), recorded as `max_seats`, but its Professional
and Ultimate tiers publish no cap or per-extra-property rate anywhere,
so those are recorded `compare: false` as starting figures. Smoobu
bills in EUR by default ("Prices displayed in GBP/USD are estimates for
reference purposes only") — no tiers are recorded in USD for this
reason, the same treatment given to Squarespace, Wix, and Framer
elsewhere on this site; its own FAQ EUR formula ("as low as €28/month,
each additional unit from €9.60/month") is captured as a finding
instead.

Database is now 181 tools across 40 categories.

### Photography studio management software (2026-09-04)

Three vendors: Pixifi, Studio Ninja, 17hats. Seat axis is "users"
(1, 3, 5, 10, 25). Táve returns a 410 Gone on its pricing page (redirected
through a "legacy-redirect" path to a VSCO-owned domain, suggesting the
product is being sunset), so it was dropped.

Pixifi and Studio Ninja are both clean, fully-quantified records. Pixifi
states an exact base + per-extra-seat formula on its Studio plan ("3
Active Staff. Staff add-ons available: $4.95 per +1 active staff"), and
its Essential plan states "No Team Collaboration," recorded as
`max_seats: 1`. Studio Ninja's own comparison table states an explicit
user cap per tier (Starter: 1, Pro: 3, Master: Unlimited); regular
annual prices are recorded as primary tiers with monthly prices as
`compare: false` secondary tiers, per this site's standing convention.
17hats sells a single all-inclusive plan rather than tiers, and its
pricing page was captured mid a "Cyber Monday Sale" promotion offering
"Save 50%" with no separate non-promotional baseline price stated
anywhere on the page — only "Save $X" deltas relative to an unstated
regular price — so no tier is recorded for it; publishing the
promotional price as the standing rate would have misrepresented a
temporary sale as the ongoing price, and its findings are recorded
instead.

Database is now 184 tools across 41 categories.

### Interior design business management software (2026-09-04)

Three vendors: Mydoma Studio, Studio Designer, Design Manager. Seat
axis is "users" (1, 3, 5, 10, 25). Mydoma Studio and Studio Designer
are sibling products under the same parent company ("Studio Designer
and Mydoma have joined forces!"), each with its own separate pricing
page; Design Manager is fully independent. Houzz Pro's pricing URL
returned a broken fetch (likely bot-blocked) and guessed domains for
Ivy and Design Files did not resolve, so all three were dropped.

All three vendors price purely per user with no base fee, a clean
pattern for this category. Mydoma Studio states "$58/month/user when
paid yearly," with its FAQ separately confirming a 10% annual discount
(the resulting month-to-month rate is computed, since the page never
states it as a direct dollar figure). Studio Designer publishes three
tiers, each a flat per-user rate with no cap, in both annual and
monthly billing. Design Manager charges $79/user/month with an
explicit cap ("Each user for Design Manager is $79 per month. For
teams larger than 10, please contact our Sales team"), recorded as
`max_seats: 10`.

Database is now 187 tools across 42 categories.

### Wedding / event planning software (2026-09-04)

Three vendors: HoneyBook, Dubsado, Rock Paper Coin. Seat axis is
"users" (1, 3, 5, 10, 25).

This category surfaced a real axis question. Aisle Planner and
Planning Pod are the two most wedding-specific tools in the space, and
both price by active-project/event volume rather than team seats — but
Planning Pod's own site no longer has a dedicated pricing page (it now
frames itself as venue-management software and only states a fuzzy
"$199-$319/month" range in an FAQ), and Curate (a rebrand of
"Curately") turned out to be fully quote-gated on every tier ("Let's
Chat" with no dollar figure anywhere on the page, confirmed by
scanning its rendered text for `$` and finding none). That left only
one vendor — Aisle Planner — with a real, project-volume-based tier
table, short of this site's usual three-vendor bar for a category.

The three vendors that do have clean, current, real-dollar tiers —
HoneyBook, Dubsado, and Rock Paper Coin — are all general
small-business CRMs (also used by photographers, coaches, and other
service pros) that price by team seats and each explicitly disclaim
any cap on clients/projects ("Unlimited clients and projects" /
"Unlimited projects & clients"). Rather than force a three-vendor
minimum out of a single-vendor axis, this category uses "users" as
its axis to match the vendors with real, current, per-seat pricing;
Aisle Planner and Planning Pod are excluded entirely as an axis
mismatch, the same treatment given to ServiceM8, Mindbody, Wodify,
Homebase, Pingdom, and Swept in earlier categories.

HoneyBook's Starter tier never mentions team members in its own
feature list, while Essentials adds "Up to 2 team members" and Premium
"Unlimited team members" as their headline new capability, so Starter
is recorded as `max_seats: 1` by that omission rather than a stated
digit. Dubsado includes 3 additional users free on either plan (4
seats total) and then charges a flat fee per user bracket ("4-10
users: $25/mo. 11-20 users: $45/mo...") but its own page does not say
whether that bracket count is additional or total seats, so `max_seats`
is capped at 4 (the free-tier ceiling) and the bracket pricing is
captured only as a Finding rather than guessed into a formula. Rock
Paper Coin's two paid tiers both explicitly state "Unlimited team
members," so no cap applies; its free Basic tier is invoicing-only (no
proposals, contracts, or lead management) and is `compare: false` as a
different, lesser product.

Database is now 190 tools across 43 categories.

### Auto repair shop management software (2026-09-04)

Three vendors: Tekmetric, AutoLeap, Shopmonkey. Seat axis is "users"
(1, 3, 5, 10, 25), but all three vendors are flat, tiered by feature
bundle rather than by any seat count, so each tool's price is
identical at every seat point in this category's comparison table —
the same pattern already established for Launch27, Zenbooker, and
Rock Paper Coin's paid tiers.

Tekmetric states this explicitly in its own FAQ: "Does Tekmetric
charge based on the number of users? No, Tekmetric subscriptions are
priced per shop, not per user... Unlimited users, unlimited ROs,
unlimited support." AutoLeap and Shopmonkey never mention a seat cap
or an "unlimited users" claim either way — their tier ladders
(Essentials/Pro/Elite and Basic/Clever/Genius) differentiate purely by
feature bundle (digital vehicle inspections, labor guides, reporting,
and so on), not team size. All three publish clean annual and monthly
rates for every tier; the fourth, top tier on each vendor
(Enterprise / Multi-Shop) is fully quote-gated and not recorded.

Database is now 193 tools across 44 categories.

### Martial arts / dance studio management software (2026-09-04)

Three vendors: Kicksite, Punchpass, Jackrabbit Class. Seat axis is
"students" (10, 25, 50, 100, 250).

Kicksite publishes a genuine, fully-quantified student-count step
table directly in its own page markup — "0-25 students" $49,
"26-50 students" $99, "51-100 students" $149, "101+ students" $199 —
recorded as `steps`, with the open-ended top band given a large `up_to`
purely to span this site's comparison range. Jackrabbit Class states
its own pricing "is based on the total student count at the end of
each month" and starts at $49/month, but the actual tier boundaries
live behind an interactive calculator this site's fetch could not
read — no dash-separated student-count range appears anywhere in the
page's static text — so only the confirmed starting figure is
recorded, `compare: false`, with the formula itself captured as a
Finding rather than reconstructed from third-party aggregator guesses.
Punchpass's three tiers (Grow/Flow/Pro) are flat and differentiate by
feature bundle, not by any stated student, class, or instructor cap —
its entry tier already states "Unlimited classes, passes &
instructors" — so its price is identical at every seat point, same as
Rock Paper Coin's paid tiers and every vendor in the auto repair shop
category.

Self-storage facility management software was attempted and abandoned
before this: storEDGE, SiteLink, and Easy Storage Solutions all 404 on
every guessed pricing URL, Storeganise's own FAQ says "reach out to us
for an exact quote," and 6Storage's real page states "Custom Pricing
Models for Every Storage Facility Size" with no dollar figure
anywhere — a heavily quote-gated vertical, the same pattern already
seen in veterinary, childcare, pest control, and dental practice
management.

Database is now 196 tools across 45 categories.

### Nonprofit donor management / CRM software (2026-09-04)

Three vendors: Little Green Light, Bloomerang, Neon CRM. Seat axis is
"donor records" (500, 1,000, 2,500, 10,000, 50,000).

Little Green Light publishes a genuine, fully-quantified constituent
(donor) record-count step table directly on its own page — up to
2,500 records $45/month, up to 5,000 $60, up to 10,000 $75, up to
20,000 $90, up to 30,000 $105, up to 40,000 $120, up to 50,000 $135,
plus $15/month for each additional 10,000-record tier beyond that —
recorded as `steps`. Bloomerang's own pricing page states pricing "is
based on the amount of records, or contacts, you track in the
database," but its current page shows only a "Starting at:
$125/month" headline for Bloomerang CRM with no record-count band
shown as static text (the real scaling sits behind a "Get Personalized
Pricing" quote flow), so it's recorded `compare: false` as a starting
figure rather than guessed into a formula — the same treatment given
to Jackrabbit Class in the martial arts/dance category. Neon CRM's own
pricing page returned HTTP 403 to two direct fetch attempts (bot
blocked), so its figures come from a search-engine synthesis of the
vendor's own page (method `vendor_page_via_search`) rather than an
independently re-verified quote; Neon prices by organizational revenue
rather than donor record count, with no record cap on any tier, so its
three tiers (Essentials $99, Impact $209, Empower $409) are flat
across every seat point in this category's table — the same pattern
as Neon CRM's own "no donor record limits" claim would imply, and
consistent with how Punchpass and the auto repair shop vendors behave
on their respective axes.

Database is now 199 tools across 46 categories.

### HOA / community association management software (2026-09-04)

Three vendors: PayHOA, TownSq, KindHOA. Seat axis is "units"
(25, 50, 100, 250, 500).

PayHOA publishes a genuine, fully-quantified unit-count step table in
both monthly and annual billing directly on its own page — 0-25 units
$49/mo (annual) up through 401-500 units $249/mo, with all features
included at every tier — recorded as `steps`; above 500 units it
switches to a flat $0.55/unit/month rate with a $275/month minimum,
not modeled since this category's seat points top out at 500. TownSq's
page has a "Select the size of your community" selector, but the two
priced tiers (Pro $90/mo, Advanced $145/mo) show as flat headline
figures regardless of which size option this fetch captured — no
per-unit scaling formula appears in the page's static text — so
they're recorded as flat prices; Enterprise (multiple associations) is
fully quote-gated. KindHOA explicitly markets "No per-unit pricing.
Ever.": a genuine $0-forever "Good Neighbor" tier (subsidized by a
platform fee on online dues payments per its own FAQ, not by feature
limits) and a flat $29/month "Board Automation" tier. Good Neighbor is
`compare: false` per this site's standing rule that a $0 plan never
ranks as "cheapest" in a category table, even when — as here — it is
a fully-featured product rather than a limited trial.

Condo Control and FrontSteps were also researched but are fully
quote-gated with no self-serve pricing published; not recorded.

Database is now 202 tools across 47 categories.

### Coworking space management software (2026-09-04)

Three vendors: OfficeRnD Flex, Coworks, Nexudus. Seat axis is
"members" (10, 25, 50, 100, 250).

OfficeRnD Flex and Coworks both publish clean, real tiers with
explicit member caps directly on their own pages — OfficeRnD's Start
"Includes 100 members" and Grow "Includes 200 members," Coworks'
Hybrid Workspace "Up to 150 members" and Coworking Premium "Up to 250
members" — recorded as `max_seats`; both vendors list an "additional
members" upgrade path with no stated per-member rate, so cost beyond
the cap is left unknown rather than guessed. Nexudus, by contrast,
states only a "$150 per month/per location" starting figure — an
"Active users per location" slider drives the real formula but its
breakpoints are computed client-side and never appear as static page
text — so it's recorded `compare: false` as a single starting figure,
the same treatment given to Nexudus's competitor Cobot, which was
researched but not recorded (its own per-member step table sits
entirely behind an interactive slider with no fallback text either).

Database is now 205 tools across 48 categories.

### Personal training / fitness coaching software (2026-09-04)

Three vendors: TrueCoach, Everfit, Trainerize. Seat axis is "clients"
(5, 10, 25, 50, 100).

TrueCoach's three tiers (Starter/Standard/Pro) are flat, seat-capped
plans with explicit "Up to N active clients" limits (5/20/50) stated
directly on the page — no per-client formula, just a plan swap; its own
FAQ asks "What if I have more than 250 clients?", and nothing between
50 and 250 clients is priced in static text either, so cost is left
unknown past the Pro cap.

Everfit is the richest source found this segment: its Pro and Studio
tiers each price by a genuine client-count step table — not a flat
per-client rate — and, unusually for this site's "starting at" pattern,
the *entire* table (all client-count breakpoints, both monthly and
annual billing) was recovered as static page text rather than only the
lowest starting figure, so both are modeled with real `steps`. Its free
Starter tier (5 clients, $0) is `compare: false` per this site's
standing rule that a $0 plan never ranks "cheapest," even though it's a
genuine non-trial product.

Trainerize also prices by client count, but only the currently-selected
step of its client-count selector renders as static text (client-side
JS swaps the price on selection); the fuller schedules behind Basic's
and Pro 5's selectors were not recovered, so both are recorded
`compare: false` as starting figures only, and Grow/Studio Plus were not
recorded at all — their base prices could not be isolated from a long
repeating add-on price sequence on the same page.

Database is now 208 tools across 49 categories.

### Tutoring center management software (2026-09-04)

Three vendors: TutorBird, My Music Staff, TutorCruncher. Seat axis is
"tutors" (1, 3, 5, 10, 25).

TutorBird and My Music Staff are evidently sister products from the
same vendor — identical page template, identical feature-heading set,
and an identical formula ("$16.95/month + $4.95 per each additional
tutor/teacher or staff member," base covering "yourself" as the first
seat) — but sold and priced separately for two different audiences
(tutors generally vs. music-lesson studios specifically), so both are
recorded as their own vendors. TutorCruncher's three tiers are all
labelled "Starting from" and differentiated mainly by payment-processing
rate rather than a stated tutor count, so all three are `compare: false`
starting figures. Teachworks was researched but excluded entirely: its
three tiers price by "student lessons" per month with explicitly
"Unlimited Tutors," a fundamentally different axis than this category's
per-tutor pricing.

Before landing on this category, daycare/childcare center management
software was researched and abandoned: Brightwheel and Procare are both
fully quote-gated ("Request pricing" forms, no self-serve figures
anywhere); Kangarootime's pricing page 404s; Famly prices "per child"
but the figure is computed entirely client-side by an interactive
range-slider calculator with no static number anywhere on the page (the
same treatment given to Cobot in the coworking category); Lillio
(formerly HiMama) publishes no price figures at all; Kinderlime has
been folded into Procare and now redirects straight into Procare's
quote-gated page. Six vendor attempts, zero usable self-serve prices —
past this site's abandonment threshold, so no category was shipped.

Database is now 211 tools across 50 categories.

### Mental health / therapy practice management software (2026-09-04)

Three vendors: SimplePractice, TherapyNotes, TheraNest (now sold by
Ensora Health). Seat axis is "clinicians" (1, 3, 5, 10, 25).

TherapyNotes has the cleanest formula: Solo is flat and capped at one
user ($69/mo), Group is a genuine base+per-seat formula ("$79/month for
the first clinician, $50/mo per additional clinician, free non-clinical
staff"); Enterprise (20+ users) uses the identical formula and only adds
an account manager, so it isn't modeled as a separate tier. TheraNest is
purely per-seat with no base fee across all three tiers (Essentials $29,
Advanced $59, Premier $89, each "/therapist/mo"). SimplePractice's
headline prices are a time-limited "50% off 3 months" promotion; the
standing prices ($49/$79/$99) were recovered from the page's own
struck-through reference prices instead, per this site's policy against
publishing promotional prices as the standing rate — but all three
tiers are solo-practitioner plans capped at one clinician, so
SimplePractice has no priced tier beyond a single seat in this table. A
$173/mo figure tied to its group-practice content was recorded only as
a Finding, since its exact per-clinician formula wasn't confirmed.

Before landing on this category, pest control business management
software was researched and abandoned: Fieldwork and Briostack's
pricing pages are unreachable (404/403), PestPac and FieldRoutes are
enterprise quote-based (commonly $125-200+ per user per month per
public reporting), and GorillaDesk — while self-serve priced — turned
out to be a generic multi-industry field-service tool (pest control,
lawn care, cleaning, contracting all served by the same product), which
would duplicate the site's existing `field_service_management` category
rather than add a genuinely distinct one.

Database is now 214 tools across 51 categories.

### Physical therapy / allied health practice management software (2026-09-04)

Three vendors: Jane App, Cliniko, ClinicSense. Seat axis is
"practitioners" (1, 3, 5, 10, 25).

Cliniko is the standout: a single unified plan priced entirely by a
genuine, complete step table by practitioner-count range ($45/mo for 1
practitioner up through $395/mo for 26-200), recovered in full as
static text — not a "starting at" figure. Jane App has a clean
base+per-seat formula across three tiers (Balance solo-only at $54/mo;
Practice $79/mo + $35/mo per additional full-time practitioner; Thrive
$99/mo + $40/mo per additional full-time practitioner). ClinicSense
states an explicit "Additional practitioners: $20/mo" rate on its
Standard tier, but its Premium tier — despite being marketed "for
clinics & wellness centers" — has no per-practitioner rate confirmed in
static text, so it's recorded capped at one practitioner like Lite
rather than guessed. WebPT was researched but is fully quote-gated (only
per-claim add-on fees are published; base tier prices are not).

Database is now 217 tools across 52 categories.

### Accounting firm practice management software (2026-09-04)

Three vendors: Karbon, Financial Cents, Canopy. Seat axis is "team
members" (1, 3, 5, 10, 25). This is workflow/practice-management
software for accounting and bookkeeping firms themselves — client
management, task tracking, document requests — distinct from this
site's existing `accounting` category, which covers general
small-business accounting software (QuickBooks, Xero, FreshBooks, Zoho
Books).

All three price purely per-user, annual primary / monthly secondary,
with no separate base fee: Karbon Team $59/user/mo (Business
$89/user/mo, min 4 users for monthly billing), Financial Cents Team
$49/user/mo (Solo is a single-user-only flat $19/mo, Scale $69/user/mo),
Canopy Standard $74/user/mo (Plus $109, Premium $149; the paired
monthly-billing rates were recovered from the same raw dollar-array
scan as the annual figures). Financial Cents' Team tier undercuts both
competitors at every seat count in this table.

Database is now 220 tools across 53 categories.

### Medical spa management software (2026-09-04)

Three vendors: Aesthetic Record, Pabau, Vagaro. Seat axis is
"providers" (1, 3, 5, 10, 25).

Aesthetic Record is a clean, genuine per-user rate with no base fee
(Essentials $15/user/mo, Accelerator $19/user/mo) plus a one-time $399
onboarding fee on both tiers (not modeled as recurring). Pabau and
Vagaro both price by team size / bookable-calendar count through an
interactive selector whose scaled figures are set by client-side
JavaScript; only the 1-seat starting rate rendered as static text for
either (Pabau's $62/mo confirmed via the page's own meta description
rather than the rendered pricing card itself, since the actual tier
grid requires a region selection to render; Vagaro's $30/mo standing
rate, with a $23.99 six-month promotional rate not used per this
site's policy). Vagaro is a multi-vertical salon/spa/fitness platform,
not medspa-specific, but explicitly serves med spas as one of its
named business types.

Before landing on this category, three other categories were
researched and abandoned this session: towing/roadside dispatch
software (only Towbook and Relay Tow had self-serve pricing; Beacon/
Dispatch Anywhere, TOPS, and TowSoft are all quote-gated or unpublished
— below this site's 3-vendor threshold), veterinary clinic management
software (only Provet had a confirmed formula; Digitail, Vetspire, and
Shepherd are quote-gated, and Hippo Manager's domain now redirects to
unrelated spam content), and chiropractic practice management software
(only ChiroSpring had confirmed pricing; ChiroTouch and PayDC are
quote-gated, and Genesis/ClinicMind prices per-visit rather than
per-provider, an axis mismatch with the rest of the category).

Database is now 223 tools across 54 categories.

### Nutrition / dietitian coaching practice management software (2026-09-04)

Three vendors: Healthie, Practice Better, Cronometer Pro. Seat axis is
"practitioners" (1, 3, 5, 10, 25).

Healthie and Practice Better both follow this site's solo-plus-group
pattern: single-practitioner tiers capped at one seat (Healthie's
Core/Essentials/Plus differ only by active-client cap — 10/250/
unlimited — at $18/$45/$115 per month annual; Practice Better's
Starter/Professional/Plus differ the same way at $25/$62/$89 annual),
plus a genuine multi-practitioner tier with a real base-plus-per-seat
formula (Healthie's Group at $135/mo for the first clinician + $50/mo
per additional; Practice Better's Team at $155/mo for 2 included
practitioners + $50/mo per additional, capped at 200). Both record
annual as the primary rate (headlined as the discounted option) with
monthly recorded separately. Cronometer Pro is single-practitioner
only ($39.99/mo) with no team plan below its quote-gated Enterprise
tier; its $2.50/mo-per-additional-client scaling is a client-count
axis, not a practitioner-count one, so only the base price is modeled
and the client scaling is recorded as a Finding instead.

Nutrium was researched but excluded: its pricing page renders three
currencies (BRL, EUR, USD) into the same DOM elements simultaneously,
producing genuinely garbled, self-contradictory price text (duplicate
"Total" blocks with mismatched symbol/number pairs) that could not be
confidently resolved to a single USD figure even after three fetch
attempts with different anchors and locale parameters.

Database is now 226 tools across 55 categories.

### Life & business coaching practice management software (2026-09-04)

Three vendors: Paperbell, CoachAccountable, Satori. Unlike this site's other
practice-management categories, coaching tools price by active-client
count rather than by number of practitioners on the team (CoachAccountable
explicitly includes "unlimited coach and administrator accounts at no
extra cost"), so this category's axis is "active clients" (10, 25, 50,
100, 250) rather than practitioners.

Paperbell is a single flat-rate plan with unlimited clients that does not
scale at all ($47.50/mo annual, $57/mo monthly). CoachAccountable has a
genuine, granular step table by active-client count running from 2 clients
at $20/mo up to 1,000 clients at $4,000/mo. Satori tiers by an active-client
cap per plan (Essentials 10 clients at $33/mo, Pro 50 clients at $49/mo,
Leader 150 clients at $124/mo); its billing-period toggle defaults to
annual per the page's own server-rendered "current" class on that tab, so
those figures are recorded as annual with no separate monthly rate
captured (the monthly figures render client-side via Alpine.js and weren't
present in static text).

Before landing on this category, two others were researched and abandoned
this session: insurance agency management software (only NowCerts had a
genuine self-serve base-plus-per-seat formula across seven vendors
attempted; Jenesis, HawkSoft, EZLynx, AgencyMatrix, AgencyBloc, and
Insureio are all quote-gated, unreachable, or redirect elsewhere — well
below this site's 3-vendor threshold) and moving company software (only
SmartMoving and FrontRunner Professional were found, both fully
quote-gated with no price shown at all).

Database is now 229 tools across 56 categories.

### Home inspection business management software (2026-09-04)

Three vendors: Spectora, Palmtech, Home Inspector Pro. Seat axis is
"inspectors" (1, 3, 5, 10, 25).

Spectora has a genuine base-plus-per-seat formula: the base subscription
includes one inspector, with additional inspectors billed per-seat
(annual $1090/yr base + $999/yr per additional inspector; monthly
$109/mo base + $99/mo per additional). Palmtech is a pure per-user rate
with no base fee at all and no feature gating across pricing models
($500/user/yr annual, $50/user/mo monthly). Home Inspector Pro publishes
a single flat $89/mo rate with no per-additional-inspector price
disclosed in static text — despite listing "Collaborative team
inspections" as a feature — so it is recorded as a single-inspector rate
rather than assumed to scale with team size; its page also advertises
"Annual discounts available" without stating the discounted figure.

Inspection Support Network was researched but excluded: it prices by
inspection volume processed per month ($725/inspection for the first 50,
stepping down at higher volumes) rather than by inspector count, an axis
mismatch with the rest of this category.

Database is now 232 tools across 57 categories.

### Notary & signing business management software (2026-09-04)

Three vendors: CloseWise, NotaryAssist, NotaryGadget. Seat axis is
"notaries" (1, 3, 5, 10, 25).

CloseWise sells two tracks from one pricing page: solo-notary plans (Pro
$15/mo, Pro+ $40/mo, both capped at one seat) and signing-service/title-
company plans that scale by a flat rate good for a team-member cap rather
than a genuine per-seat increment (Starter $20/mo for up to 5 team
members, Professional $100/mo for up to 10; each also carries a per-order
fee not modeled here). NotaryAssist and NotaryGadget are both
single-notary tools with no team plan disclosed — NotaryAssist at
$7.92/mo annual ($8.99/mo monthly), NotaryGadget at $11.95/mo monthly
only (its annual price is rendered as an image rather than text and
could not be read).

Two other categories were researched and abandoned this session before
landing on this one: real estate appraisal software (a la mode/ACI,
Bradford ClickForms, and other major players all returned broken or
quote-gated pricing pages) and driving school management software (most
candidates surfaced by search either don't resolve to a real domain or
price per-student rather than per-seat, an axis mismatch).

Database is now 235 tools across 58 categories.

### Private investigation agency management software (2026-09-04)

Three vendors: Trackops, CROSStrax, Case Jacket. Seat axis is
"investigators" (1, 3, 5, 10, 25).

Trackops has a genuine base-plus-per-seat formula on every tier: each
plan includes 2 Full Access Staff, with additional Full Access staff
billed per-seat at a rate that rises with tier ($99/mo + $39/additional
on Basic, up to $199/mo + $59/additional on Premium); "Unlimited Limited
Access Staff" (view-only) don't count toward the seat total. CROSStrax
and Case Jacket both price flat tiers capped at a stated investigator/user
count rather than a genuine per-seat increment — CROSStrax at $35/mo for
2 investigators up to $105/mo for 10 (Elite and Enterprise tiers exist
but their figures weren't captured in this fetch), Case Jacket at $40/mo
for 5 users up to $250/mo for 50 (its free Basic tier, capped at 2 users,
is excluded per this site's $0-tier policy).

This category emerged from research originally aimed at process-serving
business management software, which was abandoned: ServeManager and
Mighty Process Server both price by monthly job volume rather than by
server/seat count (ServeManager explicitly offers "unlimited users and
devices"), an axis mismatch with the rest of this site, and Process
Server's Toolbox is quote-gated. CROSStrax and Case Jacket, encountered
during that research, turned out to be genuine per-investigator private
investigation tools instead, which along with Trackops became this
category.

Database is now 238 tools across 59 categories.

### Bail bonds agency management software (2026-09-04)

Three vendors: Captira, Bailtec, BailBooks. Seat axis is "agents"
(1, 3, 5, 10, 25).

Captira is a single flat-rate plan with "Unlimited Agents" tracked (two
user logins included) that does not scale by agent count at all —
$99/mo, recorded over its "$1 first month" and "$65 small agency" promos
per this site's policy against publishing promotional prices as the
standing rate. Bailtec and BailBooks both price flat tiers capped at a
stated agent/user count rather than a genuine per-seat increment.
Bailtec scales by user-account cap (Standard 1 user at $80/mo annual,
Pro 5 users at $94/mo, Enterprise 10 users at $118/mo, each also
available month-to-month at a ~11-13% premium). BailBooks scales by
licensed-agent cap paired with a monthly bond-volume cap, with unlimited
free user accounts on every tier (Copper 1 agent at $55/mo, Bronze 2
agents at $65/mo, Silver 4 agents at $80/mo; Gold and Premium tiers exist
but weren't captured in this fetch).

Database is now 241 tools across 60 categories.

### Electronics/computer repair shop management software (2026-09-05)

Three vendors: RepairShopr, RepairDesk, Orderry. Seat axis is
"technicians" (1, 3, 5, 10, 25).

RepairShopr and RepairDesk both price flat tiers capped at a stated
user-account count rather than a genuine per-seat increment. RepairShopr
scales 1 → 10 → 10 users across Starter/Repair Shop/Big Chain ($59.99 →
$129.99 → $139.99/mo annual; Big Chain adds a 2+ locations requirement
rather than more seats), and RepairDesk scales 5 → 8 users across
Essential/Growth ($79 → $119/mo annual; its top Advanced tier is
unlimited-user but quote-gated and excluded). Orderry has a genuine
base-plus-per-seat formula on its Startup and Business tiers (3 employees
included, additional billed per-seat up to a stated cap — $69/mo +
$6/additional up to 15 on Startup, $99/mo + $9/additional up to 150 on
Business), plus a flat two-employee Hobby tier at $39/mo with no
disclosed overage rate. Orderry is a multi-industry field-service
platform rather than repair-shop-exclusive, but it explicitly names
"Electronics Repair Shop Software" among its solutions.

Two other categories were researched and abandoned this session before
landing on this one: debt collection agency management software (only
Collect!/Comtech Systems had genuine self-serve base-plus-per-seat
pricing across six vendors attempted — Debtrak, Lariat, Simplicity,
DebtView, and Case Master Pro are all quote-gated or unverifiable from
the vendor's own page) and funeral home management software (Halcyon
publishes no dollar figure at all despite third-party estimates
claiming one, and Osiris's pricing page is blocked by a bot-challenge
captcha — Passare is separately confirmed quote-gated).

Database is now 244 tools across 61 categories.

### Pool service business management software (2026-09-05)

Three vendors: Pool Brain, Pool Office Manager, Paythepoolman — all three
with a genuine base-plus-per-seat formula. Seat axis is "technicians"
(1, 3, 5, 10, 25).

Pool Brain: $50/mo covers unlimited office users, +$65/mo per active
field technician with no included seats. Pool Office Manager: $125/mo
for the first user, +$25/mo per additional user. Paythepoolman: $50/mo
base +$15/mo per technician from the first seat, recorded over its
"80% OFF for 3 Months" promo per this site's policy against publishing
promotional prices as the standing rate. Skimmer was researched but
excluded: it explicitly offers "Unlimited Technicians & Admins" and
prices purely by serviced-pool-location count, an axis mismatch with
the rest of this category.

Database is now 247 tools across 62 categories.

### Event/party equipment rental business management software (2026-09-05)

Three vendors: Booqable, RentMy, Current RMS. Seat axis is "users"
(1, 3, 5, 10, 25).

RentMy and Current RMS both publish exact, unambiguous seat pricing:
RentMy's Nano is a flat $39/mo capped at 3 user accounts, Growth a flat
$199/mo with unlimited accounts (plus a $249 one-time setup fee on both,
Enterprise excluded as quote-gated). Current RMS sells one plan priced
$79/mo for the first user plus $49/mo per additional user, read straight
off its own pricing-slider DOM values. Booqable publishes whole-plan
price jumps (Start/Grow/Scale) and states the user-count *deltas* between
them ("5 extra users" for Grow over Start, "10 extra users" for Scale
over Grow) but never the absolute headcount included in Start itself;
Start's own copy ("for starters and solo operators") is read as a
single-seat baseline, the same convention already used for SingleOps
elsewhere in this database, giving inferred seat caps of 1/6/16.

Two vendors were researched and excluded for this category: HireHop
prices cleanly by user (a first-user rate plus a flat additional-user
rate) but only in GBP, with no USD price the site renders directly —
excluded from the cost table under this site's standing non-USD
treatment, the same one applied to Smoobu. EZRentOut publishes headline
prices ($399/mo, $499/mo, custom Enterprise) but its per-tier included-
user counts are rendered in a way that repeated fetch attempts could not
extract; Goodshuffle Pro's pricing page blocks fetches outright with a
Cloudflare 403. Both are left out rather than guessed at.

Database is now 250 tools across 63 categories.

### Moving company management software (2026-09-05)

Three vendors: Elromco, MoveitPro+, QuoteIQ. Seat axis is "office users"
(1, 3, 5, 10, 25).

Elromco is a flat monthly fee capped by office-user count — Professional
$289/mo for 3 office users, Enterprise $399/mo for unlimited office users
(crew members are unlimited on both, since they don't need office seats).
MoveitPro+ sells one uncapped feature set priced by a genuine base-plus-
per-office-user formula, with the base rate set by commitment length
rather than plan name: the 12-month agreement ($359/mo prepaid, 2 users
included, +$80/mo per additional office user) is recorded as the primary
rate, since 24-month and 36-month agreements unlock cheaper per-user
rates this site's schema has no billing period to name (only "annual" and
"biennial" exist) — those are recorded as a finding instead. QuoteIQ is a
horizontal field-service CRM, not a moving-specific product, but it
explicitly markets itself to movers via a dedicated "#1 CRM For Moving
Companies" landing page, the same "generic tool with a named solution"
exception used elsewhere in this database; its five tiers (Essentials
through Max) are flat fees capped by included-user count from 1 up to
unlimited.

Vonigo was researched and excluded: despite third-party aggregators
quoting per-user prices ($98–139/user/mo), vonigo.com has no live public
pricing page of its own — /pricing and /pricing/ both redirect to the
homepage — so no vendor-page provenance exists for those figures.

Database is now 253 tools across 64 categories.

### Pet grooming and boarding management software (2026-09-05)

Three vendors: Time To Pet, DaySmart Pet, MoeGo. Seat axis is "staff"
(1, 3, 5, 10, 25).

Time To Pet is a genuine base-plus-per-staff formula on its "Team" plan
($40/mo + $16/mo per staff member, charged from the first seat — its own
page even shows the worked example "$120/month for 5 staff"), but the
same platform also sells a flat, uncapped $79/mo "Facility" plan for
daycare/boarding operations with no staff count published at all; both
are recorded, since a boarding business large enough to make Facility
the better deal would simply buy Facility. DaySmart Pet is a flat fee
per plan capped by included-user count (1/3/3/6 across its four
publicly-priced tiers). MoeGo's cheapest "Basic" tier is genuinely capped
at 1 team member, but Growth and Ultimate both list unlimited team
members and differ only by features — mobile-grooming pricing is
recorded since a same-page "Grooming salon" tab (reportedly pricier)
could not be switched to and confirmed in this fetch.

Junk removal business management software was researched as a separate
category and abandoned: the only vendors with public per-seat pricing
and a dedicated junk-removal marketing page (Jobber, Housecall Pro,
Workiz) are already fully represented in this database under
`field_service_management` with identical pricing, so a second category
would just duplicate those records rather than add anything a junk
removal buyer couldn't already see there.

Database is now 256 tools across 65 categories.

### A round of dead ends, and one real addition (2026-09-05)

Five candidate categories were researched this round and none of them
shipped as new categories — worth recording so the next pass doesn't
repeat the same dead ends:

- **Veterinary practice management software**: all three researched
  vendors failed direct verification. Shepherd's own `/pricing` page
  404s and its homepage carries no pricing at all — third-party-quoted
  figures for it have no vendor-page source. ezyVet's own page states a
  single flat "starting at $260.50 per month... whether you're a single
  veterinarian practice or you have hundreds of staff members," i.e.
  explicitly not scaled by team size, with "additional pricing details
  available upon request" for anything else. DaySmart Vet's page states
  only a vague "starting at $123/month" headline; its actual tier
  pricing routes through a "Contact our team to discuss custom pricing"
  form, not a published table.
- **Driving school management software**: two vendors check out cleanly
  (Drive Scout — $50/user/month, 5-user minimum, no tiers; Software for
  Driving School — Solo $49/mo/1 user, Team $79/mo/up to 10 users,
  Growth $399/mo/unlimited users/25 locations) but no third vendor with
  a genuine per-seat axis could be confirmed; the rest of the market is
  per-student, flat-rate, or unpublished.
- **Optometry / eye-care practice management software**: dominated by
  quote-gated pricing. RevolutionEHR's page shows flat feature tiers
  (Core/Advanced/Premium) with no stated provider-count scaling. Crystal
  Practice Management's own page gates the base price behind "Contact
  Us for Pricing" on every tier — only the marginal "additional
  doctor(s)" rate is public, which isn't enough to price a 1-doctor
  practice.
- **Junk removal business management software**: the only vendors with
  public per-seat pricing and dedicated niche marketing (Jobber,
  Housecall Pro, Workiz) are already in this database under
  `field_service_management` with identical pricing — a second category
  would just duplicate those records.
- **A dedicated "massage therapy / wellness" category**: two of the
  three vendors found with clean pricing (Jane App, ClinicSense) turned
  out to already be in this database under
  `physical_therapy_allied_health_practice_management`. Rather than ship
  a mostly-duplicate category, the one genuinely new vendor found —
  **Ruana** — was added to that existing category instead: Solo $35.99/mo
  (1 practitioner), Professional $55.99/mo + $19.99/mo per practitioner
  (base read as including 1, the same "assume 1" convention used for
  SingleOps and Booqable).

Database is now 257 tools across 65 categories.

### Commercial cleaning / janitorial contractor management software (2026-09-05)

Three vendors: Chronotek Pro, Otuvy, CleanGuru. Seat axis is "cleaners"
(1, 3, 5, 10, 25). Distinct from the existing `cleaning_management`
category, which covers residential maid-service booking apps (Launch27,
Zenbooker, ZenMaid) rather than commercial building-services
contractors.

Chronotek Pro is a genuine base-plus-per-employee formula with no tiers
at all ("no tiers, just options"): $19/mo base + $6/mo per employee,
explicitly marketed to janitorial contractors alongside other
mobile-workforce verticals. Otuvy (formerly CleanTelligent) sells a
quality-management/inspection suite: QM Inspect ($150/mo, 5 users) and
QM Pro ($250/mo, same 5-user cap, adds work orders) are flat tiers
capped by user count; a separate "Otuvy Frontline" product on the same
pricing page has a genuine base-plus-per-user formula ($50/mo + $7/mo
per user). CleanGuru is a bidding/estimating platform for cleaning
contractors with three tiers ($79/$129/$159/mo) that include 10
cleaners each and charge $5/mo per additional cleaner beyond that per
its own "Additional cleaners, just $5/mo!" note.

Database is now 260 tools across 66 categories.

### Handyman contractor business management software (2026-09-05)

Three vendors: Werx, Contractor+, Fieldd. Seat axis is "users"
(1, 3, 5, 10, 25). QuoteIQ, another strong candidate, was skipped here
since it's already in this database under `moving_company_management`
with identical pricing.

Werx's three tiers differ only by active-project count, with every
feature on every plan; team size is a separate flat per-user add-on
($6/mo standard, $4/mo time-only) layered on top, with each tier's base
read as including 1 user (Essential is explicitly "for solo
contractors"). Contractor+ defaults its pricing page to an annual-billed
view ($29/mo PRO, $58/mo PRO TEAM with the first 2 users included and
$20/mo per additional user beyond that) while its own meta description
states the higher standing monthly rates ($49/$98); both are recorded
per this site's annual-primary convention. Fieldd is a flat fee per
plan capped by included-user count (10/30/30 across its three tiers).
All three maintain a dedicated handyman-software landing page.

Database is now 263 tools across 67 categories.

### Lawn treatment / chemical applicator software (2026-09-05, abandoned)

Researched as a category distinct from the existing `landscaping_management`
(general mowing/landscape crews): specifically lawn chemical treatment and
irrigation contractor software. Two purpose-built vendors check out
cleanly — Spraye (spraye.io/pricing/): Starter $79.99/mo/1 user/100
properties, Essentials $169.99/mo/2 users/1,000 properties/+$39.99 per
additional user, Premium $399.99/mo/4 users/5,000 properties/+$49.99 per
additional user, Elite $999.99/mo/8 users/10,000 properties/+$59.99 per
additional user; and TurfHop (turfhop.com/page/pricing, explicitly
"perfect for biological lawn care companies and chemical applicators"):
Truck $49/mo/2 users, Office $79/mo/up to 4 users, Headquarters $129/mo/up
to 10 users (all with unlimited employees beyond the counted "users").

No third vendor could be confirmed: LawnPro's pricing page returns an
HTTP 403 from an AWS WAF on every fetch attempt; HindSite/FieldCentral
has no discoverable dedicated pricing-page URL despite extensive search
(its own site's "Pricing" nav link redirects to the homepage); Service
Autopilot has real public tiers ($49/$199/$499/mo) but is a generic
multi-vertical field-service tool (lawn care is one of seven listed
industries) whose lower two tiers don't state a seat cap at all — too
close to `landscaping_management`'s existing coverage and too ambiguous
on the seat axis to use. Abandoned per this site's 3-vendor minimum;
Spraye and TurfHop are recorded here in case a third vendor surfaces
later.

Database is unchanged at 263 tools across 67 categories.

### Dumpster/roll-off rental software (2026-09-05, abandoned — wrong axis)

Researched as a category distinct from `event_rental_business_management`
and from the abandoned junk-removal attempt. This one is a structural
dead end rather than a vendor-availability one: the whole dumpster/
roll-off rental software market has converged on pricing axes other
than team size. Vendors checked with genuinely public pricing — Bin
Boss (flat $99/mo, unlimited admin users, +$50/mo per driver beyond 2),
DSQ Hauler (flat $99/mo, unlimited users), iCans (flat $99/mo per
business, unlimited users), Dumpster Rental Systems/Randall Data
Systems (tiered by container count: $79.95/$195.95/$279.95/mo), HaulHQ
($0/mo base + $1.50 per completed job) — are all flat-fee, per-driver,
per-container, or per-job, never per-seat. The larger players (Rubicon,
Trux, WasteWORKS, TrashLab, CurbWaste, ServiceCore, Docket, CRO
Software) are entirely quote-gated. No purpose-built dumpster-rental
vendor with a genuine per-seat/user axis exists to build this category
around; QuoteIQ (already elsewhere in this database under
`moving_company_management`) is the only per-seat-priced tool that even
markets a dumpster-rental landing page, and it's a generic multi-trade
CRM, not purpose-built software.

Database is unchanged at 263 tools across 67 categories.

### Tree service / arborist business management software (2026-09-05)

Three vendors, all with genuine tree-service focus and published
per-seat pricing: ArboristDesk, Treezi, ArborNote. Seat axis is "users"
(1, 3, 5, 10, 25). Vendors already in this database were excluded
outright rather than re-checked for a tree-service angle: SingleOps
(landscaping_management), Service Autopilot, Aspire, Jobber, Housecall
Pro, ServiceTitan, QuoteIQ, Werx, Contractor+, Fieldd.

ArboristDesk publishes a clean base-plus-per-seat structure across all
three tiers (Starter $79/mo base, Growth $149/mo, Pro $249/mo — each
with 1 included user and a flat per-additional-user add-on of
$12/$15/$18 respectively), plus explicit seat caps on the upper two
tiers (Growth 5 users, Pro 15 users) and a stated 12-month price lock.
Treezi has no base fee at all — a single plan priced purely at
$49.99/user/month ($41.99/mo billed annually) — capped at "9 crews or
more" (a crew, not user, threshold, so no max_seats is recorded).
ArborNote's pricing page is an interactive calculator; its own
client-side JS config (`{ base: 240, additional: 130 }` for Essential,
`{ base: 350, additional: 150 }` for Enterprise) gave a clean base/seat
read despite the page not printing a static price table, and its
"ArborNote Works" mobile crew app is a separate $75/mo-per-user add-on
recorded as a non-`compare`, non-`standalone` tier. ArborNote's 10%
annual-billing discount is mentioned but never resolves to a static
number without interacting with the page's toggle, so only its monthly
pricing is recorded, with a finding noting the gap.

Database is now 266 tools across 68 categories.

## Rendered fetches (script-rendered pricing pages)

CRM and helpdesk vendors render prices client-side, and the build container
cannot reach vendor sites directly (egress policy). The working path is
DataForSEO's `on_page/instant_pages` with `enable_browser_rendering: true`
and a `custom_js` that returns `document.body.innerText`; the response's
`custom_js_response.text` is the rendered page. `tools/save_render.py <slug>
<result.json>` writes it to `data/raw/<slug>.<date>.txt` and prints the
price and term lines. Records built this way cite `method: live_fetch` with
a "browser-rendered" note.

`tools/render_fetch.py` does the same with local Playwright/Chromium for
machines that can reach vendor sites; it does not work inside the build
container.

Results on 2026-09-03: Pipedrive, Freshsales, Help Scout, Docusign, SignNow,
Quo (formerly OpenPhone), RingCentral, Grasshopper, monday.com, ClickUp,
Trello, Basecamp, LiveChat, Crisp, Olark, Intercom, Calendly, Acuity,
YouCanBookMe, Cal.com, SavvyCal, Bitwarden, 1Password, Dashlane, Keeper, Webflow
and Duda rendered with full prices (Intercom's odometer seat prices came from the widgets' `aria-label`
attributes); Asana and Tidio rendered USD only
on a US-side gateway (the German gateway serves EUR); NordPass, Squarespace, Wix and Framer never landed on one, so those
records carry EUR findings and no tiers. HubSpot's pages render without price figures (loaded after render),
and Dialpad's pricing page carries no plan prices at all. Zendesk and
Nextiva answer the rendering browser with a 403, PandaDoc with a 429.
Zoho geo-routes the German gateway to EUR pricing and Jotform localises
its currency the same way. Dropbox Sign's pricing URL 404s. A toggle's
active state can be read in the same `custom_js` (Help Scout's annual
button carries `is-active`, Quo's yearly tab `aria-selected`), which is
how billing periods are labelled. Odometer-style price widgets
(Grasshopper) leave placeholder digits in `innerText`; resolve them from
the annual total or the page's JSON-LD.

The sandbox that runs `custom_js` is not a full DOM: `createTreeWalker`
and `element.style` are unavailable, so keep scripts to `querySelector`,
`innerText`, attributes and string work.

## Deploy

`wrangler.toml` configures Cloudflare Workers Static Assets. Connect the
repo in the Cloudflare dashboard (Workers & Pages → Create → Import a
repository; project name `stackproof`), build command
`pip install -r requirements.txt && python build.py`, deploy command
`npx wrangler deploy`. Set `SITE_ORIGIN` to the production URL so canonicals
and the sitemap are absolute. Every push to `main` redeploys.

## Adding a vendor

1. Fetch the pricing page and the terms. Record the formula, not the headline.
2. Compute nothing by hand — `cost_at()` derives seat costs from the formula.
3. Write each notable fact as a `Finding` with its own provenance.
4. `not_stated` is a publishable result for any clause topic.
5. Run the tests. If a finding has no number, it will not build.

