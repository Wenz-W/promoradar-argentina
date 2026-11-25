# PromoRadar Argentina — MVP acadêmico

## Início rápido — operar o grupo de WhatsApp (prioridade atual)

O catálogo web é secundário. **Não é necessário ativar GitHub Pages** para coletar preços ou revisar ofertas.

1. Em `Settings > Actions > General`, habilite Actions e, em `Workflow permissions`, permita `Read and write permissions` quando disponível. A coleta precisa gravar arquivos de histórico no repositório.
2. Em `Actions > Coleta de preços AR (6 meses) > Run workflow`, selecione `main` e execute. A execução agendada ocorre quatro vezes por dia, sem computador ligado.
3. Confira o resultado do workflow e baixe o artefato `promoradar-relatorios` (`runs.csv`, `offers.csv`, `ofertas.json`). Confirme **observações reais** e `source_status`: a fonte SEPA pode estar desatualizada ou indisponível.
4. A fonte SEPA fornece **preços regionais, não links de compra**; assim, por si só, não permite publicar ofertas comerciais em grupos. Para obter ofertas com link de compra, é necessário habilitar o conector Mercado Libre com OAuth autorizado, ou desenvolver outros conectores autorizados.
5. Depois de haver histórico suficiente (mínimo de sete dias de preços), use o `offer_id` de `docs/offers.csv` em `Actions > Revisar oferta (aprovação humana)` para aprovar a oferta. Copie a mensagem somente após revalidar o preço, estoque e link no marketplace.
6. Crie o grupo no aplicativo WhatsApp, configure `Somente administradores` para enviar mensagens e publique manualmente as ofertas aprovadas.

**A coleta em nuvem não foi ativada nem testada até existir uma execução bem-sucedida em Actions.** Nenhuma oferta deve ser anunciada como real sem preço e disponibilidade confirmados. O grupo e sua criação são externos ao GitHub.

---


Coletor agendado de preços, auditável por seis meses, com painel **estático** no GitHub Pages, custo de infraestrutura potencialmente zero nas cotas gratuitas. Desenvolvido para apresentar **resultados reais**, nunca para simular quatro/seis meses de observações inexistentes.

## O que foi implementado

- Coleta **sem credenciais** de preços de supermercados argentinos via API pública Superprecios Claros, com atribuição aos dados oficiais do SEPA e monitoramento de frescor.
- Coleta adicional via API oficial do Mercado Libre Argentina **quando houver acesso OAuth autorizado**.
- Execuções automáticas a cada 6 horas via GitHub Actions, independentes de PC ligado.
- Persistência de observações, ofertas e logs em JSONL por mês (commits no GitHub).
- Detecção de redução sobre **mediana de preços observados nos 30 dias anteriores** (mínimo 7 dias distintos e 7 amostras).
- Registro de falhas, revalidação básica de disponibilidade, prevenção de ofertas repetidas em intervalo curto.
- Dashboard HTML estático com resultados e gráficos, relatórios CSV, mensagens de WhatsApp para copiar manualmente.
- **Catálogo público independente** com busca, filtros, ordenação e histórico, alimentado pelas mesmas ofertas aprovadas (`docs/catalogo.html`); demonstração isolada (`docs/catalogo-demo.html`).
- Aprovação/rejeição humana pelo GitHub Actions com registro imutável de decisões (`data/real/reviews-*.jsonl`).
- Demonstração com dados **sintéticos totalmente separados** dos dados reais.
- Alertas de saúde via Action diário, falhando se não houve coleta válida em 30 horas.
- Renovação de credenciais Mercado Libre com arquivo criptografado, sem expor tokens no GitHub.

## Estrutura

```
.github/workflows/coleta.yml    # cron 4 vezes ao dia
.github/workflows/health.yml    # verifica falhas
promoradar/meli.py              # API oficial /sites/MLA/search
promoradar/sepa.py              # fonte pública SEPA / supermercados
promoradar/oauth.py             # renovação e armazenamento criptografado
promoradar/analytics.py         # algoritmo de descontos
promoradar/storage.py           # histórico JSONL mensal
promoradar/dashboard.py         # dashboard estático
config/settings.json            # parâmetros e palavras-chave
scripts/health_check.py         # auditoria
scripts/setup_credentials.py    # gera chave criptográfica
data/real/                      # registro real (inicialmente vazio)
data/demo/                      # exemplos sintéticos apenas
docs/index.html                 # dashboard real
docs/catalogo.html              # catálogo público (somente ofertas reais aprovadas)
docs/catalogo-demo.html         # catálogo sintético, com aviso visível
docs/catalogo.js + catalogo.css # filtros e interface
docs/ofertas.json               # feed público sanitizado
docs/demo.html                  # dashboard DEMO
```

