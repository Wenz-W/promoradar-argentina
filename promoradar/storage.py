"""Persistência auditável em JSONL por mês, sem banco pago."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

def append_jsonl(path: Path, items: list[dict], dedupe_field: str | None = None) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = set()
    if dedupe_field and path.exists():
        for item in read_jsonl(path):
            value = item.get(dedupe_field)
            if value is not None:
                old.add(str(value))
    added = 0
    with path.open("a", encoding="utf-8") as f:
        for item in items:
            key = str(item.get(dedupe_field)) if dedupe_field else None
            if dedupe_field and key in old:
                continue
            f.write(json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
            added += 1
            if dedupe_field:
                old.add(key)
    return added

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def read_series(kind: str, mode: str = "real") -> list[dict]:
    root = DATA / mode
    return [item for path in sorted(root.glob(f"{kind}-*.jsonl")) for item in read_jsonl(path)]

def store_run(mode: str, run: dict, observations: list[dict], offers: list[dict]) -> dict:
    ym = run["started_at"][:7]
    root = DATA / mode
    obs_added = append_jsonl(root / f"observations-{ym}.jsonl", observations, "observation_id")
    offers_added = append_jsonl(root / f"offers-{ym}.jsonl", offers, "offer_id")
    append_jsonl(root / f"runs-{ym}.jsonl", [run], "run_id")
    return {"observations_added": obs_added, "offers_added": offers_added}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
