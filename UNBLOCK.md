# What I need from Dan to take StackProof live

Everything below is something I cannot do because it requires a legal person,
a card, or an account in your name. Nothing else is blocked. In order of how
much each one unlocks:

## 1. A domain (unlocks: a real address; optional to go live)

Pick one and buy it at any registrar; point DNS at Cloudflare. I'll set
`ORIGIN` in `build.py` and the sitemap/canonicals go absolute.

Shortlist, all checked for meaning not availability — verify at purchase:

- `stackproof.com` / `.co` / `.io` — matches the existing spec and brand
- `measuredstack.com`
- `receiptsforsoftware.com` (long, but says exactly what it is)
- `bought.software` (if the TLD is open to you)

## 2. Connect the repo on Cloudflare (unlocks: the site is live today — no domain needed)

Your Cloudflare account is attached to this session and has no Workers yet.
`wrangler.toml` is in the repo, so this is import-and-go:

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Import a repository**.
2. Pick `dpoore12/stackproof`. Project name must be **`stackproof`** (it must match `wrangler.toml`).
3. Build command: `pip install -r requirements.txt && python build.py`
   Deploy command: `npx wrangler deploy`
4. Save and deploy. You get a free `stackproof.<account>.workers.dev` URL immediately.
5. Add a variable `SITE_ORIGIN` = that URL (or your domain once you have one) and redeploy, so canonicals and the sitemap are absolute.

Every push to `main` redeploys. A custom domain can be attached later under the Worker's **Settings → Domains & Routes**; it is not required to go live.

## 3. Software accounts (unlocks: `verified_on_account`, the figures we stand behind)

Budget ~$500–800/month, staggered. First three, in this order:

| Vendor | Why first | Cost to verify |
|---|---|---|
| **Gusto** | Blocks bots (HTTP 403); currently our weakest record and the biggest brand | free until first payroll; needs at least one real person on payroll — this one needs your entity |
| **OnPay** | Strongest first-hand record already; one month free | $0 for month one |
| **Patriot** | Base fee not machine-extractable; 30 days free | $0 for month one |

Payroll specifically needs a real employee and real tax filings. If you don't
want to run payroll through three providers, we verify pricing/terms/support
on accounts without running payroll, and label the payroll-run findings as
not measured. That's honest and still far ahead of anyone else.

## 4. Entity, tax, and payment details for affiliate applications (unlocks: revenue)

Impact and PartnerStack require a media-kit PDF with traffic data, so we
apply **after** the site has a few months of Search Console history — not
now. When we do, each application needs: legal entity name, EIN/tax form,
payout bank or PayPal, and a business address. Have these ready; I'll
prepare the media kit and the applications, you submit them.

Vendor-direct programs to target first (all recurring, all in our categories):
Gusto (partner program), OnPay (partner program, revenue share visible on
their site), Kit, GetResponse, Pipedrive, FreshBooks, Xero.

## 5. Google Search Console access (unlocks: measuring what actually ranks and gets cited)

Add the domain once it's live and give me access. Without it I'm inferring
positions from third-party crawls.

## Not needed from you

Content, testing, page generation, comparison tables, methodology, CI,
schema markup, the AI-disclosure language, and the FTC compliance shape are
all in the repo and run without you.
