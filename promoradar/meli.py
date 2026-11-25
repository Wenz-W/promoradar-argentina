"""Conector da API oficial do Mercado Libre. Exige credenciais autorizadas."""
from __future__ import annotations
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import time
import hashlib

API = 'https://api.mercadolibre.com'

class ProviderError(Exception):
    pass


def fetch_results(token: str, site: str, query: str, limit: int, attempts: int = 3) -> list[dict]:
    url = f"{API}/sites/{site}/search?" + urlencode({'q': query, 'limit': limit})
    req = Request(url, headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json', 'User-Agent': 'PromoRadarAcademic/0.1'})
    for attempt in range(attempts):
        try:
            with urlopen(req, timeout=20) as response:
                payload = json.load(response)
            if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
                raise ProviderError('Formato de resposta inesperado da API')
            return payload['results']
        except HTTPError as e:
            if e.code in (401, 403):
                raise ProviderError(f'Acesso não autorizado ({e.code}). Verifique permissões e token.') from e
            if e.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise ProviderError(f'API respondeu HTTP {e.code}') from e
            try:
                pause = min(int(e.headers.get('Retry-After', '0')), 30)
            except (TypeError, ValueError):
                pause = 0
            time.sleep(max(pause, 2 ** attempt))
        except (URLError, TimeoutError) as e:
            if attempt == attempts - 1:
                raise ProviderError('Falha de rede/timeout na API') from e
            time.sleep(2 ** attempt)
    return []


def normalize_item(item: dict, capture_time: str, run_id: str, mode: str = 'real') -> dict | None:
    item_id = str(item.get('id') or '').strip()
    url = str(item.get('permalink') or '')
    if not item_id or not url.startswith('https://') or item.get('currency_id') != 'ARS':
        return None
    try:
        price = Decimal(str(item.get('price')))
    except (InvalidOperation, TypeError):
        return None
    if price <= 0:
        return None
    stock = 'available' if item.get('status', 'active') == 'active' else 'unknown'
    if item.get('available_quantity') == 0:
        stock = 'unavailable'
    obs_id = hashlib.sha256(f"{run_id}|MLA|{item_id}".encode()).hexdigest()[:24]
    return {
        'observation_id': obs_id,
        'run_id': run_id,
        'captured_at': capture_time,
        'source': 'mercadolibre',
        'listing_id': item_id,
        'title': str(item.get('title') or '').strip(),
        'price_ars': float(price),
        'currency': 'ARS',
        'url': url,
        'thumbnail': str(item.get('thumbnail') or ''),
        'stock_status': stock,
        'seller_id': str((item.get('seller') or {}).get('id') or ''),
        'category_id': str(item.get('category_id') or ''),
        'data_mode': mode,
        'shipping_cost_ars': None,
        'price_scope': 'public_listing_price_no_freight'
    }
