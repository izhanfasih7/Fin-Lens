"""Independent numerical examples, not values asserted from a real company report."""
import copy
import unittest

from backend.ratios import calculate_ratios, divide


def inputs():
    metrics = {key: dict(zip(("previous", "current"), pair)) for key, pair in {
        "revenue": (1000, 1200), "ebitda": (200, 300), "pat": (100, 180),
        "pbt": (125, 240), "tax": (25, 60), "finance_cost": (40, 50),
        "depreciation": (35, 40)}.items()}
    balance = {"net_debt": 900, "ltm_ebitda": 600, "net_debt_to_ebitda": None}
    return metrics, balance


class RatioTests(unittest.TestCase):
    def test_all_margins_and_coverage(self):
        result = calculate_ratios(*inputs())
        self.assertEqual(result["previous"], {
            "ebitda_margin_pct": 20, "pbt_margin_pct": 12.5,
            "pat_margin_pct": 10, "effective_tax_rate_pct": 20,
            "interest_coverage_x": 5})
        self.assertEqual(result["current"], {
            "ebitda_margin_pct": 25, "pbt_margin_pct": 20,
            "pat_margin_pct": 15, "effective_tax_rate_pct": 25,
            "interest_coverage_x": 6})

    def test_growth_and_computed_leverage(self):
        result = calculate_ratios(*inputs())
        self.assertEqual(result["yoy_growth_pct"], {"revenue": 20, "ebitda": 50, "pat": 80})
        self.assertEqual(result["net_debt_to_ebitda_x"], 1.5)

    def test_division_missing_zero_and_precision(self):
        for numerator, denominator in [(None, 2), (2, None), (2, 0), (2, -0.0)]:
            with self.subTest(numerator=numerator, denominator=denominator):
                self.assertIsNone(divide(numerator, denominator))
        self.assertEqual(divide(0, 2), 0)
        self.assertEqual(divide(1, 3, 100), 33.33)

    def test_zero_revenue_only_invalidates_revenue_ratios(self):
        metrics, balance = inputs()
        metrics["revenue"]["current"] = 0
        current = calculate_ratios(metrics, balance)["current"]
        for key in ("ebitda_margin_pct", "pbt_margin_pct", "pat_margin_pct"):
            self.assertIsNone(current[key])
        self.assertEqual(current["interest_coverage_x"], 6)

    def test_missing_finance_cost_and_zero_pbt(self):
        metrics, balance = inputs()
        metrics["finance_cost"]["current"] = None
        metrics["pbt"]["current"] = 0
        current = calculate_ratios(metrics, balance)["current"]
        self.assertIsNone(current["effective_tax_rate_pct"])
        self.assertIsNone(current["interest_coverage_x"])
        self.assertEqual(current["pbt_margin_pct"], 0)

    def test_nonpositive_growth_base_is_not_reported(self):
        for previous in (0, -100, None):
            metrics, balance = inputs()
            metrics["pat"]["previous"] = previous
            with self.subTest(previous=previous):
                self.assertIsNone(calculate_ratios(metrics, balance)["yoy_growth_pct"]["pat"])

    def test_loss_preserves_negative_margin_and_decline(self):
        metrics, balance = inputs()
        metrics["pat"]["current"] = -120
        result = calculate_ratios(metrics, balance)
        self.assertEqual(result["current"]["pat_margin_pct"], -10)
        self.assertEqual(result["yoy_growth_pct"]["pat"], -220)

    def test_missing_current_value_does_not_become_zero_growth(self):
        metrics, balance = inputs()
        metrics["ebitda"]["current"] = None
        self.assertIsNone(calculate_ratios(metrics, balance)["yoy_growth_pct"]["ebitda"])

    def test_reported_leverage_including_zero_takes_precedence(self):
        for reported in (0, 1.2):
            metrics, balance = inputs()
            balance["net_debt_to_ebitda"] = reported
            self.assertEqual(calculate_ratios(metrics, balance)["net_debt_to_ebitda_x"], reported)

    def test_unavailable_ltm_denominator(self):
        for denominator in (None, 0):
            metrics, balance = inputs()
            balance["ltm_ebitda"] = denominator
            self.assertIsNone(calculate_ratios(metrics, balance)["net_debt_to_ebitda_x"])

    def test_net_cash_can_have_negative_leverage(self):
        metrics, balance = inputs()
        balance["net_debt"] = -300
        self.assertEqual(calculate_ratios(metrics, balance)["net_debt_to_ebitda_x"], -.5)

    def test_does_not_mutate_input_or_invent_balance_ratios(self):
        original = inputs()
        before = copy.deepcopy(original)
        result = calculate_ratios(*original)
        self.assertEqual(original, before)
        for key in ("roe", "roa", "current_ratio"):
            self.assertNotIn(key, result["current"])
