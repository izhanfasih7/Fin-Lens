"""Synthetic fixtures: these are NOT the user's Reliance presentation."""
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.extraction import Page, extract_pages, number, PDFError
from backend.main import app
from backend.ratios import calculate_ratios


def fixture():
    return Page(17, "Consolidated Financial Results\nRs crore\nQ1 FY25 Q1 FY26", [[
        ["Rs crore", "Q1 FY26", "Q1 FY25"],
        ["Revenue", "1,00,000", "1,00,000"],
        ["EBITDA", "41,000", "36,000"],
        ["Finance Cost", "5,000", "5,000"],
        ["Depreciation", "10,000", "9,000"],
        ["PBT", "15,000", "10,000"],
        ["Tax", "3,700", "3,200"],
        ["PAT*", "11,300", "6,800"],
    ]])


class ExtractionTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(number("3,30,870*"), 330870)
        self.assertEqual(number("(1,234)"), -1234)
        self.assertEqual(number("8.2x"), 8.2)
        self.assertIsNone(number("(4%)"))
        self.assertIsNone(number("USD 45"))

    def test_period_order_and_ratios(self):
        result = extract_pages([fixture()])
        self.assertEqual(result["periods"]["current"], "Q1 FY26")
        ratios = calculate_ratios(result["metrics"], result["balance"])
        self.assertEqual(ratios["current"]["pat_margin_pct"], 11.3)
        self.assertEqual(ratios["previous"]["pat_margin_pct"], 6.8)
        self.assertEqual(ratios["current"]["interest_coverage_x"], 8.2)
        self.assertEqual(ratios["previous"]["interest_coverage_x"], 7.2)
        self.assertEqual(result["sources"]["pat.current"][0]["page"], 17)

    def test_missing_and_zero(self):
        result = extract_pages([])
        self.assertIn("pat.current", result["missing"])
        ratios = calculate_ratios(result["metrics"], result["balance"])
        self.assertIsNone(ratios["current"]["pat_margin_pct"])
        result = extract_pages([fixture()])
        result["metrics"]["revenue"]["current"] = 0
        self.assertIsNone(calculate_ratios(result["metrics"], result["balance"])
                          ["current"]["pat_margin_pct"])

    def test_segment_does_not_override_consolidated(self):
        segment = Page(30, "Retail\nFinancial Performance: Q1 FY26\nRs crore", [
            [["Metric", "Q1 FY25", "Q1 FY26"], ["EBITDA", "100", "200"]]])
        result = extract_pages([fixture(), segment])
        self.assertEqual(result["metrics"]["ebitda"]["current"], 41000)
        self.assertEqual(result["segment_ebitda"]["Retail"]["current"], 200)

    def test_conflict(self):
        other = fixture()
        other.number = 18
        other.tables[0][-1][1] = "12,000"
        self.assertIsNone(extract_pages([fixture(), other])["metrics"]["pat"]["current"])

    def test_ambiguous_currency(self):
        page = fixture()
        page.text += "\n$ Bn"
        self.assertIsNone(extract_pages([page])["metrics"]["pat"]["current"])

    def test_text_fallback_and_balance(self):
        page = Page(4, "Consolidated Financial Results\nRs crore\nQ1 FY25 Q1 FY26\nPAT 6,800 11,300")
        balance = Page(5, "Strong Balance Sheet\nRs crore\nNet Debt 10,000\nLTM EBITDA 5,000\nNet Debt/EBITDA 2.0x")
        result = extract_pages([page, balance])
        self.assertEqual(result["metrics"]["pat"]["current"], 11300)
        self.assertEqual(result["balance"]["net_debt_to_ebitda"], 2)


class APITests(unittest.TestCase):
    def test_round_trip_and_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"FINLENS_DB": os.path.join(directory, "test.sqlite3")}):
                with TestClient(app) as client:
                    for path in ('/', '/upload', '/results/demo', '/history', '/assets/app.css'):
                        self.assertEqual(client.get(path).status_code, 200)
                    demo = client.get('/api/demo').json()
                    self.assertTrue(demo['is_demo'])
                    self.assertGreater(demo['health']['score'],80)
                    self.assertLess(demo['health']['score'],94)
                    self.assertEqual(client.get('/api/history').json(), [])
                    self.assertEqual(client.post("/api/analyze", files={"file": ("a.txt", b"bad")}).status_code, 415)
                    self.assertEqual(client.post("/api/analyze", files={"file": ("a.pdf", b"bad")}).status_code, 415)
                    with patch("backend.main.extract_pdf", side_effect=PDFError("Corrupt PDF")):
                        self.assertEqual(client.post("/api/analyze", files={"file": ("a.pdf", b"%PDF-bad")}).status_code, 422)
                    with patch("backend.main.extract_pdf", return_value=extract_pages([fixture()])):
                        response = client.post("/api/analyze", files={"file": ("a.pdf", b"%PDF-test")})
                    self.assertEqual(response.status_code, 201)
                    result = response.json()
                    self.assertEqual(client.get('/api/analysis/' + result['id']).json(), result)
                    self.assertEqual(len(client.get('/api/history').json()), 1)
                    self.assertEqual(client.get('/api/analysis/missing').status_code, 404)


if __name__ == "__main__":
    unittest.main()
