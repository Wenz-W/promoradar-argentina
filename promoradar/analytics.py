"""Regras auditáveis de queda de preços, sem descontos de vitrine."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median
import hashlib


def as_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def detect_offers(new_rows: list[dict], historical: list[dict], previous_offers: list[dict], settings: dict) -> list[dict]:
    by_listing = defaultdict(list)
    for row in historical:
        if row.get('data_mode') != 'real' and any(n.get('data_mode') == 'real' for n in new_rows):
            continue
        by_listing[row['listing_id']].append(row)
    past = defaultdict(list)
    for offer in previous_offers:
        past[offer['listing_id']].append(offer)

    threshold = float(settings.get('drop_threshold_pct', 15))
    min_days = int(settings.get('min_historical_days', 7))
    min_samples = int(settings.get('min_historical_samples', 7))
    window = int(settings.get('historical_window_days', 30))
    cooldown = float(settings.get('repost_cooldown_hours', 48))
    extra_drop = float(settings.get('extra_drop_for_repost_pct', 5))

    offers = []
    for row in new_rows:
        if row.get('stock_status') not in ('available','listed') or row.get('price_ars') is None:
            continue
        now = as_date(row['captured_at'])
        prev = [r for r in by_listing[row['listing_id']]
                if now - timedelta(days=window) <= as_date(r['captured_at']) < now
                and r.get('price_ars') is not None and r.get('stock_status') in ('available','listed')]
        if len(prev) < min_samples or len({as_date(p['captured_at']).date() for p in prev}) < min_days:
            continue
        baseline = float(median(float(p['price_ars']) for p in prev))
        current = float(row['price_ars'])
        if not baseline or current >= baseline:
            continue
        drop = round((baseline - current) / baseline * 100, 2)
        if drop < threshold:
            continue
        prior = sorted(past[row['listing_id']], key=lambda o: o['detected_at'], reverse=True)
        if prior:
            most_recent = prior[0]
            elapsed_h = (now - as_date(most_recent['detected_at'])).total_seconds() / 3600
            if elapsed_h < cooldown or current >= float(most_recent['price_ars']) * (1 - extra_drop / 100):
                continue
        offer_id = hashlib.sha256(f"{row['observation_id']}|offer".encode()).hexdigest()[:20]
        offers.append({
            'offer_id': offer_id, 'observation_id': row['observation_id'],
            'detected_at': row['captured_at'], 'source': row['source'],
            'listing_id': row['listing_id'], 'title': row['title'],
            'url': row['url'], 'price_ars': current,
            'baseline_median_ars': round(baseline, 2), 'drop_pct': drop,
            'status': 'awaiting_review', 'currency': 'ARS',
            'evidence_samples': len(prev), 'evidence_distinct_days': len({as_date(p['captured_at']).date() for p in prev}),
            'data_mode': row['data_mode']
        })
    return offers
