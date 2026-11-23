"""Table-layout and context fixtures intentionally independent of slide numbers."""
import unittest

from backend.extraction import Page, extract_pages, normalize, number


def consolidated(rows=None, number_=19, previous="Q1 FY25", current="Q1 FY26"):
    return Page(number_, "Consolidated Financial Results\nRs crore", [
        [["Metric", previous, current], *(rows or [["Revenue", "1,00,000", "1,20,000"]])]])


class ExtractionEdgeTests(unittest.TestCase):
    def test_number_formats_and_footnotes(self):
        for raw, expected in [("3,30,870", 330870), ("(1,23,456.50)", -123456.5),
                              ("1,234†", 1234), ("41,000²↑", 41000), ("0", 0), (0, 0)]:
            with self.subTest(raw=raw):
                self.assertEqual(number(raw), expected)
        self.assertEqual(normalize(" Rs\u00a0 crore "), "Rs crore")

    def test_percentages_and_malformed_values_stay_missing(self):
        for raw in ("(4%)", "4%↑", "N/A", "—", "12,3", "12,3456", "USD 12", "1.2.3"):
            with self.subTest(raw=raw):
                self.assertIsNone(number(raw))

    def test_page_keyword_discovery_with_unrelated_pages(self):
        pages = [Page(1, "Revenue 999 888"), consolidated(number_=62), Page(80, "Thank you")]
        result = extract_pages(pages)
        self.assertEqual(result["metrics"]["revenue"]["current"], 120000)
        self.assertEqual(result["sources"]["revenue.current"], [{"page": 62, "label": "Revenue"}])

    def test_explicit_rupee_columns_in_mixed_currency_table(self):
        page = Page(21, "Consolidated Financial Results\nRs crore / $ Bn", [[
            ["Metric", "Q1 FY25 Rs crore", "Q1 FY25 $ Bn", "Q1 FY26 Rs crore", "Q1 FY26 $ Bn"],
            ["Revenue", "100000", "12", "120000", "14"]]])
        result = extract_pages([page])
        self.assertEqual(result["metrics"]["revenue"], {"previous": 100000, "current": 120000})

    def test_different_quarters_and_nonconsecutive_years_rejected(self):
        for previous, current in [("Q4 FY25", "Q1 FY26"), ("Q1 FY24", "Q1 FY26")]:
            with self.subTest(previous=previous):
                result = extract_pages([consolidated(previous=previous, current=current)])
                self.assertIsNone(result["periods"]["current"])
                self.assertIsNone(result["metrics"]["revenue"]["current"])

    def test_multiple_consolidated_period_pairs_are_ambiguous(self):
        result = extract_pages([consolidated(), consolidated(previous="Q2 FY25", current="Q2 FY26")])
        self.assertEqual(result["periods"], {"previous": None, "current": None})
        self.assertIn("revenue.current", result["missing"])

    def test_text_fallback_rejects_unlabelled_extra_column(self):
        page = Page(8, "Consolidated Financial Results\nRs crore\nQ1 FY25 Q1 FY26\nRevenue 100000 120000 20%")
        self.assertIsNone(extract_pages([page])["metrics"]["revenue"]["current"])

    def test_structured_table_preferred_to_conflicting_text(self):
        page = consolidated()
        page.text += "\nQ1 FY25 Q1 FY26\nRevenue 99 88"
        self.assertEqual(extract_pages([page])["metrics"]["revenue"]["current"], 120000)

    def test_section_context_applies_to_next_financial_slide(self):
        pages = [consolidated(), Page(30, "Digital Services"),
                 Page(31, "Financial Performance: Q1 FY26\nRs crore", [[
                     ["Metric", "Q1 FY25", "Q1 FY26"], ["EBITDA", "100", "200"]]]),
                 Page(40, "Retail"),
                 Page(41, "Financial Performance: Q1 FY26\nRs crore", [[
                     ["Metric", "Q1 FY25", "Q1 FY26"], ["EBITDA", "300", "400"]]])]
        result = extract_pages(pages)
        self.assertEqual(result["segment_ebitda"]["Digital Services"]["current"], 200)
        self.assertEqual(result["segment_ebitda"]["Retail"]["current"], 400)
        self.assertIsNone(result["metrics"]["ebitda"]["current"])

    def test_revenue_segment_summary_is_not_ebitda(self):
        summary = Page(7, "Strong Growth Momentum Across Businesses\nRs crore", [[
            ["Revenue", "Q1 FY25", "Q1 FY26"], ["Retail", "100", "200"]]])
        self.assertIsNone(extract_pages([consolidated(), summary])["segment_ebitda"]["Retail"]["current"])

    def test_ebitda_segment_summary(self):
        summary = Page(7, "Strong Growth Momentum Across Businesses\nRs crore", [[
            ["EBITDA", "Q1 FY25", "Q1 FY26"], ["O2C", "100", "200"], ["E&P", "30", "40"]]])
        result = extract_pages([consolidated(), summary])
        self.assertEqual(result["segment_ebitda"]["O2C"]["current"], 200)
        self.assertEqual(result["segment_ebitda"]["E&P"]["current"], 40)

    def test_multidate_balance_values_are_not_guessed(self):
        balance = Page(5, "Strong Balance Sheet\nRs crore", [[["Net Debt", "100", "200"]]])
        self.assertIsNone(extract_pages([consolidated(), balance])["balance"]["net_debt"])

    def test_missing_entry_and_source_are_consistent(self):
        result = extract_pages([consolidated([["PAT*", "—", "0"]])])
        self.assertIn("pat.previous", result["missing"])
        self.assertNotIn("pat.previous", result["sources"])
        self.assertEqual(result["metrics"]["pat"]["current"], 0)
        self.assertNotIn("pat.current", result["missing"])

    def test_same_value_repeated_keeps_both_sources(self):
        result = extract_pages([consolidated(number_=19), consolidated(number_=53)])
        self.assertEqual(result["metrics"]["revenue"]["current"], 120000)
        self.assertEqual({s["page"] for s in result["sources"]["revenue.current"]}, {19, 53})
