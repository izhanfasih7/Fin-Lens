import unittest
from backend.extraction import Page
from backend.report_context import describe_report


class ReportContextTests(unittest.TestCase):
    def test_cross_page_overview_keeps_qualifications(self):
        pages = [Page(1, 'RESULTS UPDATE & FAQ'),
                 Page(4, 'Q5. Please provide a brief overview of Q1 FY27 results.\nOverall, Gross Revenue grew 28%\n4'),
                 Page(5, 'YoY, while Net Revenue declined 14% YoY (6% lower YoY excluding Agri); EBITDA and PAT\nwere lower by 28% and 27% YoY, respectively.\nQ6. Other question\nRevenue grew 99%.')]
        result = describe_report(pages, {'revenue': {'current': None}})
        self.assertEqual(result['status'], 'narrative_only')
        self.assertEqual(len(result['reported_highlights']), 1)
        self.assertEqual(result['reported_highlights'][0]['pages'], [4, 5])
        self.assertIn('excluding Agri', result['reported_highlights'][0]['text'])
        self.assertNotIn('99%', result['reported_highlights'][0]['text'])

    def test_unknown_layout_not_called_missing_source_data(self):
        result = describe_report([Page(1, 'Annual financial results')], {'revenue': {'current': None}})
        self.assertEqual(result['status'], 'no_supported_figures')
        self.assertIn('unsupported layout', result['reason'])

    def test_faq_with_actual_figures_retains_dashboard(self):
        self.assertEqual(describe_report([Page(1, 'FAQ')], {'pat': {'current': 0}})['status'], 'figures_available')
