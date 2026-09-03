"""Fetch a pricing page in a real browser and save its rendered text.

Usage: python tools/render_fetch.py <slug> <url> [--wait 8000]

Writes data/raw/<slug>.<date>.txt with the visible text of the page after
JavaScript has run, plus a small header with the URL, fetch time and final
URL. Records built from this output cite method: live_fetch with a note
that the page was browser-rendered.
"""
import sys, datetime, pathlib, argparse
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug"); ap.add_argument("url")
    ap.add_argument("--wait", type=int, default=8000)
    a = ap.parse_args()
    today = datetime.date.today().isoformat()
    out = pathlib.Path("data/raw") / f"{a.slug}.{today}.txt"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium",
                              args=["--no-sandbox"])
        ctx = b.new_context(user_agent=UA, locale="en-US",
                            timezone_id="America/New_York",
                            viewport={"width": 1366, "height": 900},
                            geolocation={"latitude": 40.71, "longitude": -74.0},
                            permissions=["geolocation"])
        pg = ctx.new_page()
        try:
            pg.goto(a.url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print("goto error:", e)
        pg.wait_for_timeout(a.wait)
        # try to click a monthly/annual toggle into view is out of scope; just capture
        text = pg.evaluate("() => document.body ? document.body.innerText : ''")
        final = pg.url; title = pg.title()
        b.close()
    out.write_text(f"URL: {a.url}\nFINAL: {final}\nTITLE: {title}\nFETCHED: {datetime.datetime.utcnow().isoformat()}Z\n---\n{text}")
    print(f"{a.slug}: {len(text)} chars -> {out}  final={final}")

if __name__ == "__main__":
    main()
