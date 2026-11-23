import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.health import FEATURES, predict_health, rule_rating
from backend.sentiment import analyze_sentiment, split_sentences, summarize_predictions


class HealthTests(unittest.TestCase):
    def test_no_data_is_not_risky(self):
        result = rule_rating({})
        self.assertIsNone(result["rating"])
        self.assertIsNone(result["score"])

    def test_missing_values_are_not_zero(self):
        result = rule_rating({"pat_margin_pct": 11, "ebitda_margin_pct": 20})
        self.assertEqual(result["score"], 100)
        self.assertEqual(len(result["components"]), 2)

    def test_sparse_data_falls_back(self):
        result = predict_health({"current": {"pat_margin_pct": 3, "ebitda_margin_pct": 8}})
        self.assertEqual(result["method"], "rule_based")
        self.assertEqual(result["rating"], "Average")

    def test_training_export_company_split_and_inference(self):
        import pandas as pd
        from ml.train_health import train
        # Synthetic fixture tests plumbing, never used as the shipped trained model.
        rows = []
        for company in range(12):
            for label, value in [("Risky", -10), ("Average", 5), ("Good", 25)]:
                rows.append({"company": f"fixture_{company}", "health_label": label,
                             "label_source": "synthetic_test", **dict.fromkeys(FEATURES, value)})
        with tempfile.TemporaryDirectory() as directory:
            csv = Path(directory) / "test.csv"
            model = Path(directory) / "test.joblib"
            pd.DataFrame(rows).to_csv(csv, index=False)
            report = train(csv, model)
            self.assertFalse(set(report["train_companies"]) & set(report["test_companies"]))
            self.assertEqual(len(report["confusion_matrix"]), 3)
            with patch.dict(os.environ, {"FINLENS_HEALTH_MODEL": str(model)}):
                result = predict_health({"current": {"pat_margin_pct": 25, "ebitda_margin_pct": 25},
                                         "yoy_growth_pct": {"revenue": 25, "ebitda": 25, "pat": 25}})
            self.assertEqual(result["method"], "random_forest")
            self.assertEqual(result["rating"], "Good")
            self.assertLessEqual(result["score"], 100)


class SentimentTests(unittest.TestCase):
    def test_decimal_and_deduplication(self):
        sentences = split_sentences(["Revenue grew 11.3%. Margins improved this quarter.",
                                     "Revenue grew 11.3%."])
        self.assertEqual(len(sentences), 2)
        self.assertEqual(sentences[0], "Revenue grew 11.3%.")

    def test_unavailable_is_not_neutral(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"FINLENS_FINBERT_DIR": str(Path(directory) / 'missing')}):
                result = analyze_sentiment(["Revenue grew substantially this quarter."])
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["gauge_score"])
        self.assertIsNone(result["percentages"])

    def test_no_commentary(self):
        self.assertEqual(analyze_sentiment([])["status"], "no_commentary")

    def test_gauge_and_top_sentences(self):
        items = [{"sentence": "Revenue increased", "label": "positive", "confidence": .9,
                  "probabilities": {"positive": .9, "negative": .05, "neutral": .05}},
                 {"sentence": "Profit declined", "label": "negative", "confidence": .9,
                  "probabilities": {"positive": .05, "negative": .9, "neutral": .05}}]
        result = summarize_predictions(items, 3, 0)
        self.assertEqual(result["gauge_score"], 50)
        self.assertEqual(result["percentages"]["positive"], 50)
        self.assertEqual(len(result["top_positive"]), 1)
        self.assertEqual(result["sentences_skipped"], 1)


if __name__ == "__main__":
    unittest.main()
