# Roadmap futuro — Catálogo público de promoções vigentes

**Projeto:** PromoRadar Argentina  
**Status:** Requisito registrado; **não implementado** no MVP atual  
**Prioridade:** Próxima etapa após estabilizar a coleta de ofertas reais e a aprovação para WhatsApp  
**Origem:** Requisito do responsável pelo projeto (23/11/2026)

## Visão do produto

Criar uma **página web pública e independente** onde qualquer pessoa possa consultar, pesquisar e comparar todas as **promoções ainda vigentes** que tenham sido preparadas/aprovadas para publicação nos grupos de ofertas do WhatsApp.

A experiência deve ter identidade própria, sem depender do WhatsApp para funcionar e **sem necessidade de mencionar os grupos no site**. O mesmo catálogo de ofertas alimenta ambos os canais: publicações preparadas para WhatsApp e vitrine web pesquisável.

O objetivo não é duplicar a coleta nem criar uma segunda base de produtos, e sim oferecer uma **segunda interface de consulta** ao mesmo conjunto de ofertas verificadas.

## Funcionalidades desejadas

1. **Página inicial de ofertas vigentes**, mostrando produto, imagem quando autorizada, loja, preço atual em ARS, desconto verificado (quando houver referência confiável), data/hora da última checagem e link para a loja de origem.
2. **Pesquisa por palavras-chave** (produto, marca, modelo) e filtros por categoria, marketplace/loja, preço e percentual de desconto.
3. **Ordenação** por melhores descontos, mais recentes, preço crescente e loja.
4. **Página de detalhe** do produto com histórico de preços, data da última observação, regras/condições relevantes e identificação clara da origem da oferta.
5. **Sincronização com o pipeline atual**: quando uma oferta for aprovada e estiver válida, entra no catálogo; quando for expirada, esgotada, desatualizada ou rejeitada, deixa de aparecer como promoção vigente.
6. **Acesso público e responsivo**, pensado para uso em celular; sem login obrigatório.
7. **Links diretos** para as páginas de produto no vendedor; eventuais parâmetros de afiliado são uma capacidade futura opcional, e não exigência do MVP acadêmico.

## Regras de negócio e confiança

- **Promoção vigente** deve ter preço observado recente e comprovação da origem. Guardar `last_verified_at` e `source_observed_at` de forma separada; preço de fonte desatualizada não pode ser apresentado como preço atual.
- Se não houver histórico suficiente para confirmar uma economia, mostrar o preço encontrado **sem** afirmar um desconto histórico.
- Não inserir dados sintéticos no catálogo público como se fossem ofertas reais.
- Se houver alterações de preço, falta de estoque ou falha prolongada na verificação, marcar como indisponível/expirada ou remover da lista de vigentes.
- Evitar duplicações do mesmo anúncio; quando possível, consolidar produto equivalente de lojas diferentes.
- Respeitar permissões de uso de imagens, links e dados de cada fonte.

## Reaproveitamento técnico sem custo fixo inicial

- **Fonte de dados:** o armazenamento `data/real/` e as ofertas geradas pelo motor de detecção; evoluir os registros para incluir status de aprovação e validade.
- **Gerador:** script Python acionado no mesmo GitHub Actions da coleta, produzindo `docs/ofertas.json` e páginas HTML estáticas.
- **Hospedagem:** GitHub Pages, dentro das regras e cotas do serviço; não requer VPS ou execução 24/7 de aplicação dinâmica.
- **Frontend:** JavaScript simples com busca/filtros client-side enquanto o catálogo for pequeno; evoluir para índice de pesquisa dedicado somente se necessário.
- **Segurança:** publicar no Pages somente os campos públicos necessários; nunca publicar tokens, identificadores privados de membros do grupo ou logs internos.

## Campos adicionais sugeridos (a projetar)

`offer_id`, `product_id`, `listing_id`, `title`, `brand`, `category`, `store`, `current_price_ars`, `historical_reference_ars`, `discount_percent`, `product_url`, `image_url`, `source_observed_at`, `last_verified_at`, `published_at`, `expires_at`, `approval_status`, `offer_status`, `is_demo`.

A exibição pública exige `approval_status=approved`, `offer_status=active`, `is_demo=false` e verificação recente segundo regra configurável. Uma oferta preparada para o grupo mas ainda não aprovada não deverá aparecer publicamente por padrão.

## Critérios de aceite para a futura implementação

- Busca retorna as ofertas vigentes pelo título/marca e permite filtrar por loja e categoria.
- Todas as ofertas exibidas são reais, aprovadas e estão dentro do prazo de atualização definido.
- Uma oferta expirada deixa de aparecer na lista principal após a próxima atualização do site.
- Preço, desconto, data de verificação e origem são exibidos de forma compreensível.
- A página funciona no celular e pode ser aberta por qualquer pessoa, mesmo sem WhatsApp.
- O catálogo é gerado a partir **dos mesmos dados das ofertas**; não há segunda rotina de scraping exclusiva para o site.
- O site não exige nem promove a participação nos grupos; funciona como vitrine pública independente.

## Dependências e ordem sugerida

1. Estabilizar coleta real com histórico auditável por seis meses.
2. Implementar aprovação/status das ofertas e verificação de validade.
3. Exportar um arquivo público sanitizado com apenas ofertas ativas.
4. Publicar a vitrine estática com busca, filtros e links de origem.
5. Incorporar gráfico de histórico e comparações entre marketplaces, quando os dados forem confiáveis.

**Nota:** este arquivo registra o requisito de produto. Não significa que a funcionalidade tenha sido construída ou publicada.

## Documentação de referência

- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- GitHub Actions (agendamentos): https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
