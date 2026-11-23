import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from backend.release_layout import recover_release
from backend.extraction import Page, extract_pages


class ReleaseTests(unittest.TestCase):
    def words(self, name):
        return json.loads((Path(__file__).parent/'fixtures'/f'release{name}_words.json').read_text())

    def test_both_real_layouts_and_comparison_basis(self):
        # Expected amounts transcribed from visual review of the first page.
        for name, expected, period, debt in [
            ('26', [340257,54067,8337,15100,30630,7629,23196], 'Q1 FY27',122914),
            ('28', [293829,50932,6613,14622,29697,7530,22290], 'Q3 FY26',117102)]:
            words = self.words(name)
            tables = recover_release(SimpleNamespace(extract_words=lambda:words))
            result = extract_pages([Page(1, 'Consolidated Financial Highlights\n* Annualised', layout_tables=tables)])
            self.assertEqual(result['periods']['current'], period)
            self.assertEqual([pair['current'] for pair in result['metrics'].values()],expected)
            self.assertEqual(result['balance']['net_debt'],debt)
            self.assertEqual(result['annualized_net_debt_to_ebitda'],.57)
            self.assertIsNone(result['balance']['net_debt_to_ebitda'])
            self.assertEqual(result['sources']['pat.current'][0]['page'],1)

    def test_missing_year_headers_rejected(self):
        words=[w for w in self.words('26') if not w['text'].startswith('FY')]
        self.assertEqual(recover_release(SimpleNamespace(extract_words=lambda:words)),[])

    def test_translation_does_not_change_columns(self):
        words=self.words('28')
        original=recover_release(SimpleNamespace(extract_words=lambda:words))
        shifted=[dict(w,x0=w['x0']+20,x1=w['x1']+20,top=w['top']+40,bottom=w['bottom']+40) for w in words]
        self.assertEqual(recover_release(SimpleNamespace(extract_words=lambda:shifted)),original)
