# Auditoria de repositórios — PromoRadar Argentina

Pesquisa realizada em 23/11/2026. Objetivo: selecionar componentes para reaproveitamento no MVP acadêmico de seis meses, executado no GitHub Actions com custo fixo zero dentro das cotas gratuitas.

## Seleção por finalidade

| Repositório | O que oferece | Licença observada | Decisão |
|---|---|---|---|
| [superprecios-claros](https://github.com/hysmarcos/superprecios-claros) | Fonte pública de preços argentinos SEPA | Consultar LICENSE e termos da API antes de reutilizar trechos | Fonte complementar já integrada ao MVP; checar atualização dos dados |
| [Bot-Cazador-De-Ofertas](https://github.com/BenjaminGaelSerrano/Bot-Cazador-De-Ofertas) | Monitoramento de lojas argentinas, GitHub Actions, histórico e dedup | Sem arquivo LICENSE na raiz na data da auditoria | Referência de design; pedir permissão para copiar código |
| [sistema-de-achadinhos](https://github.com/goul4rt/sistema-de-achadinhos) | Coleta, watchlists, score, dedup, API e webhook | Não foi identificada licença; projeto jovem, um commit visível | Referência de funcionalidades; não copiar código sem licença/permissão |
| [smart-affiliate-bot](https://github.com/acellesantos/smart-affiliate-bot) | Curadoria, RPA e publicação em grupos | Sem arquivo LICENSE na raiz na data da auditoria | Referência conceitual; não reutilizar diretamente código |
| [EcomPulse](https://github.com/Aaron-Bushnell/ecompulse) | Adaptadores de Shopee/Temu, séries históricas, relatórios | MIT | Avaliar/adaptar modelos de dados e relatórios; validar cada loja e autorização de acesso |
| [PriceDrop Tracker](https://github.com/daffaroffi/price-drop-tracker) | Captura de preço em extensão, SQLite, dashboard e alertas | MIT | Reaproveitamento pontual possível para histórico, dashboard e cooldown; extensão exige navegador aberto |
| [Garimpo](https://github.com/LeoFabri1/garimpo) | Estatísticas robustas de preços, MAD/medianas e limiares | MIT | Adaptar ideias do motor de pontuação e testes; não exigir Telegram |
| [Gwibot](https://github.com/DavidSouzaLD/Gwibot) | Painel, dedup, mensagens e fila de distribuição | MIT | Avaliar interface e templates; WhatsApp não é envio oficial a grupos e integração declarada é preparatória |
| [changedetection.io](https://github.com/dgtlmoon/changedetection.io) | Monitoramento genérico de páginas, CSS/XPath, alertas | Apache-2.0 | Alternativa futura; autohospedagem 24/7 custa infraestrutura ou demanda servidor existente |
| [temu-scraper](https://github.com/omkarcloud/temu-scraper) | Dados detalhados de Temu | MIT | Não integrar neste MVP até validar região Argentina e permissões de acesso; README menciona US/UK/Canada |
| [meli-price-tracker](https://github.com/Lazaro549/meli-price-tracker) | GitHub Actions + painel histórico do Mercado Libre | README indica MIT, repo arquivado | Referência de arquitetura, mas não usar como base ativa |

### Nota sobre GitHub Actions — Cazador de Ofertas

O README descreve duas corridas por dia, mas o arquivo `.github/workflows/cazador.yml` consultado na auditoria possuía **12 expressões cron diárias**, uma a cada duas horas. Não assumir que o README representa a configuração atual de execução. O workflow emprega `concurrency` e uma branch `datos` para histórico; nosso MVP já tem mecanismos análogos de logs e persistência.

## Critérios de incorporação

1. Não copiar código de repositórios sem licença explícita/autorizações do titular. Repositório público não implica autorização de modificação ou redistribuição.
2. Para códigos MIT/Apache-2.0, manter aviso de copyright, texto de licença e notas de atribuição exigidas pela licença.
3. Verificar com testes por fonte, especialmente locale Argentina, ARS, variantes, frete e estoque; não usar mecanismos para contornar autenticação ou restrições técnicas das plataformas.
4. Manter `data/real` e `data/demo` separados. Nunca retroagir datas nem apresentar demos como histórico de seis meses.
5. A integração com WhatsApp continua por mensagem pré-preenchida e confirmação manual do administrador; não depender de WhatsApp Web não oficial no GitHub Actions.

## Sequência de aproveitamento no nosso MVP

**Primeiro:** adaptar como lógica própria as *watchlists* (filtros de categoria, palavras-chave, mínimo/máximo, cupom) e a pontuação explicável inspiradas em `sistema-de-achadinhos`. Criar testes próprios, sem copiar código do repositório sem licença.

**Segundo:** aperfeiçoar métricas para o relatório de seis meses, aproveitando padrões de `EcomPulse` (produto novo, retirada, mudanças entre observações) e `Garimpo` (estatísticas robustas, mínimo de evidências, confiança baixa quando histórico é curto). Licenças permitem reuse com atribuição.

**Terceiro:** avaliar conectores Shopee/Temu em isolamento, mantendo coleta desabilitada enquanto não houver autorização e validação dos dados argentinos. EcomPulse e PriceDrop Tracker foram originalmente desenvolvidos para outros mercados, não devendo ser considerados integração pronta para Argentina.

**Quarto:** só então desenvolver aprovação e mensagens WhatsApp. O grupo continua manual, enquanto coleta e relatórios rodam na nuvem.

## Limitações das fontes

- Superprecios Claros/SEPA é fonte de preços de supermercados, não garante estoque e não oferece necessariamente link direto de compra. Preços medianos regionais não equivalem a promoção verificada de loja específica.
- Em Argentina, comparar valores nominais por 180 dias pode ser enganoso em razão da variação geral de preços; o relatório deve diferenciar queda nominal, queda relativa a histórico recente e competitividade frente a lojas comparáveis.
- Playwright, RAE e scrapers de terceiros não tornam automaticamente autorizados os endpoints privados ou coletados.

## Fontes

- https://github.com/hysmarcos/superprecios-claros
- https://github.com/BenjaminGaelSerrano/Bot-Cazador-De-Ofertas
- https://github.com/goul4rt/sistema-de-achadinhos
- https://github.com/acellesantos/smart-affiliate-bot
- https://github.com/Aaron-Bushnell/ecompulse
- https://github.com/daffaroffi/price-drop-tracker
- https://github.com/LeoFabri1/garimpo
- https://github.com/DavidSouzaLD/Gwibot
- https://github.com/dgtlmoon/changedetection.io
- https://github.com/omkarcloud/temu-scraper
- https://github.com/Lazaro549/meli-price-tracker
