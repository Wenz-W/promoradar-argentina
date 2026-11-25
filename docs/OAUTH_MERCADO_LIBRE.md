# Conectar Mercado Libre ao PromoRadar (sem compartilhar segredos)

**Resultado esperado:** o GitHub Action troca um código OAuth de uso único por tokens, salva-os criptografados em `data/private/meli_oauth.enc`, habilita `mercadolibre` e desabilita a fonte SEPA atualmente desatualizada. A coleta de preços real só é confirmada depois de executar o coletor com sucesso.

## 1. Publicar a página de autorização HTTPS

- Em [Settings → Pages](https://github.com/Wenz-W/promoradar-argentina/settings/pages), selecione **Deploy from a branch**, branch **main**, pasta **/docs**, e salve.
- Confirme que abre: <https://wenz-w.github.io/promoradar-argentina/oauth.html>.
- A página não contém scripts de terceiros e não transmite códigos ou segredos. Ela valida `state` na mesma aba do navegador e remove o código da barra de endereço após o retorno.

## 2. Cadastrar uma aplicação Mercado Libre

- Abra o [DevCenter](https://developers.mercadolibre.com.ar/) e crie uma aplicação para **Mercado Libre** (não Mercado Pago).
- Use este **Redirect URI exatamente**: `https://wenz-w.github.io/promoradar-argentina/oauth.html`.
- Configure apenas permissões estritamente necessárias à leitura do catálogo; a disponibilidade de pesquisa para sua aplicação precisa ser validada.
- Copie o **APP ID** e **Client Secret** diretamente para [GitHub Actions Secrets](https://github.com/Wenz-W/promoradar-argentina/settings/secrets/actions), com os nomes `MELI_CLIENT_ID` e `MELI_CLIENT_SECRET` (sem colar no chat nem em commits).

## 3. Gerar chave de criptografia

- Abra a página `oauth.html`, clique em **Gerar chave** e copie o resultado para o GitHub Secret `DATA_FERNET_KEY`.
- **Preserve essa chave.** Se perdê-la, o arquivo criptografado de tokens não poderá ser decifrado e será necessário reconectar a conta.
- A chave gerada pelo navegador equivale a 32 bytes aleatórios codificados em base64 URL-safe, formato Fernet válido.

## 4. Autorizar e conectar

- Na mesma página, informe o **APP ID**; marque PKCE somente se esse fluxo estiver habilitado nas configurações do aplicativo.
- Clique em **Autorizar no Mercado Libre**, entre na sua conta e conceda autorização.
- Na página de retorno, copie o código para o Secret `MELI_AUTH_CODE`. Se utilizou PKCE, copie também o `code_verifier` para o Secret `MELI_CODE_VERIFIER`.
- Sem demora, vá a [Actions → Conectar Mercado Libre (OAuth seguro)](https://github.com/Wenz-W/promoradar-argentina/actions/workflows/conectar-meli.yml) e execute na branch `main`, mantendo `replace_existing=false` para a primeira conexão.
- O workflow realiza `POST https://api.mercadolibre.com/oauth/token` no servidor do GitHub. Os tokens não aparecem no painel nem nos logs.
- Quando concluir com sucesso, **apague os Secrets `MELI_AUTH_CODE` e `MELI_CODE_VERIFIER`**, pois já foram utilizados.

## 5. Validar a primeira coleta real

- Execute [Actions → Coleta de preços AR (6 meses)](https://github.com/Wenz-W/promoradar-argentina/actions/workflows/coleta.yml).
- Verifique o sumário e `docs/runs.csv`: `status=ok` ou `partial` com `observations_count > 0` e `source_status.mercadolibre=success`.
- Se ocorrer HTTP 403, a pesquisa não foi autorizada ou não está disponível para essa aplicação. Isso **não** deve ser contornado com endpoints privados ou coleta não autorizada.
- A primeira oferta real demanda histórico de pelo menos 7 dias distintos, preço confirmado, aprovação humana e link verificável.

## Requisitos e limitações

- O GitHub Pages é usado **somente como página auxiliar de autorização** nesta fase; o objetivo principal continua sendo o grupo de WhatsApp.
- O código OAuth é de uso único e tem prazo curto; obtenha-o apenas depois de criar os Secrets permanentes.
- Se a aplicação exigir PKCE, é preciso enviar `code_challenge` e, na troca, `code_verifier`.
- A rotação de refresh token é tratada por `promoradar/oauth.py`; o cofre criptografado é versionado, mas a chave criptográfica fica fora do repositório.
- Se quiser reconectar uma conta, gere novo código e execute o workflow com `replace_existing=true`. Isso substitui o cofre anterior: faça somente de forma consciente.

Fontes oficiais: [Criar uma aplicação](https://developers.mercadolibre.com.ar/es_ar/guia-para-servicios/crea-una-aplicacion-en-mercado-libre-es) e [OAuth](https://developers.mercadolibre.com.ar/es_ar/autenticacion-y-autorizacion/).
