import json
from pathlib import Path
import unittest
from unittest.mock import patch
from backend.extraction import Page, extract_pages
from backend.main import analyze
from backend.report_context import describe_report


class SegmentReleaseTests(unittest.TestCase):
    def fixtures(self):
        return json.loads((Path(__file__).parent/'fixtures'/'release_segments.json').read_text())

    def test_real_segment_sections(self):
        for fixture,period,expected in zip(self.fixtures(),['Q1 FY27','Q3 FY26'],
                [[17010,4973,21255,6309,1856],[16507,4857,19325,6915,2751]]):
            prev='Q1 FY26' if period=='Q1 FY27' else 'Q3 FY25'
            financial=Page(1,'Consolidated Financial Results\nRs crore',[[['Metric',prev,period],['Revenue','1','2']]])
            result=extract_pages([financial,Page(fixture['page'],fixture['text'],fixture['tables'])])
            self.assertEqual([v['current'] for v in result['segment_ebitda'].values()],expected)
            self.assertEqual(result['sources']['segments.Others.current'][0]['page'],fixture['page'])

    def test_standalone_is_not_consolidated(self):
        f=self.fixtures()[0]
        result=extract_pages([Page(1,f['text'].replace('CONSOLIDATED','STANDALONE'),f['tables'])])
        self.assertTrue(all(v['current'] is None for v in result['segment_ebitda'].values()))

    @patch('backend.main.database.save')
    @patch('backend.main.analyze_sentiment',return_value={'status':'unavailable'})
    def test_sourced_faq_does_not_become_sample(self, sentiment, save):
        pages=[Page(1,'FAQ'),Page(4,'Q5. Please provide a brief overview of Q1 FY27 results.\nGross Revenue grew 28% YoY.\nQ6. Next question')]
        result=extract_pages(pages)
        result['coverage']=describe_report(pages,result['metrics'])
        with patch('backend.main.extract_pdf',return_value=result):
            actual=analyze(b'', 'faq.pdf')
        self.assertFalse(actual.get('is_demo',False))
        self.assertIsNone(actual['metrics']['revenue']['current'])
        self.assertEqual(actual['coverage']['reported_highlights'][0]['text'],'Gross Revenue grew 28% YoY.')
