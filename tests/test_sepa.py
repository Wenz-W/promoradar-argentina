import unittest
from promoradar.sepa import parse_shard, SepaError

class SepaTests(unittest.TestCase):
    def test_parse_documented_shard(self):
        data={'region':'CENTRO','fecha':'2026-11-23','items':{
            '7790139101169':{'producto':{'nombre':'VINAGRE 500 ML'},'por_cadena':{
                '1':{'precio_efectivo':2000,'tiene_promo':True},
                '3':{'precio_efectivo':2150,'tiene_promo':False}}}}}
        items=parse_shard(data,'CENTRO','2026-11-23T12:00:00+00:00',10)
        self.assertEqual(2,len(items))
        self.assertEqual('sepa',items[0]['source'])
        self.assertEqual('2026-11-23',items[0]['source_date'])
        self.assertEqual('listed',items[0]['stock_status'])
        self.assertEqual(items[0]['observation_id'],parse_shard(data,'CENTRO','2026-11-24T12:00:00+00:00',10)[0]['observation_id'])
    def test_bad_format(self):
        with self.assertRaises(SepaError):parse_shard({'region':'NACIONAL','fecha':'x','items':{}},'CENTRO','2026-11-23T12:00:00+00:00',10)

if __name__=='__main__':unittest.main()
