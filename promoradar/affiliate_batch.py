"""Exportar lotes para o gerador OFICIAL Mercado Libre e importar seus retornos.

Não fabrica URLs de afiliado. Não valida comissões ou preço atual pelo link curto.
Dados de afiliação fornecidos pelo operador ficam separados de coletas verificadas.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .affiliate_manual import validate_affiliate_url, ManualAffiliateError
from .storage import DATA, append_jsonl, read_jsonl, read_series, utcnow

PRODUCT_ID = re.compile(r'(?<![A-Z0-9])MLA[-_ ]?(\d{6,16})(?!\d)', re.I)
LABEL = re.compile(r'[a-zA-Z0-9_\-]{3,50}\Z')
BATCH_ID = re.compile(r'AB-[A-F0-9]{16}\Z')


class AffiliateBatchError(ValueError):
    pass


def normalize_product_url(url: str) -> tuple[str, str]:
    """Retorna (identificador de catálogo/anúncio, URL canônica).

    Não inspeciona o destino via rede: só aceita URLs oficiais com MLA ID no path.
    O produto de catálogo MLA... não é necessariamente o anúncio de um vendedor.
    """
    if not isinstance(url, str) or not url or url != url.strip() or any(c.isspace() for c in url):
        raise AffiliateBatchError('URL de produto vazia ou malformada.')
    try:
        u = urlsplit(url)
    except ValueError as exc:
        raise AffiliateBatchError('URL de produto malformada.') from exc
    if (u.scheme != 'https' or u.hostname not in
            ('www.mercadolibre.com.ar', 'mercadolibre.com.ar', 'articulo.mercadolibre.com.ar')
            or u.username or u.password or u.port is not None or u.fragment):
        raise AffiliateBatchError('Use URL HTTPS de produto do Mercado Libre Argentina, sem fragmentos.')
    if '/social/' in u.path or '/redirect/' in u.path.lower():
        raise AffiliateBatchError('URL do perfil/link de afiliado não é URL de produto.')
    found = PRODUCT_ID.search(u.path)
    if not found:
        raise AffiliateBatchError('Não foi encontrado ID MLA... no caminho do produto.')
    key = 'MLA' + found.group(1)
    # Catalog URLs aceitas pelo gerador, estáveis sem slug/tracking.
    if re.search(r'/p/MLA\d+', u.path, re.I):
        return key, f'https://www.mercadolibre.com.ar/p/{key}'
    # Anúncios individuais podem depender do slug; guardamos o caminho integral.
    return key, 'https://' + u.hostname + u.path


def validate_official_affiliate_link(link: str, label: str) -> str:
    """Links curtos do gerador ou links completos /social com a MESMA etiqueta."""
    if not isinstance(link, str) or link != link.strip() or any(c.isspace() for c in link):
        raise AffiliateBatchError('Link de afiliado malformado.')
    if not LABEL.fullmatch(label):
        raise AffiliateBatchError('Etiqueta inválida.')
    try:
        if link.startswith('https://meli.la/'):
            return validate_affiliate_url(link)
        u = urlsplit(link)
        if (u.scheme != 'https' or u.hostname not in ('www.mercadolibre.com.ar','mercadolibre.com.ar')
                or u.username or u.password or u.port is not None or u.fragment
                or u.path != f'/social/{label}'):
            raise AffiliateBatchError('Link completo não corresponde ao perfil informado.')
        q = parse_qs(u.query, keep_blank_values=True)
        if q.get('matt_word') != [label] or not q.get('matt_tool') or not q.get('ref'):
            raise AffiliateBatchError('Link completo sem etiqueta ou referência oficial.')
        if len(q['matt_tool']) != 1 or not q['matt_tool'][0].isdigit() or len(q['ref']) != 1 or len(q['ref'][0]) < 20:
            raise AffiliateBatchError('Parâmetros do link completo inválidos.')
        return link
    except ManualAffiliateError as exc:
        raise AffiliateBatchError(str(exc)) from exc
    except ValueError as exc:
        raise AffiliateBatchError('Link de afiliado malformado.') from exc


def read_link_bank(*, data_dir: Path | None = None) -> dict[tuple[str,str],dict]:
    root = data_dir if data_dir is not None else DATA / 'real'
    bank: dict[tuple[str,str],dict] = {}
    for f in sorted(root.glob('affiliate-links-*.jsonl')):
        for row in read_jsonl(f):
            if row.get('source') != 'mercadolibre' or not row.get('product_key') or not row.get('label'):
                continue
            key=(row['label'],row['product_key'])
            if key not in bank or row['recorded_at'] >= bank[key]['recorded_at']:
                bank[key] = row
    return bank


def collect_latest_products(observations: list[dict], *, at: datetime | None = None,
                            max_age_hours: int = 30) -> list[dict]:
    """Busca candidatos entre observações REAIS e recentes; não inventa descontos."""
    at = (at or utcnow()).astimezone(timezone.utc)
    if not 1 <= max_age_hours <= 72:
        raise AffiliateBatchError('max_age_hours precisa estar entre 1 e 72.')
    latest: dict[str,dict] = {}
    for row in observations:
        if row.get('source') != 'mercadolibre' or row.get('data_mode') != 'real' or row.get('currency') != 'ARS':
            continue
        if row.get('stock_status') != 'available':
            continue
        try:
            ts = datetime.fromisoformat(row['captured_at'].replace('Z','+00:00')).astimezone(timezone.utc)
            if not timedelta(0) <= at-ts <= timedelta(hours=max_age_hours):
                continue
            price = float(row['price_ars'])
            if not 0 < price < 1e9:
                continue
            key,url=normalize_product_url(row['url'])
        except (KeyError, ValueError, TypeError, OverflowError):
            continue
        old=latest.get(key)
        if old is None or ts > datetime.fromisoformat(old['captured_at'].replace('Z','+00:00')):
            latest[key]={
                'product_key':key,'product_url':url,
                'title':str(row.get('title') or 'Producto').strip()[:160],
                'price_ars':price,'captured_at':ts.isoformat(),
                'source':'mercadolibre', 'origin':'automatic_authorized_observation',
                'price_evidence':'observed_price_not_historical_discount',
            }
    return sorted(latest.values(),key=lambda x:(x['captured_at'],x['product_key']),reverse=True)


def _csv(rows: list[dict], columns: list[str]) -> str:
    output=io.StringIO()
    writer=csv.DictWriter(output,fieldnames=columns,extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_batch(*, observations: list[dict] | None = None,
                 label: str, max_items: int = 20, max_age_hours: int = 30,
                 data_dir: Path | None = None, out_dir: Path | None = None,
                 at: datetime | None = None) -> dict:
    """Gera URLs alinhadas por posição; somente produtos ainda sem link oficial."""
    if not LABEL.fullmatch(label):
        raise AffiliateBatchError('Etiqueta inválida: use sua etiqueta do gerador oficial.')
    if not 1 <= max_items <= 50:
        raise AffiliateBatchError('Lote precisa conter de 1 a 50 produtos.')
    root=data_dir if data_dir is not None else DATA/'real'
    output=out_dir if out_dir is not None else Path('outputs/affiliate-batch')
    bank=read_link_bank(data_dir=root)
    observations=read_series('observations','real') if observations is None else observations
    products=collect_latest_products(observations,at=at,max_age_hours=max_age_hours)
    new=[p for p in products if (label,p['product_key']) not in bank][:max_items]
    ready=[{**p,'affiliate_url':bank[(label,p['product_key'])]['affiliate_url']}
           for p in products if (label,p['product_key']) in bank]
    output.mkdir(parents=True,exist_ok=True)
    (output/'urls-para-gerador.txt').write_text('\n'.join(p['product_url'] for p in new)+('\n' if new else ''),encoding='utf-8')
    cols=['product_key','title','price_ars','captured_at','product_url','origin','price_evidence']
    (output/'pendentes.csv').write_text(_csv(new,cols),encoding='utf-8')
    (output/'com-link-oficial.csv').write_text(_csv(ready,cols+['affiliate_url']),encoding='utf-8')
    batch_id=None
    if new:
        fingerprint='\n'.join(p['product_url'] for p in new)
        batch_id='AB-'+hashlib.sha256((label+'\n'+fingerprint).encode()).hexdigest()[:16].upper()
        doc={'batch_id':batch_id,'label':label,'generated_at':(at or utcnow()).astimezone(timezone.utc).isoformat(),
             'source':'mercadolibre', 'mapping':'ordered_lines_only', 'count':len(new), 'products':new}
        dest=root/'affiliate-batches'/f'{batch_id}.json'
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():
            prior=json.loads(dest.read_text(encoding='utf-8'))
            if [p['product_url'] for p in prior['products']] != [p['product_url'] for p in new] or prior['label']!=label:
                raise AffiliateBatchError('Lote existente inconsistente.')
        else:
            dest.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (output/'batch-id.txt').write_text(batch_id+'\n',encoding='utf-8')
    else:
        (output/'batch-id.txt').write_text('SEM NOVOS PRODUTOS\n',encoding='utf-8')
    return {'batch_id':batch_id,'pending':len(new),'already_linked':len(ready),
            'valid_recent_products':len(products),'output_dir':str(output)}


def import_batch(*, batch_id: str, links_text: str, data_dir: Path | None = None,
                 at: datetime | None = None) -> dict:
    """Importa somente output oficial na ordem do lote; valida tudo ANTES de gravar."""
    if not BATCH_ID.fullmatch(batch_id):
        raise AffiliateBatchError('batch_id inválido.')
    root=data_dir if data_dir is not None else DATA/'real'
    batch_file=root/'affiliate-batches'/f'{batch_id}.json'
    if not batch_file.exists():
        raise AffiliateBatchError('Lote não encontrado. Execute a exportação antes da importação.')
    doc=json.loads(batch_file.read_text(encoding='utf-8'))
    if doc.get('batch_id') != batch_id or doc.get('mapping')!='ordered_lines_only':
        raise AffiliateBatchError('Manifesto de lote inválido.')
    label=doc['label']
    items=doc['products']
    links=[line.strip() for line in links_text.splitlines() if line.strip()]
    if len(links) != len(items):
        raise AffiliateBatchError(f'O gerador retornou {len(links)} links, mas o lote tem {len(items)} produtos. Não gravado.')
    checked=[validate_official_affiliate_link(link,label) for link in links]
    if len(set(checked)) != len(checked):
        raise AffiliateBatchError('O mesmo link não pode ser associado a produtos distintos. Não gravado.')
    bank=read_link_bank(data_dir=root)
    # Impede que uma URL oficial conhecida seja reutilizada para outro produto.
    link_keys={rec['affiliate_url']:(lab,key) for (lab,key),rec in bank.items()}
    for p,link in zip(items,checked):
        if link in link_keys and link_keys[link] != (label,p['product_key']):
            raise AffiliateBatchError('Link já pertence a outro produto. Não gravado.')
    moment=(at or utcnow()).astimezone(timezone.utc)
    rows=[]
    for p,link in zip(items,checked):
        if (label,p['product_key']) in bank:
            if bank[(label,p['product_key'])]['affiliate_url'] != link:
                raise AffiliateBatchError('Há um link oficial diferente para esse produto; revisão manual necessária.')
            continue
        rows.append({'link_id':'AL-'+hashlib.sha256(f'{label}|{p["product_key"]}|{link}'.encode()).hexdigest()[:18].upper(),
                     'product_key':p['product_key'],'product_url':p['product_url'],
                     'affiliate_url':link,'label':label,'source':'mercadolibre',
                     'recorded_at':moment.isoformat(), 'batch_id':batch_id,
                     'evidence':'copied_from_official_generator_by_operator_no_attribution_test',
                     'price_verified':False,'product_destination_rechecked':False})
    if rows:
        filename=root/f'affiliate-links-{moment.strftime("%Y-%m")}.jsonl'
        append_jsonl(filename,rows,'link_id')
    return {'batch_id':batch_id,'imported':len(rows),'already_known':len(items)-len(rows),'total':len(items),
            'status':'links_officially_generated_operator_supplied_not_live_verified'}


def register_user_supplied_link(product_url: str, link: str, label: str,
                                *, at: datetime | None = None, data_dir: Path | None = None) -> dict:
    """Importação individual opcional, quando o usuário já trouxe link oficial validado por ele.
    Não usa horário/URL como alegação de que o preço continua vigente.
    """
    root=data_dir if data_dir is not None else DATA/'real'
    key,url=normalize_product_url(product_url)
    link=validate_official_affiliate_link(link,label)
    bank=read_link_bank(data_dir=root)
    known=bank.get((label,key))
    if known:
        if known['affiliate_url']!=link:
            raise AffiliateBatchError('Produto possui link diferente; revisão manual necessária.')
        return {**known,'new':False}
    if any(r['affiliate_url']==link and (r['label'],r['product_key'])!=(label,key) for r in bank.values()):
        raise AffiliateBatchError('URL de afiliado já associada a outro produto.')
    at=(at or utcnow()).astimezone(timezone.utc)
    row={'link_id':'AL-'+hashlib.sha256(f'{label}|{key}|{link}'.encode()).hexdigest()[:18].upper(),
         'product_key':key,'product_url':url,'affiliate_url':link,'label':label,
         'source':'mercadolibre','recorded_at':at.isoformat(),
         'evidence':'user_supplied_official_generator_example_no_live_verification',
         'price_verified':False,'product_destination_rechecked':False}
    append_jsonl(root/f'affiliate-links-{at.strftime("%Y-%m")}.jsonl',[row],'link_id')
    return {**row,'new':True}
