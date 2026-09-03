"""Save the custom_js_response text from a persisted DataForSEO instant_pages result.
Usage: python tools/save_render.py <slug> <result.json>
Writes data/raw/<slug>.<date>.txt and prints lines that mention money/terms."""
import sys, json, re, datetime, pathlib
slug, path = sys.argv[1], sys.argv[2]
raw = json.load(open(path))
if isinstance(raw, list): raw = json.loads(raw[0]["text"])
item = raw["tasks"][0]["result"][0]["items"][0]
resp = item.get("custom_js_response") or {}
text = resp.get("text", "") if isinstance(resp, dict) else str(resp)
today = datetime.date.today().isoformat()
out = pathlib.Path("data/raw") / f"{slug}.{today}.txt"
out.write_text(f"URL: {item['url']}\nSTATUS: {item['status_code']}\nFETCHED: {item.get('fetch_time')}\nMETHOD: dataforseo instant_pages enable_browser_rendering + custom_js innerText\n---\n{text}")
print(f"{slug}: status {item['status_code']}, {len(text)} chars -> {out}")
pat = re.compile(r"(\$|€|£|/\s?(user|seat|agent|month|mo\b)|per (user|seat|agent|month)|billed|annual|monthly|trial|cancel|refund|export|minimum|add-on|addon)", re.I)
seen=set()
for ln in text.splitlines():
    s=ln.strip()
    if s and pat.search(s) and s not in seen and len(s)<220:
        seen.add(s); print("  |", s)
