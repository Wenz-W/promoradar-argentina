# PromoRadar AR — Gerador de links oficiais do Mercado Libre em lote

Versão: integração v0.3. **Não utiliza API de desenvolvedores para gerar links de afiliado.**

## Situação comprovada

O gerador do painel de afiliados da Argentina aceita várias URLs de produto, cada uma em uma linha, e devolve **links na mesma ordem**. Em teste fornecido pelo operador com a etiqueta `liwe4706506`:

| URL do produto | Link curto oficial informado pelo operador |
| --- | --- |
| `https://www.mercadolibre.com.ar/p/MLA67162330` | `https://meli.la/1pRAHdr` |
| `https://www.mercadolibre.com.ar/p/MLA65551248` | `https://meli.la/2BPrtmu` |

Ao gerar novamente uma URL repetida, o painel devolveu o mesmo link curto. Isso demonstra **reutilização observada nestes dois produtos**, não uma garantia universal nem prova de comissão creditada.

Os dois pares foram registrados em `data/real/affiliate-links-2026-11.jsonl` como **links fornecidos pelo operador**, não como preços coletados, compras verificadas ou comissões validadas.

## Fluxo de operação

1. O coletor autorizado encontra produtos no Mercado Libre e salva **observações reais** em `data/real/observations-AAAA-MM.jsonl`.
2. Abra [Actions > Exportar lote para gerador oficial de afiliados](https://github.com/Wenz-W/promoradar-argentina/actions/workflows/exportar-lote-afiliados.yml). Use a etiqueta da conta e um lote até 50 produtos. `max_items=20` é recomendado.
3. No run, baixe o artefato `lote-gerador-afiliados`. Ele contém:
   - `urls-para-gerador.txt`: URLs de produtos novos, **uma por linha, na ordem exata** para colar no gerador oficial;
   - `pendentes.csv`: posição, produto, preço observado e URL para conferir a associação;
   - `com-link-oficial.csv`: produtos que já têm um link no banco, que **não precisam de nova geração**;
   - `batch-id.txt`: ID `AB-...` do lote. O manifesto de correspondência é guardado em `data/real/affiliate-batches/AB-....json`.
4. No [painel oficial de Afiliados e Creadores](https://www.mercadolibre.com.ar/l/afiliados), abra **Generador de productos recomendados**. Cole o conteúdo de `urls-para-gerador.txt`. Não mude a ordem das linhas. Escolha a **mesma etiqueta** do lote.
5. Clique **Generar** > **Links cortos** > **Copiar todos**. Compare quantidade e ordem com `pendentes.csv`. Se o painel recusou, alterou a ordem ou omitiu produto, **não importe**; será necessário corrigir o lote.
6. Abra [Actions > Importar links oficiais de afiliados (lote)](https://github.com/Wenz-W/promoradar-argentina/actions/workflows/importar-lote-afiliados.yml). Informe o `batch_id`, cole um link por linha (ou se o formulário exigir uma linha, separe-os por ` | `) e marque `confirmed_mapping` **somente após revisar**.
7. A Action valida contagem, URL oficial e duplicações; preserva o texto do link sem inventar parâmetros `matt_tool`, `ref` ou `matt_word`, e persiste em `data/real/affiliate-links-AAAA-MM.jsonl`.
8. **Antes de publicar:** abra o produto correspondente, confirme preço, disponibilidade, condições de comissão e destino de cada link. O banco de links não substitui essa verificação. Para preparar e registrar envio use os workflows atuais `Preparar oferta afiliada para WhatsApp` e `Registrar publicação manual no WhatsApp`.

## Limites e segurança

- **Descoberta ainda não operacional em produção:** o conector Mercado Libre existente precisa de credenciais oficiais e permissão de busca; a fonte SEPA estava desatualizada na última execução. Portanto, a exportação pode retornar `0` produtos enquanto não houver coletas reais recentes. Não ocultamos esse resultado.
- A inscrição no programa de afiliados não concede automaticamente a API de produtos. A função de geração de URLs é operada **no painel do afiliado**, sem copiar APIs privadas ou automatizar cookies.
- `mercadolibre.com.ar/p/MLA...` é identificador de catálogo, **não necessariamente um anúncio específico**. A associação do link ao produto deve ser revisada pelo operador.
- A importação por posição é confirmada manualmente; o robô não consegue provar que o link `meli.la` leva ao produto correto nem que a venda gera comissão. O workflow recusa contagem divergente, URLs suspeitas e links repetidos no mesmo lote.
- Não misturar links fornecidos pelo operador com observações de preços: `affiliate-links-*` não cria linhas `observations-*` nem `offers-*`.
- Como o repositório é público, os links são informações públicas de afiliado. **Não** adicionar tokens, chaves, cookies, IDs privados de sessões ou planilhas de clientes.

## Próximo bloqueio de descoberta automática

A implementação de coleta já tem um conector API oficial do Mercado Libre (`promoradar/meli.py`) que pesquisa termos quando a aplicação **está autorizada e habilitada**. Sem autorização, nenhuma oferta pode ser coletada por essa fonte. Outras integrações futuras podem usar feeds de parceiros autorizados e adaptadores de lojas, com validação das respectivas condições de uso. Não é aceitável inventar um desconto usando apenas o preço riscado pelo vendedor.

Referências:
- [Programa de Afiliados Mercado Libre AR](https://www.mercadolibre.com.ar/l/afiliados)
- [Mercado Libre — Central de ajuda e gerador de recomendados](https://www.mercadolibre.com.ar/ayuda/v2/search?query=generador%20de%20productos%20recomendados)
- [Mercado Libre Developers — APIs](https://developers.mercadolibre.com.ar/)
- [GitHub Actions — Workflows](https://docs.github.com/en/actions)
