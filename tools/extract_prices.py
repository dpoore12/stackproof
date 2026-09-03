"""Print the price/fee/term lines from a saved DataForSEO content_parsing result.

Usage: python tools/extract_prices.py <saved.json> [<saved.json> ...]

Keeps the vendor page out of the model's context: only lines that look like a
price, a per-seat rate, a fee, a trial, or a contract term are printed, each
once, truncated. The full response stays on disk for provenance.
"""
import json, re, sys

PAT = re.compile(
    r"\$\s?\d|€\s?\d|£\s?\d|/mo\b|per month|per user|per seat|per employee|per worker|"
    r"per contact|subscribers?|contacts?\b.*\d|free (plan|trial|forever)|\d+ days? free|"
    r"cancel|refund|renew|annual|billed|contract|per additional|add-?on|unlimited",
    re.I,
)

def texts(o, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("text", "h_title") and isinstance(v, str):
                out.append(" ".join(v.split()))
            else:
                texts(v, out)
    elif isinstance(o, list):
        for x in o:
            texts(x, out)

for path in sys.argv[1:]:
    body = open(path).read()
    try:
        raw = json.loads(body)
    except json.JSONDecodeError:
        raw = None
    if isinstance(raw, list) and raw and isinstance(raw[0], dict) and "text" in raw[0]:
        d = json.loads(raw[0]["text"])          # persisted-output wrapper
    elif isinstance(raw, dict):
        d = raw                                  # raw API JSON saved as text
    else:
        print(f"\n===== {path.rsplit('/',1)[-1]} =====\n(unparseable)"); continue
    items = d.get("items") or []
    print(f"\n===== {path.rsplit('/',1)[-1]} =====")
    if not items:
        print("(empty — page blocked or JS-only)")
        continue
    it = items[0]
    print("fetched:", it.get("fetch_time"), "status:", it.get("status_code"))
    out = []; texts(it.get("page_content", {}), out)
    seen = set(); n = 0
    for t in out:
        if PAT.search(t) and t not in seen and 3 < len(t) < 240:
            seen.add(t); n += 1; print("-", t)
            if n >= 60: print("... (truncated at 60 lines)"); break
