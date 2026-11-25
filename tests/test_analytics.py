import unittest
from datetime import datetime, timedelta, timezone
from promoradar.analytics import detect_offers

CFG={'drop_threshold_pct':15,'min_historical_days':7,'min_historical_samples':7,
     'historical_window_days':30,'repost_cooldown_hours':48,'extra_drop_for_repost_pct':5}

def sample(day, price, lid='MLA1', demo=False):
    stamp = (datetime(2026,11,1,tzinfo=timezone.utc) + timedelta(days=day)).isoformat()
    return {'observation_id':f'{lid}-{day}', 'captured_at':stamp, 'source':'mercadolibre',
            'listing_id':lid,'title':'Producto','price_ars':price,'stock_status':'available',
            'data_mode':'demo' if demo else 'real','url':'https://example.org/product'}

class TestScoring(unittest.TestCase):
    def test_no_baseline_is_not_an_offer(self):
        self.assertEqual([],detect_offers([sample(0,80)],[sample(0,100)],[],CFG))
    def test_drop_from_seven_distinct_days(self):
        historical=[sample(i,100) for i in range(7)]
        offers=detect_offers([sample(7,80)], historical, [], CFG)
        self.assertEqual(1,len(offers))
        self.assertEqual(20.0,offers[0]['drop_pct'])
        self.assertEqual(7,offers[0]['evidence_distinct_days'])
    def test_spike_is_not_an_offer(self):
        self.assertEqual([],detect_offers([sample(7,120)],[sample(i,100) for i in range(7)],[],CFG))
    def test_repost_cooldown(self):
        old=detect_offers([sample(7,80)],[sample(i,100) for i in range(7)],[],CFG)
        fake=sample(8,79)
        self.assertEqual([],detect_offers([fake],[sample(i,100) for i in range(7)],old,CFG))
    def test_avoid_mixing_real_demo_data(self):
        history=[sample(i,100,demo=True) for i in range(7)]
        self.assertEqual([],detect_offers([sample(7,80)],history,[],CFG))

if __name__=='__main__': unittest.main()
