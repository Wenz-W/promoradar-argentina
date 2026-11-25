"""CLI do PromoRadar: collect, render, demo, review e all."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import argparse
import json
import os
import sys
from .storage import BASE, read_series, store_run, utcnow
from .analytics import detect_offers
from .dashboard import generate
from .meli import fetch_results, normalize_item, ProviderError
from .oauth import get_access_token, CredentialError
from .sepa import fetch_sepa, SepaError
from .catalog import generate_catalog, record_review

SETTINGS = BASE / 'config' / 'settings.json'

def get_settings():
    return json.loads(SETTINGS.read_text(encoding='utf-8'))


def collect():
    cfg=get_settings()
    started=utcnow().isoformat()
    run_id=uuid4().hex
    run={'run_id':run_id,'started_at':started,'status':'pending',
         'observations_count':0,'offers_count':0,'error':'','source_status':{}}
    rows=[]
    errors=[]
    successes=0
    ml=cfg.get('mercadolibre',{})
    if ml.get('enabled'):
        try:
            token=get_access_token()
            for query in ml.get('queries',[])[:int(ml.get('max_requests_per_run',5))]:
                try:
                    items=fetch_results(token,ml['site_id'],query,int(ml.get('results_per_query',10)))
                    for item in items:
                        row=normalize_item(item,started,run_id)
                        if row is not None:
                            rows.append(row)
                    successes += 1
                except ProviderError as e:
                    errors.append(f'Mercado Libre [{query}]: {e}')
            run['source_status']['mercadolibre']='success' if successes else 'failed'
        except CredentialError as e:
            run['source_status']['mercadolibre']='unconfigured'
            errors.append(f'Mercado Libre: {e}')
        except Exception as e:
            run['source_status']['mercadolibre']='failed'
            errors.append(f'Mercado Libre: {type(e).__name__}: {str(e)[:100]}')
    sp=cfg.get('sepa',{})
    if sp.get('enabled'):
        try:
            sepa_rows=fetch_sepa(sp['region'],sp['shards'],int(sp['max_items_per_shard']),
                                 int(sp['max_staleness_days']),started)
            for row in sepa_rows:
                row['run_id']=run_id
            rows.extend(sepa_rows)
            successes += 1
            run['source_status']['sepa']='success'
        except SepaError as e:
            errors.append(f'SEPA: {e}')
            run['source_status']['sepa']='failed'
        except Exception as e:
            errors.append(f'SEPA: {type(e).__name__}: {str(e)[:100]}')
            run['source_status']['sepa']='failed'
    historical=read_series('observations','real')
    old_ids={r['observation_id'] for r in historical}
    unique={r['observation_id']:r for r in rows}
    rows=[r for r in unique.values() if r['observation_id'] not in old_ids]
    offers=detect_offers(rows,historical,read_series('offers','real'),cfg)
    run['status']='ok' if successes and not errors else ('partial' if successes else 'failed')
    if not ml.get('enabled') and not sp.get('enabled'):
        run['status']='unconfigured'
        errors.append('Nenhuma fonte habilitada.')
    run['error']=' | '.join(errors)[:900]
    run['observations_count']=len(rows)
    run['offers_count']=len(offers)
    run['finished_at']=utcnow().isoformat()
    saved=store_run('real',run,rows,offers)
    print(json.dumps({'run':run,'persisted':saved},ensure_ascii=False,indent=2))
    return 0 if run['status'] in ('ok','partial') else 2


def demo():
    """Gera preços SINTÉTICOS separados, somente para demonstração."""
    cfg=get_settings()
    fake=[('MLA-DEMO-001','Cafetera demostración',129000),
          ('SHP-DEMO-002','Auriculares demostración',65000),
          ('TEMU-DEMO-003','Organizador demostración',32000)]
    base=utcnow()-timedelta(days=20)
    rows=[]
    for day in range(21):
        ts=(base+timedelta(days=day)).isoformat()
        for code, title, initial in fake:
            if code.endswith('001'):
                price=initial if day<15 else 90000
            elif code.endswith('002'):
                price=initial if day<18 else 49000
            else:
                price=initial if day<17 else 31000
            rows.append({'observation_id':f'demo-{code}-{day}', 'run_id': f'demo-{day}', 'captured_at':ts,
                'source':'demo_synthetic', 'listing_id':code, 'title':title,'price_ars':price,
                'currency':'ARS','url':'https://example.org/demonstracion','stock_status':'available',
                'data_mode':'demo','shipping_cost_ars':None})
    records=[]
    prev=[]
    offers=[]
    for day in range(21):
        capture=[r for r in rows if r['run_id']==f'demo-{day}']
        detected=detect_offers(capture,prev,offers,cfg)
        offers += detected
        prev += capture
        records.append({'run_id':f'demo-{day}', 'started_at':capture[0]['captured_at'],
                        'status':'ok', 'observations_count':len(capture),'offers_count':len(detected),
                        'error':'DEMO SINTÉTICA'})
    root=BASE/'data'/'demo'
    for f in root.glob('*.jsonl'):
        f.unlink()
    from .storage import append_jsonl
    month=base.strftime('%Y-%m')
    # Segregar por mês para leitura e análise consistente
    from collections import defaultdict
    for kind, items in [('observations',rows),('offers',offers),('runs',records)]:
        buckets=defaultdict(list)
        key='captured_at' if kind=='observations' else ('detected_at' if kind=='offers' else 'started_at')
        for item in items: buckets[item[key][:7]].append(item)
        for ym,b in buckets.items(): append_jsonl(root/f'{kind}-{ym}.jsonl',b)
    from .storage import append_jsonl
    # Aprovações SINTÉTICAS, separadas das revisões reais.
    for path in root.glob('reviews-*.jsonl'):
        path.unlink()
    for offer in offers:
        ts=as_review_time(offer['detected_at'])
        append_jsonl(root/f"reviews-{ts[:7]}.jsonl",
            [{'offer_id':offer['offer_id'], 'listing_id':offer['listing_id'],
              'decision':'approved', 'decided_at':ts, 'reviewer':'demo_only',
              'data_mode':'demo'}])
    out=generate('demo')
    generate_catalog('demo')
    print(f'DEMO: {len(rows)} observações sintéticas, {len(offers)} oportunidades, painel: {out}')
    return 0


def as_review_time(stamp: str) -> str:
    return (datetime.fromisoformat(stamp) + timedelta(seconds=10)).isoformat()

def main():
    p=argparse.ArgumentParser(description='PromoRadar Argentina (projeto acadêmico)')
    p.add_argument('command', choices=['collect','render','demo','all','review'])
    p.add_argument('--offer-id', default='')
    p.add_argument('--decision', choices=['approved','rejected'])
    args=p.parse_args()
    if args.command=='demo': return demo()
    if args.command=='render':
        print(generate('real'))
        print(generate_catalog('real'))
        return 0
    if args.command=='review':
        if not args.offer_id or not args.decision:
            p.error('review exige --offer-id e --decision')
        try:
            event=record_review(args.offer_id,args.decision)
        except ValueError as exc:
            p.error(str(exc))
        print(json.dumps(event,ensure_ascii=False,indent=2))
        print(generate_catalog('real'))
        return 0
    if args.command=='collect': return collect()
    if args.command=='all':
        result=collect()
        generate('real')
        generate_catalog('real')
        return result

if __name__=='__main__': sys.exit(main())
