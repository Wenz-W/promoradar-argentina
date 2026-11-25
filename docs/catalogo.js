/* Catálogo estático: só utiliza o feed sanitizado e público ofertas*.json. */
(() => {
  'use strict';
  const root = document.body;
  const mode = root.dataset.mode || 'real';
  const source = mode === 'demo' ? './ofertas-demo.json' : './ofertas.json';
  const el = id => document.getElementById(id);
  const list = el('listing');
  const controls = ['q','store','category','min','max','sort'].map(el);
  const money = v => new Intl.NumberFormat('es-AR',{style:'currency',currency:'ARS',maximumFractionDigits:0}).format(v);
  const day = raw => {const d=new Date(raw);return Number.isNaN(d.valueOf())?'—':new Intl.DateTimeFormat('es-AR',{day:'2-digit',month:'short',year:'numeric',timeZone:'America/Argentina/Buenos_Aires'}).format(d)};
  const dateTime = raw => {const d=new Date(raw);return Number.isNaN(d.valueOf())?'—':new Intl.DateTimeFormat('es-AR',{dateStyle:'medium',timeStyle:'short',timeZone:'America/Argentina/Buenos_Aires'}).format(d)};
  const safeLink = value => {try{const u=new URL(value);return u.protocol==='https:'?u.href:null}catch{return null}};
  const text = (tag, className, value) => {const n=document.createElement(tag);if(className)n.className=className;n.textContent=value;return n};
  let catalog = [];

  function chart(history){
    const clean = (Array.isArray(history)?history:[]).filter(r=>Number.isFinite(r.price_ars)&&r.price_ars>0).slice(-40);
    if(clean.length<2)return text('p','', 'Todavía no hay datos suficientes para mostrar el historial.');
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 310 90');svg.setAttribute('role','img');svg.setAttribute('aria-label','Historial de precios observado');svg.classList.add('spark');
    const prices=clean.map(r=>r.price_ars);const low=Math.min(...prices);const high=Math.max(...prices);
    const points=prices.map((v,i)=>`${(8+i*294/(prices.length-1)).toFixed(1)},${(80-(v-low)/(high-low||1)*68).toFixed(1)}`).join(' ');
    const poly=document.createElementNS('http://www.w3.org/2000/svg','polyline');poly.setAttribute('points',points);svg.append(poly);return svg;
  }
  function card(o){
    const article=document.createElement('article');article.className='offer-card';
    const top=text('div','card-top','');top.append(text('span','store-pill',o.store||o.source||'Tienda'),text('span','discount',`−${Number(o.drop_pct||0).toLocaleString('es-AR',{maximumFractionDigits:1})}%`));article.append(top);
    article.append(text('div','product-art',''));
    const body=text('div','card-content','');body.append(text('div','category',o.category||'Productos'),text('h3','offer-title',o.title||'Producto sin título'));
    body.append(text('div','price',money(o.price_ars)));
    const p=text('div','reference','Referencia histórica: ');const s=document.createElement('s');s.textContent=money(o.historical_reference_ars);p.append(s);body.append(p);
    body.append(text('div','verify',`Verificado: ${dateTime(o.last_verified_at)}`));
    const actions=text('div','card-actions','');const link=text('a','go','Ver en tienda');const href=safeLink(o.url);
    if(mode==='demo'||!href){link.classList.add('disabled');link.textContent='Ejemplo — sin compra';link.setAttribute('aria-disabled','true');link.removeAttribute('href')}
    else{link.href=href;link.target='_blank';link.rel='noopener noreferrer sponsored'}
    const button=text('button','history-toggle','Historial');button.type='button';button.setAttribute('aria-expanded','false');actions.append(link,button);body.append(actions);article.append(body);
    const history=text('div','history-box','');history.append(text('p','',`Últimas ${Math.min(40,(o.history||[]).length)} observaciones registradas:`),chart(o.history),text('p','','El histórico no incluye el costo de envío ni garantiza disponibilidad en tu zona.'));
    article.append(history);button.addEventListener('click',()=>{const open=history.classList.toggle('open');button.setAttribute('aria-expanded',String(open));button.textContent=open?'Ocultar':'Historial'});return article;
  }
  function update(){
    const q=el('q').value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
    const store=el('store').value,category=el('category').value;
    const min=Number(el('min').value||0),max=Number(el('max').value||Infinity);
    let selected=catalog.filter(o=>{
      const bag=[o.title,o.store,o.category].join(' ').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
      return (!q||bag.includes(q))&&(!store||o.store===store)&&(!category||o.category===category)&&o.price_ars>=min&&o.price_ars<=max;
    });
    const sort=el('sort').value;
    selected.sort((a,b)=>sort==='price-low'?a.price_ars-b.price_ars:sort==='price-high'?b.price_ars-a.price_ars:sort==='recent'?new Date(b.detected_at)-new Date(a.detected_at):b.drop_pct-a.drop_pct);
    list.replaceChildren();
    if(!selected.length){const box=text('div','empty','');box.append(text('h3','','No encontramos ofertas con estos filtros'),text('p','',catalog.length?'Probá quitar algún filtro o buscar por otra palabra.':'Todavía no hay ofertas reales, aprobadas y vigentes. Volvé a consultar más adelante.'));list.append(box)}
    else{const batch=document.createDocumentFragment();selected.forEach(o=>batch.append(card(o)));list.append(batch)}
    el('result-count').textContent=`${selected.length} ${selected.length===1?'oferta disponible':'ofertas disponibles'}`;
  }
  function fillSelect(id,key){const options=[...new Set(catalog.map(o=>o[key]).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'es'));
    options.forEach(value=>{const opt=document.createElement('option');opt.value=value;opt.textContent=value;el(id).append(opt)})}
  async function load(){
    try{
      const response=await fetch(source,{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const feed=await response.json();if(feed.mode!==mode||!Array.isArray(feed.offers))throw new Error('Datos incompatibles');
      // Defence in depth against accidentally publishing demo or pending records in the public catalog.
      catalog=feed.offers.filter(o=>o.status==='active'&&o.is_demo===(mode==='demo')&&Number.isFinite(o.price_ars)&&o.price_ars>0);
      el('updated-at').textContent=feed.generated_at?`Actualizado: ${dateTime(feed.generated_at)}`:'Actualización pendiente';
      el('stat-offers').textContent=String(catalog.length);
      el('stat-stores').textContent=String(new Set(catalog.map(o=>o.store)).size);
      fillSelect('store','store');fillSelect('category','category');update();
    }catch(err){list.replaceChildren();const box=text('div','empty','');box.append(text('h3','','No se pudo cargar el catálogo'),text('p','','El archivo de ofertas no está disponible. Volvé a intentarlo más tarde.'));list.append(box);el('result-count').textContent='Sin datos';}
  }
  controls.forEach(control=>control.addEventListener(['q','min','max'].includes(control.id)?'input':'change',update));
  el('reset').addEventListener('click',()=>{controls.forEach(c=>c.value='');el('sort').value='discount';update()});
  load();
})();
