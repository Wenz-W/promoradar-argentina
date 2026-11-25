import io
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from cryptography.fernet import Fernet

from scripts import bootstrap_meli_oauth as bootstrap
from promoradar.oauth import CredentialError


class TestMercadoLibreBootstrap(unittest.TestCase):
    def test_missing_credentials_does_not_request_network(self):
        with self.assertRaises(CredentialError):
            bootstrap.exchange_authorization_code("", "secret", "code", bootstrap.CALLBACK_URL)

    def test_redirect_must_be_https_and_static(self):
        with self.assertRaises(CredentialError):
            bootstrap.exchange_authorization_code("123", "secret", "code", "http://localhost/callback")
        with self.assertRaises(CredentialError):
            bootstrap.exchange_authorization_code("123", "secret", "code", "https://example.org/?code=foo")

    def test_code_exchange_does_not_leak_secret_and_supports_pkce(self):
        response = {"access_token": "access", "refresh_token": "refresh", "expires_in": 21600}
        class FakeResponse(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *_): return None
        with patch.object(bootstrap, "urlopen", return_value=FakeResponse(json.dumps(response).encode())) as network:
            result = bootstrap.exchange_authorization_code("app", "secret", "one-time-code", bootstrap.CALLBACK_URL, "verifier")
            posted = network.call_args.args[0].data.decode()
        self.assertEqual(result["refresh_token"], "refresh")
        self.assertIn("code_verifier=verifier", posted)
        self.assertIn("grant_type=authorization_code", posted)

    def test_save_encrypted_connection_activates_meli_and_disables_stale_sepa(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            vault = root / "vault.enc"
            settings = root / "settings.json"
            settings.write_text(json.dumps({"mercadolibre": {"enabled": False}, "sepa": {"enabled": True}}))
            key = Fernet.generate_key().decode()
            with patch.dict(os.environ, {"DATA_FERNET_KEY": key}):
                bootstrap.save_connection({"access_token":"access", "refresh_token":"refresh", "expires_in":3600}, vault, settings)
                with self.assertRaises(CredentialError):
                    bootstrap.save_connection({"access_token":"access", "refresh_token":"refresh"}, vault, settings)
            self.assertNotIn(b"refresh", vault.read_bytes())
            decrypted = json.loads(Fernet(key).decrypt(vault.read_bytes()))
            self.assertEqual(decrypted["access_token"], "access")
            cfg = json.loads(settings.read_text())
            self.assertTrue(cfg["mercadolibre"]["enabled"])
            self.assertFalse(cfg["sepa"]["enabled"])

if __name__ == "__main__":
    unittest.main()
