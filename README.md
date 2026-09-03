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
build.py           renders site/ — tool pages, category compare, methodology
tests/             provenance rules + build invariants
site/              output (ignored; built in CI and deployed)
```

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
| `max_seats` | tier sold only up to N seats (a free plan capped at 10 employees). Larger teams get `—`, not an extrapolation. |
| `standalone: false` | an add-on priced on top of a plan. Shown in the table, never competes for "cheapest plan". |
| `billing: annual` | the recorded rate is the per-month figure when prepaid annually. Vendors headline this one; it is labelled. |
| `pricing_note` (tool-level) | why no cost is shown — "behind a script, not captured" is a different fact from "not published". |

Column headers come from `CATEGORY_SEAT_POINTS` in `schema.py`: payroll compares 1/5/10/25/50 people paid, email marketing compares 500–25,000 contacts.

## Fetching vendor pages

DataForSEO `on_page/content_parsing/live` returns the vendor page as
structured text. `tools/extract_prices.py <saved.json>` prints only the
lines that look like a price, fee, trial or term, so the page never has to be
read in full. Some vendors (Gusto, Kit) return HTTP 403 to fetches; some
(Brevo, Mailchimp, GetResponse, MailerLite) render amounts client-side. Both
cases are recorded as such with `pricing_note` — never filled from a third
party.

## Adding a vendor

1. Fetch the pricing page and the terms. Record the formula, not the headline.
2. Compute nothing by hand — `cost_at()` derives seat costs from the formula.
3. Write each notable fact as a `Finding` with its own provenance.
4. `not_stated` is a publishable result for any clause topic.
5. Run the tests. If a finding has no number, it will not build.

## Deploy

Cloudflare Pages, build command `pip install -r requirements.txt && python build.py`,
output directory `site`. Set `ORIGIN` in `build.py` to the production
origin so canonical URLs and the sitemap are absolute.
