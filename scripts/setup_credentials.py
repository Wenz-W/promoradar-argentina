"""Gerar chave Fernet para copiar em GitHub Actions Secrets."""
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode('ascii'))
print('COPIE para o secret DATA_FERNET_KEY. Nunca envie essa chave a chats, commits ou planilhas.')
