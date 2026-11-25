import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from promoradar.catalog import build_catalog, is_buy_link, record_review

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)

def row(price=800.0, at=None, stock='available', source='mercadolibre', mode='real'):
    at = at or NOW - timedelta(hours=2)
    return {
        'data_mode': mode, 'observation_id': 'OBS-001', 'listing_id': 'MLA-001',
        'title': 'Auriculares de prueba', 'source': source, 'price_ars': price,
        'currency': 'ARS', 'stock_status': stock, 'captured_at': at.isoformat(),
        'url': 'https://www.mercadolibre.com.ar/p/MLA-001', 'category_id': 'audio',
    }

def offer(at=None, mode='real', source='mercadolibre'):
    return {'offer_id':'O-001','listing_id':'MLA-001','data_mode':mode,'source':source,
            'detected_at': (at or NOW-timedelta(hours=3)).isoformat(),
            'price_ars':800,'baseline_median_ars':1000,'url':'https://www.mercadolibre.com.ar/p/MLA-001'}

def review(status='approved', at=None, mode='real'):
    return {'offer_id':'O-001','decision':status,'decided_at':(at or NOW-timedelta(hours=1)).isoformat(),'data_mode':mode}

class TestCatalog(unittest.TestCase):
    def build(self, obs=None, offers=None, reviews=None, **kw):
        return build_catalog([row()] if obs is None else obs,
                             [offer()] if offers is None else offers,
                             [review()] if reviews is None else reviews,
                             now=NOW, **kw)

    def test_approved_recent_real_offer_is_visible(self):
        feed=self.build()
        self.assertEqual(1,feed['count'])
        self.assertFalse(feed['offers'][0]['is_demo'])
        self.assertEqual(20.0, feed['offers'][0]['drop_pct'])

    def test_review_is_required(self):
        self.assertEqual(0,self.build(reviews=[])['count'])
        self.assertEqual(0,self.build(reviews=[review('rejected')])['count'])

    def test_later_rejection_revokes_approval(self):
        events=[review('approved',NOW-timedelta(hours=2)),review('rejected',NOW-timedelta(minutes=30))]
        self.assertEqual(0,self.build(reviews=events)['count'])

    def test_stale_and_out_of_stock_not_public(self):
        self.assertEqual(0,self.build(obs=[row(at=NOW-timedelta(hours=32))])['count'])
        self.assertEqual(0,self.build(obs=[row(stock='unavailable')])['count'])

    def test_price_increase_revokes_visibility(self):
        self.assertEqual(0,self.build(obs=[row(price=850)])['count'])
        self.assertEqual(1,self.build(obs=[row(price=750)])['count'])

    def test_offer_lifetime_is_bounded(self):
        self.assertEqual(0,self.build(offers=[offer(NOW-timedelta(days=8))])['count'])

    def test_sepa_not_buyable(self):
        self.assertEqual(0,self.build(obs=[row(source='sepa')],offers=[offer(source='sepa')])['count'])

    def test_demo_is_never_in_real_feed(self):
        self.assertEqual(0,self.build(obs=[row(mode='demo')],offers=[offer(mode='demo')],reviews=[review(mode='demo')])['count'])
        feed=self.build(obs=[row(mode='demo')],offers=[offer(mode='demo')],reviews=[review(mode='demo')],mode='demo')
        self.assertEqual(1,feed['count'])
        self.assertIsNone(feed['offers'][0]['url'])

    def test_url_allowlist(self):
        self.assertTrue(is_buy_link('https://www.mercadolibre.com.ar/p/MLA1','mercadolibre','real'))
        self.assertFalse(is_buy_link('https://www.mercadolibre.com.ar.bad.example/p','mercadolibre','real'))
        self.assertFalse(is_buy_link('http://www.mercadolibre.com.ar/p','mercadolibre','real'))
        self.assertFalse(is_buy_link('https://example.com/','sepa','real'))

    def test_manual_review_persists_in_separate_events_log(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            with patch('promoradar.catalog.read_series', return_value=[offer()]), \
                 patch('promoradar.catalog.DATA', d):
                event=record_review('O-001','approved',when=NOW)
                self.assertEqual('approved',event['decision'])
                self.assertTrue((d/'real'/'reviews-2026-11.jsonl').is_file())

    def test_manual_review_rejects_missing_or_unbuyable_offers(self):
        with patch('promoradar.catalog.read_series',return_value=[]):
            with self.assertRaises(ValueError):
                record_review('missing','approved')
        with patch('promoradar.catalog.read_series',return_value=[offer(source='sepa')]):
            with self.assertRaises(ValueError):
                record_review('O-001','approved')

if __name__=='__main__': unittest.main()
