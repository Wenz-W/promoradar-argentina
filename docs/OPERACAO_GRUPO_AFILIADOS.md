# PromoRadar AR — operação manual de ofertas afiliadas para WhatsApp

Esta fase **não requer aplicação no Mercado Libre Developers, API OAuth, GitHub Pages nem um servidor ligado**. Exige apenas sua conta aprovada no programa de afiliados, o link de afiliado gerado nela e uma verificação humana do produto.

## 1. Preparar a primeira oferta

1. Abra o anúncio no Mercado Libre com sua conta de afiliado. Gere **seu próprio** link `https://meli.la/...`. Não utilize o link de outra pessoa.
2. Confira título do produto, preço em ARS, estoque, vendedor e possíveis restrições de frete no anúncio. O sistema **não consegue verificar automaticamente** o destino do link curto nem se a comissão foi atribuída à sua conta.
3. Abra **GitHub > Actions > Preparar oferta afiliada para WhatsApp > Run workflow**, na branch `main`.
4. Informe `product_title`, `price_ars` (exemplo: `24999.90`, sem milhar), e `affiliate_url`. Cole o link **exatamente como fornecido pelo Mercado Libre**.
5. Depois de executar, abra a aba *Summary* e copie a mensagem pronta. Se preferir, baixe o artefato `mensagem-whatsapp` (arquivo `mensagem-whatsapp.txt`). **Reconfirme preço e estoque antes de publicar.**
6. Envie a mensagem manualmente no grupo de WhatsApp. Mantenha a indicação de que é um link de afiliado.

A mensagem não inventa percentual de desconto. Candidatos ficam em `data/real/affiliate-candidates-AAAA-MM.jsonl`, **separados** do histórico de preços coletados (`observations-*`) e de ofertas detectadas estatisticamente (`offers-*`). A indicação `precio informado` se refere à digitação pelo operador e **não** a uma verificação independente.

## 2. Registrar que o administrador publicou

1. Copie o `Candidate ID` (formato `AF-...`) mostrado no *Summary* do workflow anterior.
2. **Somente depois de realmente enviar ao grupo**, abra **Actions > Registrar publicação manual no WhatsApp > Run workflow**.
3. Informe ID, preço confirmado no anúncio, nome do grupo e marque a confirmação de que revisou **preço, estoque, destino do link e enviou a mensagem**.
4. O sistema salva a declaração em `data/real/affiliate-publications-AAAA-MM.jsonl`. Isso registra uma confirmação do operador; não é uma comprovação automática do envio no WhatsApp nem da comissão.

Se o preço tiver mudado, **não** confirme a postagem com o preço antigo. Prepare outro candidato com o valor novo.

## 3. Limites e boas práticas

- O link `meli.la` é tratado como **opaco**. O PromoRadar não troca, extrai ou inventa parâmetros de afiliado. O sistema valida o formato e o domínio, mas **não consegue confirmar o destino ou a atribuição de comissão** a partir do link curto.
- Não cadastre títulos nem preços inventados como se fossem reais. O processo registra dados fornecidos manualmente e precisa da sua revisão.
- Você pode começar a operar o grupo **sem esperar sete dias de histórico**. O período mínimo de sete dias é necessário apenas para anunciar descontos **detectados automaticamente pelo nosso algoritmo**.
- Para manter a elegibilidade das comissões, confira se seu grupo/canal e o modo de compartilhamento atendem às **condições vigentes do programa argentino**. Canais válidos e condições podem variar por país. O Brasil tem regras diferentes: não devemos copiar automaticamente suas regras para a Argentina.
- Não cole senhas, cookies, tokens de autenticação nem dados pessoais nos inputs dos workflows. O formulário solicita apenas nome público de produto, preço público e link de afiliado público.
- O catálogo público e o coletor automático permanecem independentes. Esta fase não corrige a origem SEPA desatualizada e não coleta preços do Mercado Libre automaticamente.

Fonte oficial do programa na Argentina: https://www.mercadolibre.com.ar/l/afiliados

## 4. Próxima automação

Quando o fluxo manual estiver validado, podemos aprimorar o monitoramento de preços por feeds ou APIs autorizadas e construir uma fila de ofertas detectadas que apenas solicita um link de afiliado do operador antes de compartilhar. **Uma inscrição no programa de afiliados não concede, por si só, acesso à API de busca.**
