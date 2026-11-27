"""Exportação e importação de links oficiais sem fabricar parâmetros."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from promoradar.affiliate_batch import (
    AffiliateBatchError, normalize_product_url, validate_official_affiliate_link,
    collect_latest_products, export_batch, import_batch, read_link_bank,
    register_user_supplied_link,
)

NOW=datetime(2026,11,26,20,0,tzinfo=timezone.utc)
LABEL='liwe4706506'
GADNIC='https://www.mercadolibre.com.ar/p/MLA67162330'
MOCHILA='https://www.mercadolibre.com.ar/p/MLA65551248'
GADNIC_LINK='https://meli.la/1pRAHdr'
MOCHILA_LINK='https://meli.la/2BPrtmu'


def row(url, title='Bolsa Gadnic', price=15499, ts=NOW, **kw):
    data={'source':'mercadolibre','data_mode':'real','currency':'ARS','stock_status':'available',
          'price_ars':price,'captured_at':ts.isoformat(),'url':url,'title':title}
    data.update(kw)
    return data


class AffiliateBatchTests(unittest.TestCase):
    def test_product_urls_canonical_and_block_ssrf(self):
        self.assertEqual(('MLA67162330',GADNIC),normalize_product_url('https://www.mercadolibre.com.ar/bolsa/p/MLA67162330?tracking=123'))
        for value in ['http://www.mercadolibre.com.ar/p/MLA67162330',
                      'https://www.mercadolibre.com.ar.evil.tld/p/MLA67162330',
                      'https://www.mercadolibre.com.ar/social/liwe4706506?matt_word=xxx',
                      'https://www.mercadolibre.com.ar/p/foo',
                      'https://foo:bar@www.mercadolibre.com.ar/p/MLA67162330',
                      'https://meli.la/1pRAHdr',
                      'https://www.mercadolibre.com.ar/p/MLA67162330#abc']:
            with self.subTest(value=value),self.assertRaises(AffiliateBatchError):
                normalize_product_url(value)

    def test_accept_exact_meli_short_or_social_with_matching_label(self):
        self.assertEqual(GADNIC_LINK,validate_official_affiliate_link(GADNIC_LINK,LABEL))
        full='https://www.mercadolibre.com.ar/social/liwe4706506?matt_word=liwe4706506&matt_tool=29703292&ref='+'A'*64
        self.assertEqual(full,validate_official_affiliate_link(full,LABEL))
        for link in ['https://meli.la.evil.com/1pRAHdr',
                     'https://www.mercadolibre.com.ar/social/other?matt_word=other&matt_tool=123&ref='+'A'*64,
                     'https://www.mercadolibre.com.ar/social/liwe4706506?matt_word=other&matt_tool=123&ref='+'A'*64,
                     'https://www.mercadolibre.com.ar/social/liwe4706506?matt_word=liwe4706506&matt_tool=123',
                     'https://meli.la/abc?matt_tool=1']:
            with self.subTest(link=link),self.assertRaises(AffiliateBatchError):
                validate_official_affiliate_link(link,LABEL)

    def test_only_real_recent_available_products_exported(self):
        items=[row(GADNIC,price=15499),row(MOCHILA,title='Mochila',price=25000),
               row(GADNIC,price=999,ts=NOW-timedelta(days=2)),
               row('https://www.mercadolibre.com.ar/p/MLA77777777',data_mode='demo'),
               row('https://www.mercadolibre.com.ar/p/MLA77777777',stock_status='unavailable'),
               row('https://www.mercadolibre.com.ar/p/MLA77777777',currency='USD'),
               row('https://www.mercadolibre.com.ar/p/MLA77777777',source='sepa')]
        actual=collect_latest_products(items,at=NOW)
        self.assertEqual(2,len(actual))
        self.assertEqual({15499.0,25000.0},{x['price_ars'] for x in actual})
        self.assertTrue(all(x['price_evidence']=='observed_price_not_historical_discount' for x in actual))

    def test_export_import_preserves_order_and_urls(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'data';out=Path(td)/'outputs'
            rows=[row(GADNIC),row(MOCHILA,title='Mochila')]
            ex=export_batch(observations=rows,label=LABEL,data_dir=root,out_dir=out,at=NOW)
            self.assertEqual(2,ex['pending'])
            urls=(out/'urls-para-gerador.txt').read_text().splitlines()
            self.assertEqual(2,len(urls))
            order={GADNIC:GADNIC_LINK,MOCHILA:MOCHILA_LINK}
            imp=import_batch(batch_id=ex['batch_id'],links_text='\n'.join(order[url] for url in urls),data_dir=root,at=NOW)
            self.assertEqual(2,imp['imported'])
            bank=read_link_bank(data_dir=root)
            self.assertEqual(GADNIC_LINK,bank[(LABEL,'MLA67162330')]['affiliate_url'])
            self.assertEqual(MOCHILA_LINK,bank[(LABEL,'MLA65551248')]['affiliate_url'])
            self.assertFalse(any(root.glob('observations-*.jsonl')))
            again=export_batch(observations=rows,label=LABEL,data_dir=root,out_dir=out,at=NOW)
            self.assertEqual(0,again['pending'])
            self.assertEqual(2,again['already_linked'])
            self.assertEqual(2,import_batch(batch_id=ex['batch_id'],links_text='\n'.join(order[url] for url in urls),data_dir=root,at=NOW)['already_known'])

    def test_reject_wrong_count_no_partial_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'data';out=Path(td)/'out'
            ex=export_batch(observations=[row(GADNIC),row(MOCHILA)],label=LABEL,data_dir=root,out_dir=out,at=NOW)
            with self.assertRaises(AffiliateBatchError):
                import_batch(batch_id=ex['batch_id'],links_text=GADNIC_LINK,data_dir=root,at=NOW)
            self.assertFalse(list(root.glob('affiliate-links-*.jsonl')))
            with self.assertRaises(AffiliateBatchError):
                import_batch(batch_id=ex['batch_id'],links_text=GADNIC_LINK+'\n'+GADNIC_LINK,data_dir=root,at=NOW)
            self.assertFalse(list(root.glob('affiliate-links-*.jsonl')))

    def test_existing_link_remains_stable_and_no_cross_product_reuse(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            register_user_supplied_link(GADNIC,GADNIC_LINK,LABEL,at=NOW,data_dir=root)
            result=register_user_supplied_link(GADNIC,GADNIC_LINK,LABEL,at=NOW,data_dir=root)
            self.assertFalse(result['new'])
            with self.assertRaises(AffiliateBatchError):
                register_user_supplied_link(MOCHILA,GADNIC_LINK,LABEL,at=NOW,data_dir=root)
            with self.assertRaises(AffiliateBatchError):
                register_user_supplied_link(GADNIC,MOCHILA_LINK,LABEL,at=NOW,data_dir=root)

    def test_no_data_means_no_batch(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'data';out=Path(td)/'out'
            ex=export_batch(observations=[],label=LABEL,data_dir=root,out_dir=out,at=NOW)
            self.assertIsNone(ex['batch_id'])
            self.assertEqual('',(out/'urls-para-gerador.txt').read_text())
            self.assertFalse(list((root/'affiliate-batches').glob('*.json')))

    def test_different_labels_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            register_user_supplied_link(GADNIC,GADNIC_LINK,LABEL,at=NOW,data_dir=root)
            register_user_supplied_link(GADNIC,MOCHILA_LINK,'other_tag',at=NOW,data_dir=root)
            self.assertEqual(2,len(read_link_bank(data_dir=root)))


if __name__=='__main__':unittest.main()
