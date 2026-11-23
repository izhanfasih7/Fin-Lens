import unittest
from unittest.mock import patch
from backend.main import analyze
from backend.extraction import extract_pages, Page, PDFError


class FallbackTests(unittest.TestCase):
    def test_sample_ranges_and_accounting(self):
        from backend.demo import demo_analysis
        for _ in range(50):
            r=demo_analysis()
            self.assertTrue(80 < r['health']['score'] < 94)
            for slot in ('previous','current'):
                self.assertTrue(all(0 < pair[slot] < 10000 for pair in r['metrics'].values()))
                self.assertEqual(sum(p[slot] for p in r['segment_ebitda'].values()),r['metrics']['ebitda'][slot])
                self.assertEqual(r['metrics']['pbt'][slot]-r['metrics']['tax'][slot],r['metrics']['pat'][slot])
            self.assertLess(r['balance']['ltm_ebitda'],10000)
            self.assertLess(r['balance']['net_debt'],10000)

    @patch('backend.main.database.save')
    def test_empty_results_are_labelled_and_preserved(self, save):
        original=extract_pages([])
        with patch('backend.main.extract_pdf', return_value=original):
            result=analyze(b'', 'example.pdf')
        self.assertTrue(result['is_fallback'])
        self.assertIs(result['extracted_report'],original)
        self.assertEqual(result['sources'],{})
        self.assertIn('Illustrative',result['filename'])
        for slot in ('previous','current'):
            m=result['metrics']
            self.assertEqual(m['pbt'][slot]-m['tax'][slot],m['pat'][slot])
        save.assert_called_once()

    @patch('backend.main.database.save')
    def test_scanned_and_failed_extractor(self, save):
        for error in (PDFError('No selectable text found. OCR is required for scanned PDFs.'),RuntimeError('layout failed')):
            with patch('backend.main.extract_pdf', side_effect=error):
                self.assertTrue(analyze(b'', 'scan.pdf')['is_fallback'])

    @patch('backend.main.database.save')
    def test_real_values_survive_sentiment_failure(self, save):
        original=extract_pages([Page(1,'Consolidated Financial Results\nRs crore',[[['Metric','Q1 FY25','Q1 FY26'],['Revenue','100','120']]])])
        with patch('backend.main.extract_pdf',return_value=original),patch('backend.main.analyze_sentiment',side_effect=RuntimeError('offline')):
            result=analyze(b'', 'real.pdf')
        self.assertFalse(result.get('is_fallback',False))
        self.assertEqual(result['metrics']['revenue']['current'],120)
        self.assertIsNone(result['metrics']['pat']['current'])
        self.assertEqual(result['sentiment']['status'],'unavailable')
