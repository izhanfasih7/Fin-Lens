"""Regression for the user's FY27 report, visually checked on pages 9, 10 and 11."""
import copy
import json
import os
from pathlib import Path
import unittest

from backend.extraction import Page, extract_pages, extract_pdf
from backend.layout import recover_table
from backend.ratios import calculate_ratios

SNAPSHOT = json.loads((Path(__file__).parent / 'fixtures/ril_fy27_layout.json').read_text(encoding='utf-8'))
METRICS = {'revenue': (273252, 340257), 'ebitda': (49100, 54067),
           'finance_cost': (7036, 8337), 'depreciation': (13842, 15100),
           'pbt': (28222, 30630), 'tax': (6465, 7629), 'pat': (21859, 23196)}
SEGMENTS = {'O2C': (14511, 17010), 'E&P': (4996, 4973),
            'Digital Services': (18312, 21255), 'Retail': (6381, 6309), 'Others': (4900, 4520)}


class WordPage:
    def __init__(self, words):
        self.words = words

    def extract_words(self):
        return self.words


def recovered_result():
    pages = []
    for entry in SNAPSHOT['pages']:
        words = entry['words']
        tables, as_of, commentary = recover_table(WordPage(words))
        text = ' '.join(w['text'] for w in words)
        pages.append(Page(entry['page'], text, [], tables, as_of, commentary))
    return extract_pages(pages)


def assert_figures(case, result):
    case.assertEqual(result['periods'], {'previous': 'Q1 FY26', 'current': 'Q1 FY27'})
    for key, pair in METRICS.items():
        case.assertEqual(result['metrics'][key], dict(zip(('previous', 'current'), pair)), key)
        for period in ('previous', 'current'):
            case.assertEqual(result['sources'][f'{key}.{period}'][0]['page'], 9)
    for key, pair in SEGMENTS.items():
        case.assertEqual(result['segment_ebitda'][key], dict(zip(('previous', 'current'), pair)), key)
        for period in ('previous', 'current'):
            case.assertEqual(result['sources'][f'segments.{key}.{period}'][0]['page'], 10)
    case.assertEqual(result['balance'], {'net_debt': 122914, 'ltm_ebitda': 203954, 'net_debt_to_ebitda': .6})
    case.assertEqual(result['balance_as_of'], 'Jun-26')
    case.assertEqual(result['missing'], [])


class FY27LayoutTests(unittest.TestCase):
    def test_all_27_amounts_and_sources(self):
        assert_figures(self, recovered_result())

    def test_ratios_match_new_report_not_old_fy26_expectations(self):
        result = recovered_result()
        ratios = calculate_ratios(result['metrics'], result['balance'])
        self.assertEqual(ratios['current']['pat_margin_pct'], 6.82)
        self.assertEqual(ratios['current']['interest_coverage_x'], 6.49)
        self.assertEqual(ratios['yoy_growth_pct'], {'revenue': 24.52, 'ebitda': 10.12, 'pat': 6.12})

    def test_moving_table_on_page_does_not_change_extraction(self):
        for entry in SNAPSHOT['pages']:
            moved = copy.deepcopy(entry['words'])
            for word in moved:
                for axis in ('x0','x1'):
                    word[axis] += 35
                for axis in ('top','bottom'):
                    word[axis] += 20
            self.assertEqual(recover_table(WordPage(moved))[:2], recover_table(WordPage(entry['words']))[:2])

    def test_missing_rupee_units_cannot_be_assumed(self):
        words = [w for w in SNAPSHOT['pages'][0]['words'] if w['text'] not in ('₹','crore')]
        self.assertEqual(recover_table(WordPage(words))[0], [])

    def test_latest_balance_date_is_selected_not_last_column(self):
        words = copy.deepcopy(SNAPSHOT['pages'][2]['words'])
        for w in words:
            if w['text'] == 'Mar-26':
                w['text'] = 'Sep-26'
        table, as_of, _ = recover_table(WordPage(words))
        self.assertEqual(as_of, 'Sep-26')
        self.assertEqual(table[0][0][0], 'Net Debt')
        self.assertEqual(table[0][0][1], '1,24,717')


@unittest.skipUnless(os.environ.get('FINLENS_FY27_PDF'), 'Set FINLENS_FY27_PDF to run the full FY27 PDF regression.')
class FY27RealPDFTests(unittest.TestCase):
    def test_full_pdf_matches_visually_reviewed_figures(self):
        result = extract_pdf(Path(os.environ['FINLENS_FY27_PDF']).read_bytes())
        self.assertEqual(result['page_count'], 76)
        assert_figures(self, result)
        self.assertTrue(any('exclude profit' in w for w in result['warnings']))
        self.assertFalse(any('formats offset' in w for w in result['warnings']))
