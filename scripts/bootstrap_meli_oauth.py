"""Inicialização OAuth de uso único do Mercado Libre dentro do GitHub Actions.

Nunca imprima authorization codes, client secrets, access tokens ou refresh tokens.
O redirect_uri HTTPS deve ser o mesmo cadastrado no DevCenter e usado na autorização.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import json
import os

from promoradar.oauth import CredentialError, TOKEN_FILE, _fernet
from promoradar.storage import BASE

SETTINGS = BASE / "config" / "settings.json"
CALLBACK_URL = "https://wenz-w.github.io/promoradar-argentina/oauth.html"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"


def exchange_authorization_code(client_id: str, client_secret: str, code: str,
                                redirect_uri: str, code_verifier: str = "") -> dict:
    """Troca código por tokens sem expor informações sensíveis nos erros."""
    if not client_id or not client_secret or not code:
        raise CredentialError("Faltam MELI_CLIENT_ID, MELI_CLIENT_SECRET ou MELI_AUTH_CODE nos Secrets.")
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise CredentialError("MELI_REDIRECT_URI deve ser um endereço HTTPS estático e exato.")
    body = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    if code_verifier:
        body["code_verifier"] = code_verifier
    request = Request(
        TOKEN_URL, data=urlencode(body).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise CredentialError(f"Mercado Libre recusou a autorização (HTTP {exc.code}). Confirme código novo, PKCE e redirect URI.") from None
    except (URLError, TimeoutError, ValueError):
        raise CredentialError("Falha de conexão ou resposta inválida no OAuth do Mercado Libre.") from None
    if not isinstance(payload, dict) or not payload.get("access_token") or not payload.get("refresh_token"):
        raise CredentialError("A autorização não retornou access_token e refresh_token.")
    return payload


def save_connection(payload: dict, vault: Path = TOKEN_FILE, settings_path: Path = SETTINGS,
                    replace_existing: bool = False) -> None:
    """Persiste estado criptografado e habilita a fonte apenas após OAuth concluído."""
    if vault.exists() and not replace_existing:
        raise CredentialError("Já existe um OAuth criptografado. Para reconectar, habilite replace_existing manualmente.")
    fer = _fernet()
    cfg = json.loads(settings_path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    record = {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "expires_at": (now + timedelta(seconds=max(60, int(payload.get("expires_in", 21600))))).isoformat(),
    }
    vault.parent.mkdir(parents=True, exist_ok=True)
    tmp = vault.with_suffix(".tmp")
    tmp.write_bytes(fer.encrypt(json.dumps(record).encode("utf-8")))
    tmp.replace(vault)
    cfg.setdefault("mercadolibre", {})["enabled"] = True
    # A fonte SEPA do agregador está desatualizada; evitar que invalide coletas ML atuais.
    cfg.setdefault("sepa", {})["enabled"] = False
    settings_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    try:
        redirect = os.getenv("MELI_REDIRECT_URI", CALLBACK_URL).strip() or CALLBACK_URL
        if redirect != CALLBACK_URL:
            raise CredentialError("Redirect URI diferente do callback do PromoRadar; ajuste o cadastro no DevCenter.")
        vault = TOKEN_FILE
        replace_existing = os.getenv("MELI_REPLACE_EXISTING", "false").lower() == "true"
        if vault.exists() and not replace_existing:
            raise CredentialError("OAuth já configurado. Use replace_existing=true apenas para reconectar.")
        # Valida chave ANTES de consumir um authorization_code (uso único).
        _fernet()
        if not SETTINGS.exists():
            raise CredentialError("Arquivo de configuração indisponível.")
        cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
        if "mercadolibre" not in cfg:
            raise CredentialError("Configuração mercadolibre ausente.")
        data = exchange_authorization_code(
            os.getenv("MELI_CLIENT_ID", "").strip(),
            os.getenv("MELI_CLIENT_SECRET", "").strip(),
            os.getenv("MELI_AUTH_CODE", "").strip(),
            redirect,
            os.getenv("MELI_CODE_VERIFIER", "").strip(),
        )
        save_connection(data, vault, SETTINGS, replace_existing)
        print("OAuth Mercado Libre salvo de forma criptografada. Fonte Mercado Libre ativada; SEPA desativada.")
        return 0
    except CredentialError as exc:
        print(f"Falha de configuração OAuth: {exc}")
        return 2
    except (OSError, ValueError, KeyError, TypeError):
        print("Falha ao salvar configuração OAuth. Tokens não foram exibidos.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
