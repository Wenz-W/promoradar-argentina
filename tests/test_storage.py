import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from promoradar.storage import append_jsonl, read_jsonl
from promoradar.meli import normalize_item

class TestStorage(unittest.TestCase):
    def test_jsonl_dedupe(self):
        with TemporaryDirectory() as d:
            path=Path(d)/'records.jsonl'
            self.assertEqual(2,append_jsonl(path,[{'id':'a'},{'id':'b'}],'id'))
            self.assertEqual(0,append_jsonl(path,[{'id':'a'}],'id'))
            self.assertEqual(2,len(read_jsonl(path)))
    def test_meli_normalization(self):
        item={'id':'MLA123','title':'Cafetera','permalink':'https://www.mercadolibre.com.ar/test',
              'currency_id':'ARS','price':100000,'status':'active','available_quantity':12}
        record=normalize_item(item,'2026-11-23T12:00:00+00:00','run')
        self.assertEqual('MLA123',record['listing_id'])
        self.assertEqual(100000.0,record['price_ars'])
        self.assertEqual('real',record['data_mode'])
    def test_other_currency_rejected(self):
        item={'id':'MLA123','permalink':'https://www.mercadolibre.com.ar/test','currency_id':'USD','price':40}
        self.assertIsNone(normalize_item(item,'2026-11-23T12:00:00+00:00','run'))

if __name__=='__main__': unittest.main()
