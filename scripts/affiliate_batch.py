"""Interface CLI do gerador de lotes afiliados Mercado Libre (GitHub Actions)."""
from __future__ import annotations
import argparse
import json
import os
from promoradar.affiliate_batch import export_batch, import_batch, AffiliateBatchError


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('action', choices=['export','import'])
    args=parser.parse_args()
    try:
        if args.action=='export':
            result=export_batch(label=os.getenv('AFFILIATE_LABEL','liwe4706506'),
                                max_items=int(os.getenv('MAX_ITEMS','20')),
                                max_age_hours=int(os.getenv('MAX_AGE_HOURS','30')))
            extra='Copie o arquivo urls-para-gerador.txt para o gerador oficial, mantendo a ordem. '
        else:
            if os.getenv('CONFIRMED_MAPPING','').lower() != 'true':
                raise AffiliateBatchError('Confirme a correspondência entre produtos e links antes de importar.')
            result=import_batch(batch_id=os.getenv('BATCH_ID',''),links_text=os.getenv('OFFICIAL_LINKS',''))
            extra='Links armazenados sem modificar seus parâmetros. Reconfirme destino, preço e condições antes de publicar. '
    except (AffiliateBatchError, ValueError) as exc:
        print('ERROR:',str(exc))
        return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    summary=os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf-8') as f:
            f.write('## PromoRadar — Lote de afiliados\n\n')
            for key,val in result.items():
                f.write(f'- **{key}**: `{val}`\n')
            f.write('\n'+extra+'\n')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