## Testar imediatamente no computador

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/Mac: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m promoradar demo
python -m promoradar render
# Para aprovar uma oferta REAL já detectada:
# python -m promoradar review --offer-id ID_DA_OFERTA --decision approved
python -m http.server 8000 -d docs
```

Acesse `http://localhost:8000/demo.html` e `http://localhost:8000/catalogo-demo.html` para **dados sintéticos**, e `http://localhost:8000/index.html` e `http://localhost:8000/catalogo.html` para os painéis reais, que estarão vazios até iniciar a coleta e aprovar ofertas. Use o servidor HTTP local: abrir os arquivos com `file://` pode impedir o carregamento do JSON pelo navegador.

## Ativar execução na nuvem

1. Criar **novo** repositório GitHub (preferencialmente público para GitHub Pages gratuito no GitHub Free), por exemplo `promoradar-argentina`.
2. Enviar o conteúdo **desta pasta** à branch principal `main`, incluindo `.github/workflows` e `docs`.
3. GitHub: `Settings > Actions > General > Workflow permissions > Read and write permissions` (se essa opção estiver disponível). Revisar permissões e custos do plano.
4. GitHub: `Settings > Pages > Build and deployment > Source: GitHub Actions`. O workflow realiza o deploy direto a cada execução (push automático de `GITHUB_TOKEN` não aciona Pages em modo branch).
5. Em `Actions > Coleta de preços AR > Run workflow`, executar uma vez para validar o agendamento. **Sem credenciais do Mercado Libre**, o workflow ainda tentará a fonte pública SEPA. Confira `source_status` e o histórico: fontes públicas podem falhar ou estar desatualizadas.
6. O conector **SEPA já vem habilitado** e não exige credenciais. Mercado Libre vem desabilitado por padrão. No primeiro run, verifique se ele coletou preços recentes; fontes terceirizadas podem ficar desatualizadas. O conector Mercado Libre é opcional e exige OAuth e autorização para pesquisa. Para integrar Mercado Libre posteriormente, altere `mercadolibre.enabled` para `true` em `config/settings.json` depois de autorizar a API.
7. **Apenas se for integrar Mercado Libre:** adicionar os quatro secrets do repositório para integração persistente:
   - `MELI_CLIENT_ID`: id de aplicação autorizada.
   - `MELI_CLIENT_SECRET`: segredo da aplicação.
   - `MELI_INITIAL_REFRESH_TOKEN`: refresh token inicial obtido via OAuth oficial (de uso único).
   - `DATA_FERNET_KEY`: saída do comando `python scripts/setup_credentials.py`.
8. Após habilitar Mercado Libre, executar manualmente mais uma vez. A primeira renovação salva `data/private/meli_oauth.enc` **criptografado**, depois versionado; secrets jamais são escritos no painel, logs ou repositório.

**Atenção à rotação OAuth:** Mercado Libre usa access tokens de aproximadamente 6 horas e refresh tokens que devem ser substituídos após a renovação. A implementação guarda o par atualizado criptografado. Se a aplicação expirar, for revogada ou perder permissão, o programa registra falha, e será preciso autorizar novamente.

## Testar uma credencial temporária

Opcionalmente, apenas para uma execução **local**, defina `MELI_ACCESS_TOKEN` (não inclua no código/`.env` versionado) e execute `python -m promoradar all`. Esse token expira e **não serve** para seis meses na nuvem. Para operação duradoura, configure o fluxo completo acima.

## Quando haverá dados verdadeiros?

**Somente depois de:** (a) criar o repositório, (b) ativar Actions e Pages e (c) observar um primeiro run `ok` ou `partial` com observações válidas de SEPA (ou outra fonte autorizada). Para Mercado Libre, também precisamos de permissões e credenciais OAuth. A data inicial real será a do primeiro registro persistido, não a data de criação do projeto. A duração planejada é de **seis meses a partir dessa primeira coleta bem-sucedida**.

SEPA é uma fonte oficial de dados abertos, acessada aqui por meio da API agregada **de terceiros**, que pode parar de atualizar. O sistema verifica que a data do SEPA não esteja defasada mais que 3 dias. Região `CENTRO` inclui localidades da Província de Buenos Aires; `AMBA` na API cobre apenas CABA. Preços são medianas por rede/região, não necessariamente preços da unidade específica. A API **não é um link de compra**, e a disponibilidade de estoque não é confirmada.

Mercado Libre é uma integração **condicional**, pois algumas operações exigem escopos ou perfis específicos. Não assumimos que qualquer conta acadêmica terá acesso à busca. Shopee, Temu e SHEIN estão **explicitamente desativados**, até verificação de termos e feeds ou APIs permitidos. RAE pode auxiliar durante pesquisa técnica de APIs mas não concede autorização para endpoints internos.

## Restrições e qualidade da evidência

