"""Tokens OAuth do Mercado Libre guardados criptografados para rotação entre GitHub Actions.

O arquivo criptografado pode ser versionado; a chave Fernet NUNCA deve ser versionada.
A rotação usa refresh token de uso único conforme documentação oficial.
"""
from __future__ import annotations
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet, InvalidToken
import os
import json

TOKEN_FILE = Path(__file__).resolve().parent.parent / 'data' / 'private' / 'meli_oauth.enc'

class CredentialError(Exception):
    pass


def _fernet():
    key = os.getenv('DATA_FERNET_KEY', '')
    if not key:
        raise CredentialError('DATA_FERNET_KEY não configurada.')
    try:
        return Fernet(key.encode('ascii'))
    except (ValueError, TypeError) as e:
        raise CredentialError('DATA_FERNET_KEY inválida.') from e


def get_access_token() -> str:
    """Retorna token autorizado ou solicita refresh, persistindo novos tokens com cifra."""
    standalone = os.getenv('MELI_ACCESS_TOKEN', '').strip()
    if standalone:
        return standalone  # Só para testes temporários; expira e não sustenta 6 meses.
    app_id = os.getenv('MELI_CLIENT_ID', '').strip()
    secret = os.getenv('MELI_CLIENT_SECRET', '').strip()
    initial_refresh = os.getenv('MELI_INITIAL_REFRESH_TOKEN', '').strip()
    if not app_id or not secret:
        raise CredentialError('Falta MELI_CLIENT_ID/MELI_CLIENT_SECRET; modo real indisponível.')
    fer = _fernet()
    if TOKEN_FILE.exists():
        try:
            record = json.loads(fer.decrypt(TOKEN_FILE.read_bytes()))
        except (InvalidToken, json.JSONDecodeError) as e:
            raise CredentialError('Falha ao abrir vault criptografado. NÃO use token inicial novamente.') from e
    else:
        if not initial_refresh:
            raise CredentialError('Falta MELI_INITIAL_REFRESH_TOKEN para a primeira autorização.')
        record = {'refresh_token': initial_refresh, 'access_token': '', 'expires_at': ''}
    expires = record.get('expires_at', '')
    if record.get('access_token') and expires:
        expiry = datetime.fromisoformat(expires)
        if expiry > datetime.now(timezone.utc) + timedelta(minutes=30):
            return record['access_token']
    req = Request('https://api.mercadolibre.com/oauth/token',
                  data=urlencode({'grant_type': 'refresh_token', 'client_id': app_id,
                                  'client_secret': secret, 'refresh_token': record['refresh_token']}).encode(),
                  headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST')
    try:
        with urlopen(req, timeout=20) as res:
            payload = json.load(res)
    except Exception as e:
        raise CredentialError(f'Renovação OAuth falhou: {type(e).__name__}. Não prosseguiremos com token vencido.') from e
    if not payload.get('access_token') or not payload.get('refresh_token'):
        raise CredentialError('A resposta de renovação não trouxe os dois tokens exigidos.')
    expires_in = max(int(payload.get('expires_in', 21600)), 60)
    new_record = {'access_token': payload['access_token'], 'refresh_token': payload['refresh_token'],
                  'expires_at': (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()}
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = TOKEN_FILE.with_suffix('.tmp')
    temp.write_bytes(fer.encrypt(json.dumps(new_record).encode()))
    temp.replace(TOKEN_FILE)
    return new_record['access_token']
