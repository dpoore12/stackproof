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

Checked this directly (2026-09-04): the Cloudflare connector attached to
this session gives me account-resource *management* (D1, KV, R2, reading
Worker metadata) but no deploy action, and there's no API token stored in
this environment — so I cannot click the button myself. Two ways to
finish this; pick one.

### Option A — GitHub Actions (recommended; the workflow is already written)

`.github/workflows/deploy.yml` is in the repo and deploys on every push to
`main`. It just needs two values set on the `dpoore12/stackproof` repo:

1. Cloudflare dashboard → **My Profile → API Tokens → Create Token** →
   template "Edit Cloudflare Workers" (or a custom token with
   `Account.Workers Scripts:Edit`). Copy the token.
2. GitHub → repo **Settings → Secrets and variables → Actions**:
   - **Secrets** tab → New repository secret → name `CLOUDFLARE_API_TOKEN`, paste the token.
   - **Variables** tab → New repository variable → name `CLOUDFLARE_ACCOUNT_ID`, value from the Cloudflare dashboard's account home URL or the right sidebar of any zone page.
3. Push anything to `main` (or re-run the workflow from the Actions tab) — it deploys from there on, automatically, forever.

### Option B — Cloudflare dashboard import (no GitHub secret needed, more clicks)

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Import a repository**.
2. Pick `dpoore12/stackproof`. Project name must be **`stackproof`** (it must match `wrangler.toml`).
3. Build command: `pip install -r requirements.txt && python build.py`
   Deploy command: `npx wrangler deploy`
4. Save and deploy. You get a free `stackproof.<account>.workers.dev` URL immediately.

Either way: once you have a URL, set `SITE_ORIGIN` to it (a GitHub Actions
repository *variable* for Option A; a Cloudflare dashboard build variable
for Option B) and redeploy, so canonicals and the sitemap go absolute. A
custom domain can be attached later under the Worker's **Settings →
Domains & Routes**; it is not required to go live.

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

I can't complete these signups myself: every network and vendor-direct
program requires a legal entity/person, a tax form (W-9 for a US person or
business), and a bank or PayPal to pay out to — none of which I have or
can create. I can research the programs, draft the media kit, and fill in
every field of the application *except* those; you'd submit it (or paste
me the entity/tax/payout details and I'll fill the form text, but the
account creation and identity/bank verification steps need to happen as
you, not me).

Impact and PartnerStack require a media-kit PDF with traffic data, so we
apply **after** the site has a few months of Search Console history — not
now. When we do, each application needs: legal entity name, EIN/tax form,
payout bank or PayPal, and a business address. Have these ready; I'll
prepare the media kit and the applications, you submit them.

Vendor-direct programs to target first (all recurring, all in our categories):
Gusto (partner program), OnPay (partner program, revenue share visible on
their site), Kit, GetResponse, Pipedrive, FreshBooks, Xero.

## 5. Google Search Console access (unlocks: measuring what actually ranks and gets cited)

Checked (2026-09-04): I have Google Drive and Gmail connected to this
session, but no Search Console connector, so I don't have this today even
though other Google access looks connected. Also blocked on #2 regardless
— there's no live domain yet to add. Once the site is live: add the
domain/URL-prefix property in Search Console, then either add my
connected Google account as a user on that property (Settings → Users and
permissions → Add user) or, if a direct Search Console connector becomes
available for this session, connect that instead. Without it I'm inferring
positions from third-party crawls.

## Not needed from you

Content, testing, page generation, comparison tables, methodology, CI,
schema markup, the AI-disclosure language, and the FTC compliance shape are
all in the repo and run without you.
