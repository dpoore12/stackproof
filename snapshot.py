"""Record today's prices into the time series.

Run after records change (`python snapshot.py`). Writes
`data/history/YYYY-MM-DD.json`, one file per day, containing every tier and
fee as recorded on that day. `build.py` diffs consecutive snapshots into the
/changes/ page.

This is the dataset that distinguishes a record from a listing: "what Gusto
charges" is on Gusto's site; "what Gusto has charged, by date" is not.
Snapshots are committed to the repository — they are the product.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import yaml

from schema import Tool

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "tools"
HISTORY = ROOT / "data" / "history"


def snapshot_of(tools: list[Tool]) -> dict:
    out: dict = {}
    for t in tools:
        out[t.slug] = {
            "vendor": t.vendor,
            "product": t.product,
            "category": t.category,
            "tiers": [
                {
                    "plan": ti.plan,
                    "base_monthly_usd": ti.base_monthly_usd,
                    "per_seat_monthly_usd": ti.per_seat_monthly_usd,
                    "steps": [s.model_dump() for s in ti.steps] if ti.steps else None,
                    "billing": ti.billing,
                    "max_seats": ti.max_seats,
                    "fetched_at": ti.provenance.fetched_at.isoformat(),
                    "source_url": ti.provenance.source_url,
                }
                for ti in t.tiers
            ],
            "fees": [
                {"name": f.name, "amount_usd": f.amount_usd, "unit": f.unit,
                 "fetched_at": f.provenance.fetched_at.isoformat()}
                for f in t.fees
            ],
        }
    return out


def take(today: date | None = None) -> Path:
    today = today or date.today()
    HISTORY.mkdir(parents=True, exist_ok=True)
    tools = [Tool.model_validate(yaml.safe_load(p.read_text())) for p in sorted(DATA.glob("*.yaml"))]
    path = HISTORY / f"{today.isoformat()}.json"
    path.write_text(json.dumps({"date": today.isoformat(), "tools": snapshot_of(tools)}, indent=1, sort_keys=True))
    return path


if __name__ == "__main__":
    p = take()
    print(f"snapshot written: {p.relative_to(ROOT)}")
    sys.exit(0)