- GitHub Actions pode atrasar/omitir execuções agendadas. Logs mensais preservam a evidência dos runs executados e o monitor de saúde detecta ausência de sucesso, mas não garante SLA.
- Se publicarmos no GitHub Pages, tudo em `docs/` ficará público. Não guarde informações privadas ou tokens lá.
- `data/real/` não recebe amostras falsas; `data/demo/` contém exclusivamente dados sintéticos.
- Histórico requer observações reais por pelo menos 7 dias diferentes; antes disso, não há base suficiente para atestar `−15%`.
- Preço é o preço de anúncio visível via API, sem frete, cupom, região ou condição especial. Registrar contexto e não anunciar como “menor preço de mercado”.
- Os arquivos JSONL crescem a cada coleta. Com dezenas de milhares de linhas, usar um banco de dados gerenciado será preferível; o MVP acadêmico usa JSONL para reduzir custo.
- GitHub Pages não é um painel de administração autenticado. O botão “Copiar mensagem” é manual; a aprovação de ofertas é feita explicitamente por um workflow manual. A confirmação de envio ao WhatsApp continua manual e ainda não é registrada automaticamente.

## Validação de quatro/seis meses

Na data de apresentação, utilizar somente `data/real/` e `docs/runs.csv`/`docs/offers.csv` como evidências de observações, com vínculo aos commits datados e logs de execução. A demonstração sintética (`docs/demo.html`) deve ser marcada como tal.

## Documentações oficiais

- GitHub Actions schedule: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- GitHub Actions cobrança: https://docs.github.com/en/actions/concepts/billing-and-usage
- Dados abertos SEPA: https://www.argentina.gob.ar/economia/industria-y-comercio/defensadelconsumidor/precios-sepa
- API derivada Superprecios Claros (MIT): https://github.com/hysmarcos/superprecios-claros
- Mercado Libre autenticação: https://developers.mercadolibre.com.ar/es_ar/publica-productos/autenticacion-y-autorizacion
- Mercado Libre busca: https://developers.mercadolibre.com.ar/es_ar/servicios-consulta-usuarios/items-y-busquedas
- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site

## Auditoria de bibliotecas e reaproveitamento

Veja [Auditoria de repositorios](docs/REPOS_REAPROVEITAMENTO.md) para priorizacao, licencas, limitacoes e roteiro de incorporacao segura de projetos GitHub semelhantes.

## Catálogo público de promoções — fase inicial implementada

A página `docs/catalogo.html` mostra um **site público independente**, sem menções aos grupos de WhatsApp, com busca em texto, filtros por loja e categoria, preço mínimo e máximo, ordenação, preço atual, referência histórica, data da última verificação e histórico visual. O feed `docs/ofertas.json` vem **do mesmo histórico de observações e oportunidades**; não há coletor separado para o catálogo.

**Uma oferta só aparece se satisfizer todas as condições:**

- foi detectada por queda de preço documentada, possui `data_mode=real` e recebeu uma aprovação humana explícita;
- foi detectada nos últimos **7 dias**, está em estoque (segundo a última resposta da origem), teve preço revalidado há menos de **30 horas**, e o preço atual não subiu acima do preço aprovado;
- há um **link HTTPS comercial reconhecido** por fonte, isto é, pode levar ao produto em marketplace/loja; registros informativos do SEPA não são apresentados como ofertas clicáveis;
- se houver uma rejeição posterior, ela revoga a aprovação. Se o anúncio expirar ou ficar sem coleta, desaparece da próxima geração do site.

**Aprovar pelo GitHub sem instalar nada:** em `Actions > Revisar oferta (aprovação humana) > Run workflow`, copie o `offer_id` de `docs/offers.csv`, escolha `approved` ou `rejected` e execute. O workflow grava o evento de revisão, reconstrói `docs/ofertas.json` e publica o site no Pages. Para revisão local equivalente, execute `python -m promoradar review --offer-id ID --decision approved`; posteriormente envie os arquivos ao repositório.

**Importante:** a API SEPA fornece preços regionais, mas não links diretos de compra, e por isso não gera publicações no catálogo. O Mercado Libre requer OAuth e disponibilidade de API autorizada para preencher ofertas reais. No momento, `docs/ofertas.json` contém uma lista vazia — isso é correto, não é uma falha do gerador. Shopee, Temu e SHEIN ainda não estão integrados.

Para conferir o comportamento da interface sem dados externos, abra `docs/catalogo-demo.html`: os produtos e aprovações são *sintéticos* e ficam em `data/demo/`/`docs/ofertas-demo.json`; botões de compra permanecem desabilitados. **Jamais misturar esses registros com dados reais.**

O catálogo já funciona localmente, mas **não está publicado em uma URL pública** até a criação do repositório e ativação de Actions + GitHub Pages. Para reprodução da coleta por seis meses, o prazo deve ser contado da **primeira coleta real gravada**, não da criação do código. Detalhes e evoluções futuras: [Roadmap do catálogo web](docs/ROADMAP_CATALOGO_WEB.md).
