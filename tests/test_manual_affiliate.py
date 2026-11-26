import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from promoradar.affiliate_manual import (
    create_candidate, save_candidate, make_whatsapp_draft, normalize_price,
    validate_affiliate_url, get_candidate, mark_published, ManualAffiliateError
)
from promoradar.storage import read_jsonl


NOW = datetime(2026, 11, 26, 19, 0, tzinfo=timezone.utc)
LINK = 'https://meli.la/1pRAHdr'


class AffiliateManualTests(unittest.TestCase):
    def make(self, **kwargs):
        args = {'title':'Cafetera de prueba', 'price_ars':'89900', 'affiliate_url': LINK, 'when':NOW}
        args.update(kwargs)
        return create_candidate(**args)

    def test_preserves_exact_user_link(self):
        row=self.make()
        self.assertEqual(LINK, row['affiliate_url'])
        self.assertEqual('mercadolibre', row['source'])
        self.assertFalse(row['historical_discount_verified'])
        self.assertEqual('real_manual_candidate', row['data_mode'])

    def test_does_not_invent_discount(self):
        draft=make_whatsapp_draft(self.make())
        self.assertIn('https://meli.la/1pRAHdr', draft)
        self.assertIn('89.900,00', draft)
        self.assertNotIn('−15%', draft)
        self.assertNotIn('descuento', draft.lower())
        self.assertIn('Enlace de afiliado', draft)

    def test_rejects_lookalike_and_credentials(self):
        for link in ['https://meli.la.evil.com/1pRAHdr',
                     'http://meli.la/1pRAHdr',
                     'https://meli.la@evil.com/x',
                     'https://meli.la:443/1pRAHdr',
                     'https://meli.la/1pRAHdr?secret=x',
                     'https://meli.la/1pRAHdr\n',
                     'https://example.com/abc',
                     'https://meli.la/a']:
            with self.subTest(link=link):
                with self.assertRaises(ManualAffiliateError):
                    validate_affiliate_url(link)

    def test_price_format_validated(self):
        self.assertEqual('24999.90',str(normalize_price('24999.90')))
        for value in ['12.345,67', '29,90', '-3', '0', 'NaN', 'Infinity', '120.999', '1e8']:
            with self.subTest(value=value):
                with self.assertRaises(ManualAffiliateError):
                    normalize_price(value)

    def test_record_is_separate_and_deduplicated(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            row=self.make()
            self.assertTrue(save_candidate(row,data_dir=root))
            self.assertFalse(save_candidate(row,data_dir=root))
            self.assertEqual(1,len(read_jsonl(root/'affiliate-candidates-2026-11.jsonl')))
            self.assertFalse(list(root.glob('observations-*.jsonl')))
            self.assertFalse(list(root.glob('offers-*.jsonl')))

    def test_publish_requires_human_confirmation(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            row=self.make()
            save_candidate(row,data_dir=root)
            with self.assertRaises(ManualAffiliateError):
                mark_published(row['candidate_id'], '89900','PromoRadar AR',confirmed=False,data_dir=root)
            self.assertFalse(list(root.glob('affiliate-publications-*.jsonl')))

    def test_publish_rejects_changed_price(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            row=self.make()
            save_candidate(row,data_dir=root)
            with self.assertRaises(ManualAffiliateError):
                mark_published(row['candidate_id'], '99900','PromoRadar AR',confirmed=True,data_dir=root)

    def test_publish_records_attestation_not_independent_proof(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            row=self.make()
            save_candidate(row,data_dir=root)
            record=mark_published(row['candidate_id'], '89900','PromoRadar AR',confirmed=True,when=NOW,data_dir=root)
            self.assertEqual('operator_attested_sent_and_checked',record['confirmation_type'])
            self.assertEqual(LINK, record['affiliate_url'])
            with self.assertRaises(ManualAffiliateError):
                mark_published(row['candidate_id'], '89900','PromoRadar AR',confirmed=True,when=NOW,data_dir=root)

    def test_missing_candidate(self):
        with self.assertRaises(ManualAffiliateError):
            get_candidate('AF-MISSING',records=[])

    def test_day_changes_id_for_new_verification(self):
        row=self.make()
        other=self.make(when=datetime(2026,11,27,19,0,tzinfo=timezone.utc))
        self.assertNotEqual(row['candidate_id'],other['candidate_id'])


if __name__=='__main__':unittest.main()
