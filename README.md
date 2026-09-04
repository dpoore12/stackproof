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

