"""Optional checks on the user's real PDF. Never silently substitute synthetic data."""
import os
from pathlib import Path
import unittest

from backend.extraction import extract_pdf
from backend.ratios import calculate_ratios

SAMPLE = os.environ.get("FINLENS_SAMPLE_PDF")


@unittest.skipUnless(SAMPLE, "Real Reliance PDF not supplied; set FINLENS_SAMPLE_PDF to enable.")
class RelianceSampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(SAMPLE)
        if not path.is_file():
            raise FileNotFoundError(f"FINLENS_SAMPLE_PDF does not point to a file: {path}")
        cls.result = extract_pdf(path.read_bytes())
        cls.ratios = calculate_ratios(cls.result["metrics"], cls.result["balance"])

    def test_expected_report_periods_and_length(self):
        self.assertEqual(self.result["page_count"], 80, "Expected the specified 80-slide presentation.")
        self.assertEqual(self.result["periods"], {"previous": "Q1 FY25", "current": "Q1 FY26"})

    def test_user_provided_ratio_expectations(self):
        for period, margin, coverage in [("previous", 6.8, 7.2), ("current", 11.3, 8.2)]:
            for key, expected in [("pat_margin_pct", margin), ("interest_coverage_x", coverage)]:
                with self.subTest(period=period, ratio=key):
                    value = self.ratios[period][key]
                    self.assertIsNotNone(value, f"Cannot validate {key}: required figures are missing.")
                    self.assertAlmostEqual(value, expected, delta=.05)

    def test_required_figures_and_provenance_are_present(self):
        for metric in ("revenue", "ebitda", "finance_cost", "depreciation", "pbt", "tax", "pat"):
            for period in ("previous", "current"):
                with self.subTest(metric=metric, period=period):
                    self.assertIsNotNone(self.result["metrics"][metric][period])
                    sources = self.result["sources"].get(f"{metric}.{period}", [])
                    self.assertTrue(sources)
                    self.assertTrue(all(1 <= s["page"] <= self.result["page_count"] for s in sources))
        for metric in ("net_debt", "ltm_ebitda", "net_debt_to_ebitda"):
            with self.subTest(balance_metric=metric):
                self.assertIsNotNone(self.result["balance"][metric])
                self.assertTrue(self.result["sources"].get(metric))
        for segment in ("O2C", "E&P", "Digital Services", "Retail", "Others"):
            for period in ("previous", "current"):
                with self.subTest(segment=segment, period=period):
                    self.assertIsNotNone(self.result["segment_ebitda"][segment][period])
                    self.assertTrue(self.result["sources"].get(f"segments.{segment}.{period}"))
