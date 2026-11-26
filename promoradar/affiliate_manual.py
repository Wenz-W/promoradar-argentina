"""Candidatos manuais para WhatsApp (links fornecidos pelo afiliado).

NÃO são observações de preço da API nem descontos históricos detectados.
O redirecionamento/atribuição do link curto NÃO é verificado pelo programa.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit
import re

from .storage import DATA, append_jsonl, read_series, utcnow


class ManualAffiliateError(ValueError):
    pass


def normalize_price(value: str | float | int) -> Decimal:
    raw = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,10}(?:\.[0-9]{1,2})?", raw):
        raise ManualAffiliateError('Preço inválido. Use 24999 ou 24999.90, sem separador de milhares.')
    try:
        price = Decimal(raw)
    except InvalidOperation as exc:
        raise ManualAffiliateError('Preço inválido.') from exc
    if price < Decimal('1') or price > Decimal('999999999.99'):
        raise ManualAffiliateError('Preço fora do intervalo permitido.')
    return price.quantize(Decimal('0.01'))


def validate_affiliate_url(raw: str) -> str:
    """Aceita SOMENTE link curto meli.la enviado pelo afiliado; sem reescrita."""
    url = str(raw)
    if not url or url != url.strip() or any(c.isspace() for c in url):
        raise ManualAffiliateError('URL inválida; copie o link de afiliado diretamente do Mercado Libre.')
    try:
        p = urlsplit(url)
        if (p.scheme != 'https' or p.hostname != 'meli.la'
                or p.netloc != 'meli.la' or p.username or p.password
                or p.query or p.fragment or not re.fullmatch(r'/[A-Za-z0-9_-]{5,48}', p.path)):
            raise ManualAffiliateError('Por segurança, use um link https://meli.la/... gerado na sua conta.')
    except ValueError as exc:
        raise ManualAffiliateError('URL de afiliado malformada.') from exc
    return url


def clean_label(raw: str, *, label: str, min_len: int = 3, max_len: int = 160) -> str:
    value = re.sub(r'\s+', ' ', str(raw)).strip().replace('`','').replace('*','')
    if not min_len <= len(value) <= max_len or any(ord(c) < 32 for c in value):
        raise ManualAffiliateError(f'{label} deve ter entre {min_len} e {max_len} caracteres.')
    return value


def create_candidate(title: str, price_ars: str, affiliate_url: str,
                     *, when: datetime | None = None) -> dict:
    """Um cadastro NÃO prova preço ou estoque e nunca afirma desconto percentual."""
    moment = (when or utcnow()).astimezone(timezone.utc)
    safe_title = clean_label(title, label='Título')
    price = normalize_price(price_ars)
    link = validate_affiliate_url(affiliate_url)
    unique = f'{link}|{moment.date().isoformat()}|{safe_title}|{price}'
    return {
        'candidate_id': 'AF-' + sha256(unique.encode()).hexdigest()[:12].upper(),
        'recorded_at': moment.isoformat(),
        'source': 'mercadolibre', 'product_title': safe_title,
        'price_ars': float(price), 'currency': 'ARS',
        'affiliate_url': link,
        'status': 'awaiting_manual_price_and_stock_check',
        'evidence_type': 'operator_submitted_not_independently_verified',
        'historical_discount_verified': False,
        'data_mode': 'real_manual_candidate',
    }


def save_candidate(candidate: dict, *, data_dir: Path | None = None) -> bool:
    root = data_dir if data_dir is not None else DATA / 'real'
    file = root / f"affiliate-candidates-{candidate['recorded_at'][:7]}.jsonl"
    return append_jsonl(file, [candidate], 'candidate_id') == 1


def display_price(price_ars: float) -> str:
    formatted = f'{float(price_ars):,.2f}'
    return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')


def make_whatsapp_draft(candidate: dict) -> str:
    return (
        '🛍️ *PROMORADAR AR*\n'
        f"*{candidate['product_title']}*\n\n"
        f"💰 *Precio informado:* $ {display_price(candidate['price_ars'])}\n"
        f"🔗 *Ver producto:* {candidate['affiliate_url']}\n\n"
        '⚠️ Revisá precio, disponibilidad y condiciones antes de comprar.\n'
        'ℹ️ Enlace de afiliado.'
    )


def get_candidate(candidate_id: str, *, records: list[dict] | None = None) -> dict:
    records = read_series('affiliate-candidates','real') if records is None else records
    found = [r for r in records if r.get('candidate_id') == candidate_id]
    if not found:
        raise ManualAffiliateError('Candidato inexistente. Consulte a saída do workflow Preparar oferta.')
    return found[-1]


def mark_published(candidate_id: str, confirmed_price_ars: str, channel: str,
                   *, confirmed: bool, when: datetime | None = None,
                   data_dir: Path | None = None) -> dict:
    if not confirmed:
        raise ManualAffiliateError('Confirme que verificou preço, estoque, destino do link e enviou a mensagem.')
    root = data_dir if data_dir is not None else DATA / 'real'
    if data_dir is None:
        candidate = get_candidate(candidate_id)
        previous = read_series('affiliate-publications', 'real')
    else:
        from .storage import read_jsonl
        candidate = get_candidate(candidate_id, records=[r for f in sorted(root.glob('affiliate-candidates-*.jsonl')) for r in read_jsonl(f)])
        previous = [r for f in sorted(root.glob('affiliate-publications-*.jsonl')) for r in read_jsonl(f)]
    verified_price = normalize_price(confirmed_price_ars)
    if verified_price != normalize_price(str(candidate['price_ars'])):
        raise ManualAffiliateError('O preço mudou. Prepare um novo candidato com o preço atualizado.')
    channel = clean_label(channel, label='Nome do grupo/canal', min_len=2, max_len=80)
    if any(r.get('candidate_id') == candidate_id and r.get('channel') == channel for r in previous):
        raise ManualAffiliateError('Este candidato já foi marcado como publicado neste grupo.')
    moment = (when or utcnow()).astimezone(timezone.utc)
    event = {
        'publication_id': 'PUB-' + sha256(f'{candidate_id}|{channel}'.encode()).hexdigest()[:12].upper(),
        'candidate_id': candidate_id, 'channel': channel,
        'reported_published_at': moment.isoformat(),
        'confirmed_price_ars': float(verified_price),
        'affiliate_url': candidate['affiliate_url'],
        'confirmation_type': 'operator_attested_sent_and_checked',
        'data_mode': 'real_manual_self_report',
    }
    file = root / f"affiliate-publications-{moment.strftime('%Y-%m')}.jsonl"
    append_jsonl(file, [event], 'publication_id')
    return event
