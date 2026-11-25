"""Preços de supermercados: API aberta Superprecios Claros com dados SEPA.

Fonte oficial original: SEPA (Argentina.gob.ar). API agregada de terceiros:
https://github.com/hysmarcos/superprecios-claros (MIT).
Não é um link de compra e não garante estoque nem preço da unidade individual.
"""
from __future__ import annotations
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import date, datetime, timezone
from hashlib import sha256
import json

API_BASE = 'https://hysmarcos.github.io/superprecios-claros'
CHAIN_NAMES = {'1':'Coto','2':'Vea','3':'Disco','4':'Jumbo','5':'Carrefour Hiper',
               '6':'Carrefour Market','7':'Carrefour Express','8':'Maxi Carrefour',
               '9':'DIA','10':'La Anónima','11':'Topsy','12':'Bomba',
               '13':'Cooperativa Obrera','14':'Libertad','15':'Toledo'}

class SepaError(Exception):
    pass


def download_json(url: str) -> dict:
    req = Request(url, headers={'User-Agent':'PromoRadarAcademic/0.1 (SEPA attribution)', 'Accept':'application/json'})
    try:
        with urlopen(req, timeout=25) as response:
            payload=json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
        raise SepaError(f'Falha ao consultar fonte pública SEPA: {type(e).__name__}') from e
    if not isinstance(payload,dict):
        raise SepaError('Resposta da fonte pública não é JSON objeto.')
    return payload


def parse_shard(payload: dict, region: str, retrieved_at: str, max_items: int) -> list[dict]:
    fecha = payload.get('fecha')
    items = payload.get('items')
    if not isinstance(fecha, str) or not isinstance(items,dict) or payload.get('region')!=region:
        raise SepaError('Formato de resposta de shard diferente do documentado.')
    try:
        date.fromisoformat(fecha)
    except ValueError as e:
        raise SepaError('Data SEPA inválida') from e
    captured_at=f'{fecha}T12:00:00+00:00'
    out=[]
    count=0
    for ean, info in sorted(items.items()):
        if count>=max_items:
            break
        produto=info.get('producto') or {}
        title=str(produto.get('nombre') or '').strip()
        chain_info=info.get('por_cadena') or {}
        if not title or not isinstance(chain_info,dict):
            continue
        seen_any=False
        for chain_id, spec in sorted(chain_info.items()):
            try:
                price=float(spec.get('precio_efectivo', 0))
                chain_int=int(chain_id)
            except (TypeError, ValueError):
                continue
            if not 0<price<20_000_000:
                continue
            listing_id=f'SEPA:{region}:{ean}:{chain_int}'
            obs_id=sha256(f'{listing_id}:{fecha}'.encode()).hexdigest()[:24]
            out.append({
                'observation_id':obs_id, 'run_id':'', 'captured_at':captured_at,
                'source_date':fecha, 'retrieved_at':retrieved_at,
                'source':'sepa', 'listing_id':listing_id,
                'title':f"{title} — {CHAIN_NAMES.get(str(chain_int), f'Cadena {chain_int}')}",'price_ars':price,
                'currency':'ARS','url':f'{API_BASE}/v1/sku/{ean}/{region}.json',
                'thumbnail':'','stock_status':'listed','seller_id':str(chain_int),
                'category_id':'supermercado', 'merchant':CHAIN_NAMES.get(str(chain_int), f'Cadena {chain_int}'), 'data_mode':'real',
                'shipping_cost_ars':None,'price_scope':'regional_chain_median_price',
                'ean':ean, 'region':region,
                'has_promotion':bool(spec.get('tiene_promo',False)),
                'source_attribution':'SEPA — Secretaria de Comercio Argentina; API superprecios-claros',
            })
            seen_any=True
        if seen_any: count+=1
    return out


def fetch_sepa(region: str, shards: list[str], max_items_per_shard: int,
               max_staleness_days: int, retrieved_at: str) -> list[dict]:
    rows=[]
    for shard in shards:
        if len(shard)!=2 or not shard.isdecimal():
            raise SepaError(f'Shard inválido: {shard!r}')
        url=f'{API_BASE}/v1/skus/{region}/{shard}.json'
        payload=download_json(url)
        fecha=payload.get('fecha')
        if not isinstance(fecha,str):
            raise SepaError('Fonte SEPA não retornou data.')
        try:
            age=(datetime.fromisoformat(retrieved_at).date()-date.fromisoformat(fecha)).days
        except ValueError as e:
            raise SepaError('Data SEPA inválida.') from e
        if age < 0 or age > max_staleness_days:
            raise SepaError(f'Dados SEPA desatualizados: {fecha}; idade {age} dias (limite {max_staleness_days}).')
        rows.extend(parse_shard(payload,region,retrieved_at,max_items_per_shard))
    return rows
