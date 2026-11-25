"""Gera site estático e auditável para GitHub Pages sem API paga."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
import json
import csv
from .storage import DATA, BASE, read_series

DOCS = BASE / 'docs'

def fmt_money(n):
    return '$ ' + format(float(n), ',.2f').replace(',', 'X').replace('.', ',').replace('X', '.')


def line_svg(values: list[float], height: int = 88, width: int = 280) -> str:
    if not values:
        return '<span class="subtle">Sem histórico suficiente</span>'
    vals = values[-40:]
    lo, hi = min(vals), max(vals)
    range_v = hi - lo if hi != lo else 1
    coords = []
    for i, v in enumerate(vals):
        x = 5 + i * (width - 10) / max(len(vals)-1, 1)
        y = 6 + (hi - v) / range_v * (height - 12)
        coords.append((x, y))
    points = ' '.join(f'{x:.1f},{y:.1f}' for x, y in coords)
    return (f'<svg role="img" aria-label="Evolución de precios" viewBox="0 0 {width} {height}" '
            f'class="spark"><polyline points="{points}" fill="none" stroke="#1575e9" '
            f'stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/></svg>')


def _export_csv(path: Path, rows: list[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def generate(mode='real'):
    obs = read_series('observations', mode)
    runs = read_series('runs', mode)
    offers = read_series('offers', mode)
    latest = {}
    series = defaultdict(list)
    for r in sorted(obs, key=lambda x: x['captured_at']):
        latest[r['listing_id']] = r
        series[r['listing_id']].append(float(r['price_ars']))
    ok_runs = sum(1 for r in runs if r['status'] in ('ok', 'partial'))
    errors = [r for r in runs if r['status'] not in ('ok', 'partial')]
    first = min((r['started_at'] for r in runs), default=None)
    last = max((r['started_at'] for r in runs), default=None)
    recent = sorted(offers, key=lambda x: x['detected_at'], reverse=True)[:60]
    products = sorted(latest.values(), key=lambda x: x['title'].casefold())[:250]
    cards = [
        ('Observaciones', format(len(obs), ',')),
        ('Productos distintos', str(len(latest))),
        ('Ofertas detectadas', str(len(offers))),
        ('Coletas concluídas', f'{ok_runs} / {len(runs)}')
    ]
    heading = 'Datos de prueba — DEMOSTRACIÓN' if mode == 'demo' else 'Monitoreo real — Argentina'
    data_flag = 'DEMO: DATOS SINTÉTICOS, NO COMERCIALES' if mode == 'demo' else ('SIN COLECTAS REALES TODAVÍA' if not obs else 'DATOS OBSERVADOS: FUENTES INDICADAS')
    stats = ''.join(f'<div class="stat"><div class="stat-val">{escape(v)}</div><div class="stat-name">{escape(k)}</div></div>' for k, v in cards)
    offer_rows = []
    for o in recent:
        title = escape(o['title'])
        url = escape(o['url'], quote=True)
        msg = (f"REFERENCIA DE PRECIOS (SEPA): {o['title']}\nPrecio informado: {fmt_money(o['price_ars'])} ARS\nBaja frente a mediana registrada: {o['drop_pct']}%\nNo es enlace de compra. Sujeto a sucursal, condiciones y disponibilidad.\nFuente: SEPA (Argentina)\n{o['url']}" if o['source']=='sepa' else f"OFERTA PARA REVISAR: {o['title']}\nPrecio observado: {fmt_money(o['price_ars'])} ARS\nBaja frente a mediana registrada: {o['drop_pct']}%\nVerificar precio, stock y envío antes de comprar.\n{o['url']}")
        payload = escape(json.dumps(msg, ensure_ascii=False), quote=True)
        offer_rows.append(f'<tr><td><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></td>'
                          f'<td>{escape(o["source"])}</td><td>{fmt_money(o["price_ars"])}</td>'
                          f'<td><span class="discount">−{float(o["drop_pct"]):.1f}%</span></td>'
                          f'<td>{escape(o["detected_at"][:16].replace("T", " "))} UTC</td>'
                          f'<td><button class="copy" data-text="{payload}">Copiar mensaje</button></td></tr>')
    prod_rows = []
    for p in products:
        pid = escape(p['listing_id'])
        url = escape(p['url'], quote=True)
        prod_rows.append(f'<tr><td><a href="{url}" target="_blank" rel="noopener noreferrer">{escape(p["title"][:90])}</a><small>{pid}</small></td>'
                         f'<td>{escape(p["source"])}</td><td>{fmt_money(p["price_ars"])}</td>'
                         f'<td>{line_svg(series[p["listing_id"]])}</td><td>{escape(p["captured_at"][:16].replace("T", " "))} UTC</td></tr>')
    runs_rows=[]
    for r in sorted(runs, key=lambda x: x['started_at'], reverse=True)[:35]:
        status = escape(r['status'])
        note = escape(str(r.get('error',''))[:180])
        runs_rows.append(f'<tr><td>{escape(r["started_at"][:19].replace("T", " "))} UTC</td><td><span class="state">{status}</span></td><td>{r.get("observations_count",0)}</td><td>{r.get("offers_count",0)}</td><td>{note}</td></tr>')
    since = escape(first[:10] if first else '—')
    until = escape(last[:10] if last else '—')
    empty = '<tr><td colspan="6" class="empty">Nenhum registro disponível ainda.</td></tr>'
    doc = f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>PromoRadar AR — {escape(heading)}</title>
<style>
:root {{font-family: Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#18283e;background:#f5f8fc}}
*{{box-sizing:border-box}} body{{margin:0}} .container{{max-width:1180px;margin:0 auto;padding:36px 22px 80px}}
header{{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:28px}}
.brand{{display:flex;align-items:center;gap:10px;font-size:22px;font-weight:780;letter-spacing:-.7px}}
.mark{{background:#1575e9;color:white;border-radius:11px;padding:9px 11px;font-size:15px}}
nav a{{color:#326197;text-decoration:none;font-size:14px;margin-left:12px}}h1{{letter-spacing:-1.5px;font-size:clamp(30px,4.2vw,48px);line-height:1.1;margin:0 0 12px}}
h2{{font-size:21px;letter-spacing:-.4px;margin:0 0 18px}}.intro{{max-width:830px;color:#5a6980;line-height:1.7;margin:0 0 22px}}
.banner{{display:inline-block;color:#124d8d;background:#e8f2ff;border:1px solid #c9e0fc;border-radius:20px;padding:7px 12px;font-weight:700;font-size:11px;letter-spacing:.7px;margin-bottom:18px}}
.smallprint{{font-size:13px;color:#708197;margin:8px 0 30px}}.stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:24px 0 32px}}
.stat{{background:white;border:1px solid #e4eaf2;border-radius:15px;padding:24px;box-shadow:0 6px 20px #122b4805}}.stat-val{{font-size:29px;letter-spacing:-1px;font-weight:800}}.stat-name{{color:#708197;margin-top:6px;font-size:13px}}
section{{background:white;padding:24px;border:1px solid #e4eaf2;border-radius:17px;margin-top:18px;box-shadow:0 6px 20px #122b4804}}.tbl{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:13px;text-align:left}}
th{{color:#697d92;font-weight:650;font-size:11px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #dce5ef;padding:13px 11px;white-space:nowrap}}
td{{border-bottom:1px solid #edf1f6;padding:13px 11px;vertical-align:middle}}td a{{color:#175fae;text-decoration:none;font-weight:600}}td small{{color:#9caabc;display:block;margin-top:4px}}
.discount{{color:#167547;background:#edf9f0;padding:5px 9px;border-radius:7px;font-weight:750}}.spark{{width:135px;height:48px}}
.copy{{border:0;border-radius:8px;background:#e8f2ff;color:#1359a2;font-size:12px;padding:9px 12px;cursor:pointer;white-space:nowrap;font-weight:650}}
.state{{border-radius:7px;background:#f0f4f8;padding:5px 9px;display:inline-block}}.empty{{color:#8191a2;padding:27px}}.subtle{{color:#8391a2;font-size:12px}}
footer{{margin-top:24px;font-size:13px;color:#7b8da3;line-height:1.65}}
@media (max-width:750px){{.container{{padding:20px 14px 40px}}.stats{{grid-template-columns:repeat(2,minmax(0,1fr))}}.stat{{padding:16px}}.stat-val{{font-size:24px}}section{{padding:18px}}}}
</style></head><body><div class="container"><header><div class="brand"><span class="mark">PR</span> PromoRadar <span style="color:#8899aa">AR</span></div>
<nav><a href="./index.html">Datos reales</a><a href="./demo.html">Demostración</a><a href="./catalogo.html">Catálogo de ofertas</a></nav></header>
<main><span class="banner">{escape(data_flag)}</span><h1>{escape(heading)}</h1>
<p class="intro">Seguimiento de precios en Argentina. La variación se calcula sobre observaciones guardadas, no sobre el precio tachado en los comercios. Precios sin envío ni cupones, salvo indicación contraria.</p>
<p class="smallprint">Primer registro: {since} · Último registro: {until} · Actualización del sitio: {escape(datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))}</p>
<div class="stats">{stats}</div>
<section><h2>Oportunidades detectadas</h2><div class="tbl"><table><thead><tr><th>Producto</th><th>Tienda</th><th>Precio ARS</th><th>Variación</th><th>Fecha</th><th>WhatsApp (manual)</th></tr></thead><tbody>{''.join(offer_rows) or empty}</tbody></table></div></section>
<section><h2>Productos monitoreados</h2><div class="tbl"><table><thead><tr><th>Producto</th><th>Fuente</th><th>Último precio</th><th>Histórico</th><th>Última coleta</th></tr></thead><tbody>{''.join(prod_rows) or empty}</tbody></table></div></section>
<section><h2>Registro de ejecuciones</h2><div class="tbl"><table><thead><tr><th>Fecha</th><th>Estado</th><th>Observaciones</th><th>Ofertas</th><th>Detalle</th></tr></thead><tbody>{''.join(runs_rows) or empty}</tbody></table></div></section>
</main><footer>Proyecto académico de programación. Datos simulados y reales se encuentran estrictamente separados. Los enlaces son externos y pueden cambiar de precio. Fuentes de supermercados: SEPA (Secretaría de Comercio, Argentina), datos derivados por superprecios-claros. No hay publicación automática en WhatsApp.</footer>
</div><script>document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',async()=>{{try{{await navigator.clipboard.writeText(JSON.parse(b.dataset.text));b.textContent='Copiado';}}catch(e){{alert('Copiado no disponible; usa un navegador HTTPS.');}}}}));</script></body></html>'''
    DOCS.mkdir(exist_ok=True)
    filename = 'demo.html' if mode == 'demo' else 'index.html'
    (DOCS / filename).write_text(doc, encoding='utf-8')
    if mode == 'real':
        _export_csv(DOCS / 'runs.csv', runs, ['run_id','started_at','status','observations_count','offers_count','error'])
        _export_csv(DOCS / 'offers.csv', offers, ['offer_id','detected_at','source','listing_id','title','price_ars','baseline_median_ars','drop_pct','status','url'])
    return str(DOCS / filename)
