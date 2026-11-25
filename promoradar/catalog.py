"""Catálogo público estático. Só promove anúncios reais, aprovados e revalidados.

A oferta não é um anúncio de supermercado regional: SEPA não fornece checkout.
Aprovações são eventos auditáveis, separados dos registros imutáveis de coleta.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .analytics import as_date
from .storage import DATA, BASE, append_jsonl, read_series, utcnow

DOCS = BASE / 'docs'


def is_buy_link(url: str, source: str, mode: str) -> bool:
    if mode == 'demo':
        return False  # Nunca tratar links fictícios como compra real.
    if source == 'sepa':
        return False  # Médias regionais informativas, não links de compra.
    hosts = {
        'mercadolibre': ('mercadolibre.com.ar', 'mercadolibre.com'),
        'shopee': ('shopee.com.ar',),
        'temu': ('temu.com',),
        'shein': ('shein.com',),
        'fravega': ('fravega.com',),
        'carrefour': ('carrefour.com.ar',),
    }
    try:
        parts = urlsplit(url)
        hostname = (parts.hostname or '').lower()
        return parts.scheme == 'https' and parts.username is None and parts.password is None and any(
            hostname == root or hostname.endswith('.' + root)
            for root in hosts.get(source, ())
        )
    except ValueError:
        return False


def record_review(offer_id: str, decision: str, mode: str = 'real', *, when: datetime | None = None) -> dict:
    if decision not in ('approved', 'rejected'):
        raise ValueError('Decisão inválida; use approved ou rejected.')
    if mode != 'real':
        raise ValueError('Aprovações de demonstração são geradas apenas pelo comando demo.')
    offers = read_series('offers', mode)
    matching = [o for o in offers if o.get('offer_id') == offer_id]
    if not matching:
        raise ValueError('Oferta não encontrada no histórico real; não é possível aprovar.')
    offer = matching[-1]
    if offer.get('data_mode') != 'real' or offer.get('source') == 'sepa':
        raise ValueError('Apenas anúncios reais com link de compra podem ser aprovados.')
    if not is_buy_link(offer.get('url', ''), offer.get('source',''), 'real'):
        raise ValueError('Link comercial não validado para esta fonte.')
    ts = (when or utcnow()).astimezone(timezone.utc).isoformat()
    event = {'offer_id': offer_id, 'listing_id': offer['listing_id'], 'decision': decision,
             'decided_at': ts, 'reviewer': 'github_actions_manual', 'data_mode': 'real'}
    append_jsonl(DATA / mode / f'reviews-{ts[:7]}.jsonl', [event])
    return event


def build_catalog(observations: list[dict], offers: list[dict], reviews: list[dict],
                  *, now: datetime | None = None, mode: str = 'real',
                  max_age_hours: float = 30, max_offer_days: float = 7,
                  min_drop_pct: float = 15) -> dict:
    """Pure function for testability: no unreviewed, stale or synthetic real offers."""
    if mode not in ('real', 'demo'):
        raise ValueError('Modo inválido')
    now = (now or utcnow()).astimezone(timezone.utc)
    nowstr = now.isoformat()
    # Última revisão ganha (rejeição posterior revoga aprovação anterior).
    latest_review = {}
    for event in reviews:
        if event.get('data_mode') != mode or event.get('decision') not in ('approved', 'rejected'):
            continue
        key = event.get('offer_id')
        if not key:
            continue
        try:
            ts = as_date(event['decided_at'])
        except (KeyError, ValueError, TypeError):
            continue
        if ts <= now and (key not in latest_review or ts >= latest_review[key][0]):
            latest_review[key] = (ts, event['decision'])

    # Captured_at é a data da observação; data original das fontes agregadas pode divergir.
    latest_observation = {}
    history = defaultdict(list)
    for row in observations:
        if row.get('data_mode') != mode or row.get('currency') != 'ARS':
            continue
        listing_id = row.get('listing_id')
        if not listing_id:
            continue
        try:
            observed_at = as_date(row['captured_at'])
        except (KeyError, TypeError, ValueError):
            continue
        if observed_at > now:
            continue
        history[listing_id].append(row)
        old = latest_observation.get(listing_id)
        if old is None or observed_at >= as_date(old['captured_at']):
            latest_observation[listing_id] = row

    selected = {}
    for offer in offers:
        if offer.get('data_mode') != mode:
            continue
        offer_id = offer.get('offer_id')
        if latest_review.get(offer_id, (None, None))[1] != 'approved':
            continue
        try:
            detected_at = as_date(offer['detected_at'])
        except (KeyError, TypeError, ValueError):
            continue
        if not timedelta(0) <= now - detected_at <= timedelta(days=max_offer_days):
            continue
        listing_id = offer.get('listing_id')
        row = latest_observation.get(listing_id)
        if not row or row.get('stock_status') not in ('available', 'listed'):
            continue
        if row.get('source') != offer.get('source'):
            continue
        age = now - as_date(row['captured_at'])
        if not timedelta(0) <= age <= timedelta(hours=max_age_hours):
            continue
        # Fontes com preço agregado não autorizam links de compra.
        if not is_buy_link(row.get('url',''), row.get('source',''), mode) and mode == 'real':
            continue
        try:
            current = float(row['price_ars'])
            ref = float(offer['baseline_median_ars'])
            approved_price = float(offer['price_ars'])
        except (KeyError, TypeError, ValueError):
            continue
        if current <= 0 or ref <= 0 or current > approved_price:
            continue  # Mudou para mais caro: precisa de nova curadoria.
        drop = round((ref - current) / ref * 100, 2)
        if drop < min_drop_pct:
            continue
        entry = {
            'offer_id': offer_id,
            'listing_id': listing_id,
            'title': row.get('title') or offer.get('title') or 'Produto',
            'store': ({'mercadolibre':'Mercado Libre','shopee':'Shopee','temu':'Temu',
                       'shein':'SHEIN','fravega':'Frávega','carrefour':'Carrefour', 'demo_synthetic':'Tienda ficticia'}
                      .get(row.get('source'), row.get('source',''))),
            'source': row.get('source'),
            'category': row.get('category_name') or row.get('category_id') or 'Otros',
            'price_ars': round(current, 2),
            'historical_reference_ars': round(ref, 2),
            'drop_pct': drop,
            'url': row.get('url') if mode == 'real' else None,
            'image_url': None,  # Direitos de reprodução de imagens são por fonte.
            'detected_at': offer['detected_at'],
            'last_verified_at': row['captured_at'],
            'approved_at': latest_review[offer_id][0].isoformat(),
            'status': 'active',
            'is_demo': mode == 'demo',
            'price_scope': row.get('price_scope','public_listing_price_no_freight'),
            'history': [
                {'date': r['captured_at'][:10], 'price_ars': round(float(r['price_ars']),2)}
                for r in sorted(history[listing_id], key=lambda r:r['captured_at'])[-40:]
                if r.get('price_ars') is not None
            ],
        }
        previous = selected.get(listing_id)
        if previous is None or detected_at > as_date(previous['detected_at']):
            selected[listing_id] = entry

    entries = sorted(selected.values(), key=lambda r: (-r['drop_pct'], -as_date(r['detected_at']).timestamp()))
    return {
        'generated_at': nowstr, 'mode': mode, 'max_age_hours': max_age_hours,
        'max_offer_days': max_offer_days, 'count': len(entries), 'offers': entries,
    }


def generate_catalog(mode: str = 'real', *, now: datetime | None = None) -> Path:
    cfg = json.loads((BASE / 'config' / 'settings.json').read_text(encoding='utf-8'))
    opts = cfg.get('catalog', {})
    feed = build_catalog(read_series('observations',mode), read_series('offers',mode),
                         read_series('reviews',mode), now=now, mode=mode,
                         max_age_hours=float(opts.get('max_verification_age_hours',30)),
                         max_offer_days=float(opts.get('max_offer_age_days',7)),
                         min_drop_pct=float(cfg.get('drop_threshold_pct',15)))
    DOCS.mkdir(exist_ok=True)
    filename = 'ofertas-demo.json' if mode == 'demo' else 'ofertas.json'
    path = DOCS / filename
    path.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding='utf-8')
    return path
