"""GitHub Actions: preparação de mensagens e registro manual de publicações."""
from __future__ import annotations
import json
import os
from pathlib import Path
from promoradar.affiliate_manual import (
    create_candidate, save_candidate, make_whatsapp_draft, mark_published,
    ManualAffiliateError,
)


def _summary(text: str):
    path = os.getenv('GITHUB_STEP_SUMMARY')
    if path:
        with open(path,'a',encoding='utf-8') as f:
            f.write(text + '\n')


def main() -> int:
    import sys
    if len(sys.argv) != 2 or sys.argv[1] not in ('prepare', 'published'):
        print('Uso: python -m scripts.affiliate_manual prepare|published', file=sys.stderr)
        return 2
    try:
        action = sys.argv[1]
        if action == 'prepare':
            row = create_candidate(os.environ.get('PRODUCT_TITLE',''),
                                   os.environ.get('PRICE_ARS',''),
                                   os.environ.get('AFFILIATE_URL',''))
            fresh = save_candidate(row)
            message = make_whatsapp_draft(row)
            out = Path('outputs/affiliate')
            out.mkdir(parents=True, exist_ok=True)
            (out/'mensagem-whatsapp.txt').write_text(message + '\n',encoding='utf-8')
            (out/'candidato.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'candidate_id':row['candidate_id'],'created':fresh,
                              'status':row['status']},ensure_ascii=False))
            _summary(f"## Oferta para revisão — {row['candidate_id']}\n\n"
                     f"**Registro:** {'novo' if fresh else 'já existente'}; o preço foi informado manualmente, não medido por API.\n\n"
                     f"**Antes de enviar:** abra o link, confira produto, preço e estoque e então copie a mensagem do artefato `mensagem-whatsapp`.\n\n"
                     f"```text\n{message}\n```\n\n**Candidate ID:** `{row['candidate_id']}`")
        else:
            row = mark_published(os.environ.get('CANDIDATE_ID',''),
                                 os.environ.get('CONFIRMED_PRICE_ARS',''),
                                 os.environ.get('CHANNEL',''),
                                 confirmed=os.environ.get('CONFIRMED_SENT','').lower()=='true')
            print(json.dumps(row,ensure_ascii=False,indent=2))
            _summary(f"## Publicação registrada\n\nCandidato `{row['candidate_id']}` declarado enviado a **{row['channel']}**. Registro é confirmação manual, não prova independente de envio.")
    except (ManualAffiliateError, KeyError) as exc:
        print('ERRO: '+str(exc),file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
