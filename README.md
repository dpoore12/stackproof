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

