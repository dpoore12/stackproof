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

